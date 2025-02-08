"""
Trading Agent
Handles automated trading execution and analysis
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
from termcolor import cprint
from dotenv import load_dotenv
from src.monitoring.performance_monitor import PerformanceMonitor
from src.monitoring.system_monitor import SystemMonitor
from src import nice_funcs as n
from src.data.ohlcv_collector import collect_all_tokens
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
from src.models import ModelFactory
from src.data.jupiter_client import JupiterClient
from src.data.raydium_client import RaydiumClient
from src.data.chainstack_client import ChainStackClient
from src.strategies.snap_strategy import SnapStrategy
from src.monitoring.performance_monitor import PerformanceMonitor
from src.monitoring.system_monitor import SystemMonitor
from src.agents.risk_agent import RiskAgent
from src.agents.focus_agent import FocusAgent
import json
from pathlib import Path
from src.config import (
    USDC_SIZE,
    MAX_LOSS_PERCENTAGE,
    SLIPPAGE,
    TRADE_INTERVAL,
    MIN_SOL_BALANCE,
    MIN_USDC_BALANCE,
    CREATE_ATA_IF_MISSING,
    USDC_ADDRESS,
    USE_SOL_FOR_TRADING,
    MIN_TRADE_SIZE_SOL,
    MAX_ORDER_SIZE_SOL
)

# Load token list
TOKEN_LIST_PATH = Path(__file__).parent.parent / "data" / "token_list.json"
with open(TOKEN_LIST_PATH) as f:
    token_data = json.load(f)
    FOCUS_TOKENS = [token["address"] for token in token_data["tokens"]]
from src.nice_funcs import (
    market_buy,
    market_sell,
    fetch_wallet_holdings_og,
    calculate_atr
)

# Load environment variables
load_dotenv()

class TradingAgent:
    def __init__(self, instance_id: str, model_type: str = "deepseek", model_name: str = "deepseek-r1:1.5b"):
        self.instance_id = instance_id
        self.model_type = model_type
        self.model_name = model_name
        self.model_factory = ModelFactory()
        self.model = self.model_factory.get_model(self.model_type)
        self.min_trade_size = MIN_TRADE_SIZE_SOL
        self.max_position_size = 0.20
        self.cash_buffer = 0.30
        self.slippage = SLIPPAGE
        self.snap_strategy = SnapStrategy()
        self.performance_monitor = PerformanceMonitor()
        self.system_monitor = SystemMonitor(self.performance_monitor)
        self.last_trade_time = datetime.now()
        self.active = True
        self.total_trades = 0
        self.successful_trades = 0
        
        # Initialize trading components
        self.jupiter_client = JupiterClient()
        self.raydium_client = RaydiumClient()
        self.chainstack_client = ChainStackClient()
        self.sol_token = "So11111111111111111111111111111111111111112"
        
        # Initialize position tracking
        self.positions: Dict[str, float] = {}
        
    def _parse_analysis(self, response: str) -> dict:
        """Parse AI model response into structured data"""
        default_analysis = {
            'sentiment': 'neutral',
            'confidence': 0.0,
            'action': 'hold',
            'reason': ''
        }
        
        try:
            lines = response.strip().split('\n')
            analysis = default_analysis.copy()
            
            for line in lines:
                if 'sentiment:' in line.lower():
                    analysis['sentiment'] = line.split(':')[1].strip().lower()
                elif 'confidence:' in line.lower():
                    try:
                        analysis['confidence'] = float(line.split(':')[1].strip().replace('%', '')) / 100
                    except:
                        pass
                elif 'action:' in line.lower():
                    analysis['action'] = line.split(':')[1].strip().lower()
                elif 'reason:' in line.lower():
                    analysis['reason'] = line.split(':')[1].strip()
                    
            return analysis
        except Exception as e:
            print(f"Error parsing analysis: {e}")
            default_analysis['reason'] = f'Error: {e}'
            return default_analysis
            
    def detect_market_condition(self, token_data: dict) -> str:
        """Detect if market is trending"""
        try:
            prices = token_data.get('prices', [])
            if len(prices) < 20:
                return 'unknown'
                
            # Calculate 20-period SMA
            sma = sum(prices[-20:]) / 20
            current_price = prices[-1]
            
            # If price is >2% away from SMA, consider trending
            return 'trending' if abs(current_price - sma) / sma > 0.02 else 'ranging'
        except Exception as e:
            print(f"Error detecting market condition: {e}")
            return 'unknown'
            
    def calculate_signal_strength(self, strategy_signal: float, sentiment_score: float, volatility: float) -> float:
        """Calculate composite signal strength using multi-factor model"""
        return (0.6 * strategy_signal + 0.3 * sentiment_score + 0.1 * (1 - volatility))
        
    async def get_position_size(self, token: str) -> float:
        """Get current position size in tokens"""
        try:
            wallet_address = os.getenv("WALLET_ADDRESS")
            if not wallet_address:
                return 0.0
                
            # Get token balance from positions cache
            return self.positions.get(token, 0.0)
        except Exception as e:
            cprint(f"❌ Error getting position size: {str(e)}", "red")
            return 0.0
            
    async def execute_partial_position(self, token: str, percentage: float) -> Optional[str]:
        """Execute trade for percentage of position"""
        try:
            current_size = await self.get_position_size(token)
            if current_size <= 0:
                cprint(f"❌ No position found for token {token}", "red")
                return None
                
            # Calculate trade size
            trade_size = current_size * percentage
            if trade_size < self.min_trade_size:
                cprint(f"❌ Trade size {trade_size} below minimum {self.min_trade_size}", "red")
                return None
                
            # Execute trade
            trade_request = {
                'token': token,
                'amount': trade_size,
                'slippage_bps': self.slippage,
                'direction': 'sell'  # Partial positions are for selling
            }
            signature = self.execute_trade(trade_request)
            
            if signature:
                # Update position tracking
                self.positions[token] = current_size - trade_size
                if self.positions[token] <= 0:
                    del self.positions[token]
                    
            return signature
        except Exception as e:
            cprint(f"❌ Error executing partial position: {str(e)}", "red")
            return None
            
            if signature:
                # Update position tracking
                self.positions[token] = current_size - trade_size
                if self.positions[token] <= 0:
                    del self.positions[token]
                    
            return signature
            
    async def validate_position_size(self, token: str, size: float) -> bool:
        """Validate if position size is within limits"""
        try:
            # Get total portfolio value
            values = await self.get_position_values()
            total_value = sum(values.values())
            
            # Calculate new position value
            token_price = await self.get_token_price(token)
            new_position_value = size * token_price
            
            # Check against max position size
            if total_value > 0 and new_position_value / total_value > self.max_position_size:
                cprint(f"❌ Position size {new_position_value/total_value:.2%} exceeds max {self.max_position_size:.2%}", "red")
                return False
                
            return True
        except Exception as e:
            cprint(f"❌ Error validating position size: {str(e)}", "red")
            return False
            
    async def get_position_values(self) -> Dict[str, float]:
        """Get current position values in SOL"""
        values = {}
        for token, size in self.positions.items():
            price = await self.get_token_price(token)
            values[token] = size * price
        return values
            
    async def get_token_price_raydium(self, token_address: str) -> Optional[Decimal]:
        """Get token price from Raydium
        
        Args:
            token_address: Token mint address
            
        Returns:
            Token price as Decimal or None if error occurs
        """
        try:
            async with RaydiumClient() as client:
                return await client.get_token_price(token_address)
        except Exception as e:
            cprint(f"❌ Failed to get Raydium token price: {str(e)}", "red")
            return None
            
    async def get_token_price(self, token: str) -> float:
        """Get token price in SOL using Jupiter"""
        try:
            quote = self.jupiter_client.get_quote(
                input_mint=token,
                output_mint=self.jupiter_client.sol_token,
                amount="1000000000"  # 1 unit in smallest denomination
            )
            if not quote:
                return 0.0
            return float(quote.get('outAmount', 0)) / 1e9
        except Exception as e:
            cprint(f"❌ Error getting token price: {str(e)}", "red")
            return 0.0
        
    def calculate_position_size(self, token_data: dict) -> float:
        """Calculate dynamic position size based on ATR and portfolio value"""
        try:
            atr = calculate_atr(
                token_data.get('high_prices', []),
                token_data.get('low_prices', []),
                token_data.get('close_prices', [])
            )
            
            portfolio_value = float(token_data.get('portfolio_value', 0))
            max_risk_amount = portfolio_value * 0.01  # 1% risk per trade
            
            position_size = min(
                max_risk_amount / (atr if atr > 0 else 1),
                portfolio_value * 0.05  # 5% max position size
            )
            
            return max(position_size, 0)
        except Exception as e:
            print(f"Error calculating position size: {e}")
            return 0
            
    async def analyze_market_data(self, token_data: dict) -> dict:
        """Analyze market data using Snap strategy and DeepSeek model"""
        if not token_data or not isinstance(token_data, dict):
            return {
                'action': 'NEUTRAL',
                'confidence': 0.0,
                'reason': 'Invalid token data',
                'metadata': {}
            }
            
        try:
            # Get Snap strategy signals
            symbol = token_data.get('symbol', '')
            if not symbol:
                return {
                    'action': 'NEUTRAL',
                    'confidence': 0.0,
                    'reason': 'Missing token symbol',
                    'metadata': {}
                }
                
            self.snap_strategy.set_token(symbol)
            strategy_signals = self.snap_strategy.generate_signals()
            
            # Get DeepSeek analysis
            if not self.model:
                return {
                    'action': 'NEUTRAL',
                    'confidence': 0.0,
                    'reason': 'Model not initialized',
                    'metadata': {}
                }
                
            model_analysis = await self.model.analyze_trading_opportunity(token_data)
            if not model_analysis:
                return {
                    'action': 'NEUTRAL',
                    'confidence': 0.0,
                    'reason': 'Model analysis failed',
                    'metadata': {}
                }
                
            # Combine signals
            signal_strength = self.calculate_signal_strength(
                strategy_signals.get('signal', 0),
                model_analysis.get('confidence', 0),
                token_data.get('volatility', 0.2)
            )
            
            # Determine final direction
            strategy_direction = strategy_signals.get('direction', 'NEUTRAL')
            model_direction = model_analysis.get('direction', 'NEUTRAL')
            
            # Only trade if both signals agree
            final_direction = strategy_direction if strategy_direction == model_direction else 'NEUTRAL'
            
            return {
                'action': final_direction,
                'confidence': signal_strength,
                'reason': f"Strategy: {strategy_signals.get('metadata', {})} | Model: {model_analysis.get('factors', [])}",
                'metadata': {
                    'strategy_signals': strategy_signals,
                    'model_analysis': model_analysis,
                    'params': strategy_signals.get('metadata', {}).get('params', {})
                }
            }
        except Exception as e:
            cprint(f"❌ Error analyzing market data: {str(e)}", "red")
            return {
                'action': 'NEUTRAL',
                'confidence': 0.0,
                'reason': f'Error: {str(e)}',
                'metadata': {}
            }
            
    async def check_balances(self) -> tuple[bool, str]:
        """Check if wallet has sufficient balances"""
        try:
            # Check SOL balance
            wallet_address = os.getenv("WALLET_ADDRESS")
            if not wallet_address:
                return False, "Wallet address not set"
                
            # Get real-time SOL balance from ChainStack
            sol_balance = await self.chainstack_client.get_wallet_balance(wallet_address)
            if not sol_balance:
                return False, "Failed to get SOL balance"
                
            # Convert to float for comparison
            balance_sol = float(sol_balance)
            
            # Check minimum SOL balance (0.02 SOL for trade + 0.01 SOL buffer)
            min_required = 0.02 + 0.01  # Trade amount + buffer for gas
            
            if balance_sol < min_required:
                return False, f"Insufficient SOL balance: {balance_sol:.4f} SOL (required: {min_required:.4f} SOL)"
                
            # Log balance check
            cprint(f"✅ SOL balance check passed: {balance_sol:.4f} SOL", "green")
            return True, f"Sufficient SOL balance: {balance_sol:.4f} SOL"
                
        except Exception as e:
            error_msg = f"Error checking balances: {str(e)}"
            cprint(f"❌ {error_msg}", "red")
            await logging_service.log_error(
                error_msg,
                {
                    'error': str(e),
                    'wallet': '[REDACTED]'
                },
                'system'
            )
            return False, error_msg

    async def execute_trade(self, trade_request: Dict[str, Any]) -> Optional[str]:
        """Execute trade based on trade request"""
        if not self.active:
            cprint(f"❌ Instance {self.instance_id} is not active", "red")
            return None
            
        try:
            wallet_address = os.getenv("WALLET_ADDRESS")
            if not wallet_address:
                cprint("❌ Trade failed: No wallet address configured", "red")
                return None
                
            if not trade_request.get('token'):
                cprint("❌ Trade failed: No token specified", "red")
                return None
                
            # Check balances first
            balances_ok, reason = await self.check_balances()
            if not balances_ok:
                cprint(f"❌ Trade failed: {reason}", "red")
                return None
                
            # Route specific token to Raydium
            if trade_request['token'] == "6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump":
                try:
                    # Use Raydium for specified token with fixed 0.02 SOL amount
                    amount = str(int(0.02 * 1e9))  # Convert to lamports
                    
                    async with self.raydium_client as client:
                        quote = await client.get_quote(
                            input_mint=self.sol_token if trade_request.get('direction') == 'buy' else trade_request['token'],
                            output_mint=trade_request['token'] if trade_request.get('direction') == 'buy' else self.sol_token,
                            amount=amount
                        )
                        if not quote:
                            cprint("❌ Failed to get Raydium quote", "red")
                            return None
                            
                        # Execute swap with SOL wrapping/unwrapping
                        signature = await client.execute_swap(
                            quote=quote,
                            wallet_key=wallet_address,
                            is_sol_trade=True  # Enable SOL wrapping/unwrapping
                        )
                        
                        if signature:
                            # Verify transaction
                            success = await client.verify_transaction(signature)
                            if not success:
                                cprint(f"❌ Transaction failed verification: {signature}", "red")
                                return None
                                
                            # Log metrics
                            await self.performance_monitor.log_trade_metrics({
                                'instance_id': self.instance_id,
                                'token': trade_request['token'],
                                'direction': trade_request.get('direction', 'buy'),
                                'amount': 0.02,  # Fixed amount
                                'execution_time': datetime.now().timestamp(),
                                'slippage': trade_request.get('slippage_bps', 250) / 100,
                                'success': True,
                                'dex': 'raydium'
                            })
                            
                            self.total_trades += 1
                            self.successful_trades += 1
                            self.last_trade_time = datetime.now()
                            
                            cprint(f"✅ Raydium trade successful: {signature}", "green")
                            return signature
                            
                        return None
                except Exception as e:
                    cprint(f"❌ Raydium trade error: {str(e)}", "red")
                    return None
                    
            # Use Jupiter for all other tokens
            try:
                # Get quote with optimized parameters
                quote = await self.jupiter_client.get_quote(
                    input_mint=self.sol_token if trade_request.get('direction') == 'buy' else trade_request['token'],
                    output_mint=trade_request['token'] if trade_request.get('direction') == 'buy' else self.sol_token,
                    amount=str(int(float(trade_request['amount']) * 1e9))
                )
                if not quote:
                    cprint("❌ Failed to get Jupiter quote", "red")
                    return None
                    
                # Execute swap
                signature = await self.jupiter_client.execute_swap(
                    quote_response=quote,
                    wallet_pubkey=wallet_address,
                    use_shared_accounts=True
                )
                
                if signature:
                    # Log metrics for Jupiter trade
                    await self.performance_monitor.log_trade_metrics({
                        'instance_id': self.instance_id,
                        'token': trade_request['token'],
                        'direction': trade_request.get('direction', 'buy'),
                        'amount': float(trade_request['amount']),
                        'execution_time': datetime.now().timestamp(),
                        'slippage': trade_request.get('slippage_bps', 250) / 100,
                        'success': True,
                        'dex': 'jupiter'
                    })
                    
                    self.total_trades += 1
                    self.successful_trades += 1
                    self.last_trade_time = datetime.now()
                    
                    # Update position tracking for buys
                    if trade_request.get('direction') == 'buy':
                        current = self.positions.get(trade_request['token'], 0.0)
                        self.positions[trade_request['token']] = current + float(trade_request['amount'])
                        
                    cprint(f"✅ Jupiter trade successful: {signature}", "green")
                    
                return signature
                
            except Exception as e:
                cprint(f"❌ Jupiter trade error: {str(e)}", "red")
                return None
                
        except Exception as e:
            cprint(f"❌ Error executing trade: {str(e)}", "red")
            return None
            # Get quote with optimized parameters
            loop = asyncio.get_event_loop()
            quote = await loop.run_in_executor(
                None,
                lambda: self.jupiter_client.get_quote(
                    input_mint=self.sol_token if trade_request.get('direction') == 'buy' else trade_request['token'],
                    output_mint=trade_request['token'] if trade_request.get('direction') == 'buy' else self.sol_token,
                    amount=str(int(float(trade_request['amount']) * 1e9))
                )
            )
            if not quote:
                cprint("❌ Failed to get quote", "red")
                return None
                
            # Execute swap
            signature = await loop.run_in_executor(
                None,
                lambda: self.jupiter_client.execute_swap(
                    quote_response=quote,
                    wallet_pubkey=wallet_address,
                    use_shared_accounts=True
                )
            )
            
            if signature:
                # Update metrics
                metrics = {
                    'instance_id': self.instance_id,
                    'token': trade_request['token'],
                    'direction': trade_request.get('direction', 'buy'),
                    'amount': float(trade_request['amount']),
                    'execution_time': datetime.now().timestamp(),
                    'slippage': trade_request.get('slippage_bps', 250) / 100,
                    'success': True
                }
                await loop.run_in_executor(
                    None,
                    lambda: self.performance_monitor.log_trade_metrics(metrics)
                )
                self.total_trades += 1
                self.successful_trades += 1
                self.last_trade_time = datetime.now()
                
                # Update position tracking for buys
                if trade_request.get('direction') == 'buy':
                    current = self.positions.get(trade_request['token'], 0.0)
                    self.positions[trade_request['token']] = current + float(trade_request['amount'])
                
            return signature
            
        except Exception as e:
            cprint(f"❌ Error executing trade: {str(e)}", "red")
            return None
                
            # Get current positions and calculate total position value
            positions_df = fetch_wallet_holdings_og(os.getenv("WALLET_ADDRESS", ""))
            total_position = positions_df['USD Value'].sum()
            max_trade_size = float(os.getenv("SOL_BALANCE", "0")) * self.max_position_size
            
            # Check if new trade would exceed max position size
            if total_position + trade_request.get('amount_sol', 0) > max_trade_size:
                cprint(f"❌ Trade would exceed max position size of {max_trade_size} SOL", "red")
                return None
                
            jupiter = JupiterClient()
            
            # Calculate SOL amount for trade
            trade_amount = min(trade_request.get('amount_sol', 0), MAX_ORDER_SIZE_SOL)
            client = ChainStackClient()
            start_balance = client.get_wallet_balance(os.getenv("WALLET_ADDRESS"))
            
            # Get quote with optimized parameters
            quote = self.jupiter_client.get_quote(
                input_mint=self.sol_token if trade_request.get('direction') == 'buy' else trade_request['token'],
                output_mint=trade_request['token'] if trade_request.get('direction') == 'buy' else self.sol_token,
                amount=str(int(float(trade_request['amount']) * 1e9))
            )
            if not quote:
                cprint("❌ Failed to get quote", "red")
                return None
                
            # Execute swap
            if wallet_address:
                signature = self.jupiter_client.execute_swap(
                    quote_response=quote,
                    wallet_pubkey=wallet_address,
                    use_shared_accounts=True
                )
                
            if signature:
                end_balance = client.get_wallet_balance(os.getenv("WALLET_ADDRESS"))
                gas_cost = start_balance - end_balance - trade_amount
                metrics = {
                    'instance_id': self.instance_id,
                    'token': trade_request.get('output_token'),
                    'direction': 'BUY',
                    'amount': trade_amount,
                    'execution_time': 0,  # Will be set by caller
                    'slippage': trade_request.get('slippage_bps', 250) / 100,
                    'gas_cost': gas_cost,
                    'success': True
                }
                self.performance_monitor.log_trade_metrics(metrics)
                self.total_trades += 1
                self.successful_trades += 1
                self.last_trade_time = datetime.now()
                
            return signature
        except Exception as e:
            cprint(f"❌ Error executing trade: {str(e)}", "red")
            return None
            
    def check_circuit_breakers(self, trade_data: dict) -> tuple[bool, str]:
        """Check multi-layer circuit breakers"""
        try:
            # Circuit breaker 1: Single trade loss
            if trade_data.get('unrealized_loss_percentage', 0) > 2:
                return False, "Single trade loss exceeds 2% - reducing position by 50%"
                
            # Circuit breaker 2: Market volatility
            if trade_data.get('market_volatility', 0) > 0.3:
                return False, "Market volatility exceeds 30% - halting trading"
                
            # Circuit breaker 3: Portfolio volatility
            if trade_data.get('portfolio_volatility', 0) > 0.25:
                return False, "Portfolio volatility high - reducing leverage to 50%"
                
            return True, ""
        except Exception as e:
            print(f"Error in circuit breakers: {e}")
            return False, f"Circuit breaker error: {str(e)}"
            
    async def _check_risk_limits(self) -> bool:
        """Check risk management limits with circuit breakers"""
        try:
            # Get current positions from chainstack
            wallet_address = os.getenv("WALLET_ADDRESS")
            if not wallet_address:
                return True
                
            total_value = 0
            for token, amount in self.positions.items():
                price = await self.get_token_price(token)
                total_value += amount * price
                
            if total_value == 0:
                return True
                
            # Prepare trade data
            market_volatility = await self.calculate_volatility("SOL")  # Use SOL as market indicator
            trade_data = {
                'portfolio_value': total_value,
                'portfolio_volatility': await self._calculate_portfolio_volatility(),
                'market_volatility': market_volatility
            }
            
            # Check position sizes
            for token, amount in self.positions.items():
                price = await self.get_token_price(token)
                position_value = amount * price
                size_percentage = (position_value / total_value) * 100
                
                # Get entry price from order history
                entry_price = self.positions.get(f"{token}_entry_price", price)
                unrealized_pnl = (price - entry_price) / entry_price * 100
                trade_data['unrealized_loss_percentage'] = -unrealized_pnl
                
                # Check circuit breakers
                is_safe, reason = self.check_circuit_breakers(trade_data)
                if not is_safe:
                    cprint(f"🚨 Circuit breaker: {reason}", "yellow")
                    return False
                    
            return True
            
        except Exception as e:
            print(f"Error checking risk limits: {e}")
            return False
            
    async def _calculate_portfolio_volatility(self) -> float:
        """Calculate portfolio volatility"""
        try:
            # Calculate volatility based on position values
            if not self.positions:
                return 0.0
                
            total_volatility = 0.0
            total_value = 0.0
            
            for token, amount in self.positions.items():
                price = await self.get_token_price(token)
                value = amount * price
                volatility = await self.calculate_volatility(token)
                total_volatility += value * volatility
                total_value += value
                
            return total_volatility / total_value if total_value > 0 else 0.0
            return float(values.std() / values.mean()) if values.mean() > 0 else 0
            
        except Exception as e:
            print(f"Error calculating portfolio volatility: {e}")
            return 1.0  # Return high volatility on error

    async def get_token_data(self, token: str) -> dict:
        """Get token market data"""
        try:
            token_data = await self.chainstack_client.get_token_data(token)
            if not token_data:
                return {}
            
            # Ensure symbol is available for snap strategy
            if 'symbol' not in token_data:
                token_data['symbol'] = token
                
            return token_data
        except Exception as e:
            cprint(f"❌ Error getting token data: {str(e)}", "red")
            return {}

    async def calculate_volatility(self, token: str) -> float:
        """Calculate token volatility using ATR"""
        try:
            token_data = await self.get_token_data(token)
            if not token_data:
                return 0.2  # Default 20% volatility
                
            atr = calculate_atr(
                token_data.get('high_prices', []),
                token_data.get('low_prices', []),
                token_data.get('close_prices', [])
            )
            
            # Normalize ATR to percentage
            current_price = token_data.get('close_prices', [])[-1] if token_data.get('close_prices') else 1
            return float(atr / current_price if current_price > 0 else 0.2)
            
        except Exception as e:
            cprint(f"❌ Error calculating volatility: {str(e)}", "red")
            return 0.2

    async def generate_trading_signal(self, token: str) -> dict:
        """Generate trading signal using DeepSeek model and Snap strategy"""
        try:
            token_data = await self.get_token_data(token)
            if not token_data:
                return {
                    'signal': 0.0,
                    'direction': 'NEUTRAL',
                    'confidence': 0.0,
                    'metadata': {}
                }
                
            analysis = await self.analyze_market_data(token_data)
            if not analysis:
                return {
                    'signal': 0.0,
                    'direction': 'NEUTRAL',
                    'confidence': 0.0,
                    'metadata': {}
                }
                
            return {
                'signal': analysis.get('confidence', 0.0),
                'direction': analysis.get('action', 'NEUTRAL'),
                'confidence': analysis.get('confidence', 0.0),
                'metadata': analysis.get('metadata', {})
            }
        except Exception as e:
            cprint(f"❌ Error generating trading signal: {str(e)}", "red")
            return {
                'signal': 0.0,
                'direction': 'NEUTRAL',
                'confidence': 0.0,
                'metadata': {}
            }

    def update_config(self, config: Dict[str, Any]) -> None:
        self.min_trade_size = config.get('amount_sol', MIN_TRADE_SIZE_SOL)
        self.max_position_size = config.get('max_position_size', 0.20)
        self.cash_buffer = config.get('cash_buffer', 0.30)
        self.slippage = config.get('slippage_bps', SLIPPAGE)
        self.strategy_params = config.get('strategy_params', {})
        
    def apply_strategy(self, strategy_name: str, strategy_params: Dict[str, Any]) -> None:
        self.strategy_params = strategy_params
        if strategy_name == 'snap':
            self.snap_strategy = SnapStrategy(**strategy_params)
        # Additional strategies can be added here

    def toggle_active(self) -> bool:
        self.active = not self.active
        return self.active

    def get_instance_metrics(self) -> Dict[str, Any]:
        return {
            'instance_id': self.instance_id,
            'total_trades': self.total_trades,
            'successful_trades': self.successful_trades,
            'success_rate': f"{(self.successful_trades / self.total_trades * 100):.1f}%" if self.total_trades > 0 else "0%",
            'last_trade_time': self.last_trade_time.isoformat() if self.last_trade_time else None,
            'active': self.active,
            'configuration': {
                'min_trade_size': self.min_trade_size,
                'max_position_size': self.max_position_size,
                'cash_buffer': self.cash_buffer,
                'slippage': self.slippage
            }
        }

    async def run(self, instance_config: Optional[Dict[str, Any]] = None):
        """Main processing loop with instance-specific configuration"""
        if not instance_config:
            instance_config = {}
            
        trading_interval = instance_config.get('interval_minutes', TRADE_INTERVAL)
        trade_size = instance_config.get('amount_sol', MIN_TRADE_SIZE_SOL)
        focus_tokens = instance_config.get('tokens', FOCUS_TOKENS)
        
        cprint(f"\n🚀 Trading Agent starting for instance {self.instance_id}...", "cyan")
        cprint(f"✨ Using {self.model_name} model for analysis", "cyan")
        cprint(f"⏱️ Trading interval: {trading_interval} minutes", "cyan")
        cprint(f"💰 Trade size: {trade_size} SOL", "cyan")
        cprint(f"🎯 Focus tokens: {', '.join(focus_tokens)}", "cyan")
        
        self.last_trade_time = datetime.now() - timedelta(minutes=trading_interval)
        
        try:
            while True:
                # Check system health
                await self.system_monitor.check_system_health()
                
                for token in instance_config.get('tokens', FOCUS_TOKENS):
                    try:
                        if not self.active:
                            cprint(f"⏹️ Instance {self.instance_id} stopped", "yellow")
                            return
                            
                        # Check risk limits before trading
                        risk_ok = await self._check_risk_limits()
                        if not risk_ok:
                            cprint("⚠️ Risk limits exceeded, skipping trades", "yellow")
                            continue
                            
                        # Get market data
                        token_data = await self.get_token_data(token)
                        if not token_data:
                            continue
                            
                        # Analyze with Snap strategy and DeepSeek
                        analysis = await self.analyze_market_data(token_data)
                        
                        # Execute trade if signal is strong
                        if analysis and analysis.get('confidence', 0) > 0.7 and analysis.get('action') != 'NEUTRAL':
                            trade_size = instance_config.get('amount_sol', MIN_TRADE_SIZE_SOL)
                            if analysis['metadata'].get('params'):
                                params = analysis['metadata']['params']
                                trade_size *= min(params.get('size', 1.0), instance_config.get('max_position_multiplier', 1.0))
                                
                            start_time = time.time()
                            trade_request = {
                                'token': token,
                                'amount': trade_size,
                                'direction': 'buy' if analysis['action'] == 'BUY' else 'sell',
                                'slippage_bps': self.slippage
                            }
                            signature = self.execute_trade(trade_request)
                            execution_time = int((time.time() - start_time) * 1000)
                            
                            self.performance_monitor.log_trade_metrics({
                                'token': token,
                                'direction': analysis['action'],
                                'amount': trade_size,
                                'execution_time': execution_time,
                                'slippage': self.slippage / 100,
                                'gas_cost': 0.000005,
                                'success': bool(signature)
                            })
                            
                            if signature:
                                cprint(f"✅ Trade executed for {token}", "green")
                                cprint(f"💡 Reason: {analysis['reason']}", "cyan")
                                
                                # Update last trade time
                                self.last_trade_time = datetime.now()
                                
                                # Monitor trading interval
                                self.system_monitor.monitor_trading_interval(
                                    token=token,
                                    last_trade_time=self.last_trade_time,
                                    instance_id=self.instance_id
                                )
                                
                                # Print trade summary
                                self.performance_monitor.print_summary()
                            
                    except Exception as e:
                        cprint(f"❌ Error trading {token}: {str(e)}", "red")
                        self.performance_monitor.log_trade_metrics({
                            'token': token,
                            'direction': 'NEUTRAL',
                            'amount': 0,
                            'execution_time': 0,
                            'slippage': 0,
                            'gas_cost': 0,
                            'success': False
                        })
                        
                # Print performance summary every hour
                if datetime.now().minute == 0:
                    self.performance_monitor.print_summary()
                    
                # Print performance summary and check system health
                if datetime.now().minute % 15 == 0:
                    self.performance_monitor.print_summary()
                    health_metrics = await self.system_monitor.check_system_health()
                    if health_metrics.get('rpc_latency', 0) > 5000:  # 5s latency threshold
                        cprint("⚠️ High RPC latency detected!", "yellow")
                    if health_metrics.get('cpu_usage', 0) > 80:
                        cprint("⚠️ High CPU usage detected!", "yellow")
                        
                await asyncio.sleep(trading_interval * 60)  # Convert minutes to seconds
                
        except KeyboardInterrupt:
            cprint("\n⏹️ Trading Agent shutting down...", "yellow")
            self.performance_monitor.print_summary()
            
        except Exception as e:
            cprint(f"❌ Critical error: {str(e)}", "red")
            self.performance_monitor.print_summary()
            raise  # Re-raise to handle in caller

if __name__ == "__main__":
    import asyncio
    agent = TradingAgent(instance_id="test")
    asyncio.run(agent.run())
