"""
Trading Agent
Handles automated trading execution and analysis
"""

import os
import sys
import time
import aiohttp
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
from src.data.chainstack_client import ChainStackClient
from src.strategies.snap_strategy import SnapStrategy
from src.monitoring.performance_monitor import PerformanceMonitor
from src.monitoring.system_monitor import SystemMonitor
from src.agents.base_agent import BaseAgent
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

class TradingAgent(BaseAgent):
    def __init__(self, agent_type: str = 'trading', instance_id: str = 'main', model_type: str = "deepseek-r1", model_name: str = "deepseek-r1:1.5b"):
        super().__init__(agent_type=agent_type, instance_id=instance_id)
        self.model_type = model_type
        self.model_name = model_name
        self.model_factory = ModelFactory()
        self.model = self.model_factory.get_model('ollama')  # Use ollama as the model provider
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
        self.chainstack_client = ChainStackClient()
        self.sol_token = "So11111111111111111111111111111111111111112"
        
        # Initialize position tracking
        self.chainstack_client = ChainStackClient()
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
            signature = await self.execute_trade(trade_request)
            
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
            
    async def get_token_price(self, token: str) -> float:
        """Get token price in SOL"""
        try:
            quote = await self.jupiter_client.get_quote(
                input_mint=token,
                output_mint=self.jupiter_client.sol_token,
                amount="1000000000",  # 1 unit in smallest denomination
                use_shared_accounts=True,
                force_simpler_route=True
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
                
            sol_balance = await self.chainstack_client.get_wallet_balance(wallet_address)
            if not sol_balance or float(sol_balance) < MIN_SOL_BALANCE:
                return False, f"Insufficient SOL balance: {sol_balance}"
                
            if USE_SOL_FOR_TRADING:
                if float(sol_balance) < MIN_TRADE_SIZE_SOL + MIN_SOL_BALANCE:
                    return False, f"Insufficient SOL for trading: {sol_balance}"
                return True, "Sufficient SOL balance"
                
            # Check USDC balance if not using SOL
            usdc_balance = await self.chainstack_client.get_token_balance(USDC_ADDRESS, wallet_address)
            if not usdc_balance or float(usdc_balance) < MIN_USDC_BALANCE:
                if CREATE_ATA_IF_MISSING:
                    try:
                        success = await self.jupiter_client.create_token_account(USDC_ADDRESS, wallet_address)
                        if success:
                            return True, "Created USDC token account"
                    except Exception as e:
                        return False, f"Failed to create token account: {str(e)}"
                return False, f"Insufficient USDC balance: {usdc_balance}"
                
            return True, "Sufficient balances"
        except Exception as e:
            return False, f"Error checking balances: {str(e)}"

    async def execute_trade(self, trade_request: Dict[str, Any]) -> Optional[str]:
        """Execute trade based on trade request"""
        try:
            if not self.active:
                cprint(f"❌ Instance {self.instance_id} is not active", "red")
                return None
                
            wallet_address = os.getenv("WALLET_ADDRESS")
            if not wallet_address:
                cprint("❌ Trade failed: No wallet address configured", "red")
                return None
                
            if not trade_request.get('token'):
                cprint("❌ Trade failed: No token specified", "red")
                return None
                
            # Check balances first
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.jupiter_client.rpc_url,
                        headers={"Content-Type": "application/json"},
                        json={
                            "jsonrpc": "2.0",
                            "id": "get-balance",
                            "method": "getBalance",
                            "params": [wallet_address]
                        }
                    ) as response:
                        response.raise_for_status()
                        result = await response.json()
                        balance = float(result.get("result", {}).get("value", 0)) / 1e9
                        if balance < self.min_trade_size:
                            cprint(f"❌ Trade failed: Insufficient SOL balance: {balance}", "red")
                            return None
            except Exception as e:
                cprint(f"❌ Trade failed: Error checking balance: {str(e)}", "red")
                return None
                
            # Get quote with optimized parameters
            quote = await self.jupiter_client.get_quote(
                input_mint=self.sol_token if trade_request.get('direction') == 'buy' else trade_request['token'],
                output_mint=trade_request['token'] if trade_request.get('direction') == 'buy' else self.sol_token,
                amount=str(int(float(trade_request['amount']) * 1e9))
            )
            if not quote:
                cprint("❌ Failed to get quote", "red")
                return None
                
            # Execute swap
            signature = await self.jupiter_client.execute_swap(
                quote_response=quote,
                wallet_pubkey=wallet_address,
                use_shared_accounts=True
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
                await self.performance_monitor.log_trade_metrics(metrics)
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
        
    async def execute_dialogue_trade(self, dialogue_input: str) -> dict:
        """Execute trade based on dialogue input with bilingual support"""
        try:
            # Parse trading instruction using DeepSeek model
            if not self.model:
                return {
                    'status': 'error',
                    'message': 'Model not initialized',
                    'message_cn': '模型未初始化'
                }
                
            trade_params = await self.model.analyze_trade(dialogue_input)
            if not trade_params or 'error' in trade_params:
                return {
                    'status': 'error',
                    'message': trade_params.get('error', 'Failed to parse trade instruction'),
                    'message_cn': trade_params.get('error_cn', '无法解析交易指令')
                }
                
            # Validate parameters
            token = trade_params.get('token', '').upper()
            amount = float(trade_params.get('amount', 0))
            direction = trade_params.get('direction', '').lower()
            slippage_bps = int(trade_params.get('slippage_bps', self.slippage))
            
            # Basic parameter validation
            if not token or amount <= 0 or direction not in ['buy', 'sell']:
                return {
                    'status': 'error',
                    'message': 'Invalid trade parameters',
                    'message_cn': '交易参数无效'
                }
                
            # Convert token symbol to address
            if token == 'SOL':
                token = self.sol_token
            elif token == 'USDC':
                token = USDC_ADDRESS
                return {
                    'status': 'error',
                    'message': 'Invalid trade parameters',
                    'message_cn': '交易参数无效'
                }
                
            # Check balances and risk limits
            balances_ok, balance_msg = await self.check_balances()
            if not balances_ok:
                return {
                    'status': 'error',
                    'message': f'Insufficient balance: {balance_msg}',
                    'message_cn': f'余额不足：{balance_msg}'
                }
                
            # Check risk limits
            risk_ok = await self._check_risk_limits()
            if not risk_ok:
                return {
                    'status': 'error',
                    'message': 'Risk limits exceeded',
                    'message_cn': '超出风险限制'
                }
                
            # Get risk analysis from model
            if not self.model:
                return {
                    'status': 'error',
                    'message': 'Model not initialized',
                    'message_cn': '模型未初始化'
                }
                
            risk_check = await self.model.check_risk_dialogue({
                'token': token,
                'amount': amount,
                'direction': direction,
                'slippage': slippage_bps / 10000
            })
            
            if not risk_check.get('approved', False):
                return {
                    'status': 'rejected',
                    'message': risk_check.get('reason', 'Risk check failed'),
                    'message_cn': risk_check.get('reason_cn', '风险检查未通过')
                }
                
            # Execute trade
            trade_request = {
                'token': token,
                'amount': amount,
                'direction': direction,
                'slippage_bps': slippage_bps
            }
            
            signature = await self.execute_trade(trade_request)
            if signature:
                return {
                    'status': 'success',
                    'message': f'Trade executed successfully: {signature}',
                    'message_cn': f'交易执行成功：{signature}',
                    'signature': signature
                }
            else:
                return {
                    'status': 'error',
                    'message': 'Trade execution failed',
                    'message_cn': '交易执行失败'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error executing trade: {str(e)}',
                'message_cn': f'交易执行错误：{str(e)}'
            }

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
                            signature = await self.execute_trade(trade_request)
                            execution_time = int((time.time() - start_time) * 1000)
                            
                            metrics = {
                                'token': token,
                                'direction': analysis['action'],
                                'amount': trade_size,
                                'execution_time': execution_time,
                                'slippage': self.slippage / 100,
                                'gas_cost': 0.000005,
                                'success': bool(signature)
                            }
                            try:
                                await self.performance_monitor.log_trade_metrics(metrics)
                            except Exception as e:
                                cprint(f"❌ Error logging trade metrics: {str(e)}", "red")
                            
                            if signature:
                                cprint(f"✅ Trade executed for {token}", "green")
                                cprint(f"💡 Reason: {analysis['reason']}", "cyan")
                                
                                # Update last trade time
                                self.last_trade_time = datetime.now()
                                
                                # Monitor trading interval
                                await self.system_monitor.monitor_trading_interval(
                                    token=token,
                                    last_trade_time=self.last_trade_time,
                                    instance_id=self.instance_id
                                )
                                
                                # Print trade summary
                                self.performance_monitor.print_summary()
                            
                    except Exception as e:
                        cprint(f"❌ Error trading {token}: {str(e)}", "red")
                        await self.performance_monitor.log_trade_metrics({
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
