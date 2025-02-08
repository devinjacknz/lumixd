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
from src.strategies.snap_strategy import SnapStrategy
from src.models import ModelFactory
from src.data.jupiter_client import JupiterClient
from src.data.chainstack_client import ChainStackClient
from src.api.v1.routes.trades import TradeRequest
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
    def __init__(self, instance_id: str, model_type="deepseek", model_name="deepseek-r1:1.5b"):
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
            
    def analyze_market_data(self, token_data: dict) -> dict:
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
            self.snap_strategy.set_token(token_data.get('symbol'))
            strategy_signals = self.snap_strategy.generate_signals()
            
            # Get DeepSeek analysis
            if not self.model:
                return {
                    'action': 'NEUTRAL',
                    'confidence': 0.0,
                    'reason': 'Model not initialized',
                    'metadata': {}
                }
                
            model_analysis = self.model.analyze_trading_opportunity(token_data)
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
            
    def check_balances(self) -> tuple[bool, str]:
        """Check if wallet has sufficient balances"""
        try:
            # Check SOL balance
            client = ChainStackClient()
            wallet_address = os.getenv("WALLET_ADDRESS")
            if not wallet_address:
                return False, "Wallet address not set"
            sol_balance = client.get_wallet_balance(wallet_address)
            if not sol_balance or sol_balance < MIN_SOL_BALANCE:
                return False, f"Insufficient SOL balance: {sol_balance}"
                
            if USE_SOL_FOR_TRADING:
                if sol_balance < MIN_TRADE_SIZE_SOL + MIN_SOL_BALANCE:
                    return False, f"Insufficient SOL for trading: {sol_balance}"
                return True, "Sufficient SOL balance"
                
            # Check USDC balance if not using SOL
            usdc_balance = float(client.get_token_balance(USDC_ADDRESS) or 0)
            if usdc_balance < MIN_USDC_BALANCE:
                if CREATE_ATA_IF_MISSING:
                    jupiter = JupiterClient()
                    if jupiter.create_token_account(USDC_ADDRESS, os.getenv("WALLET_ADDRESS")):
                        return True, "Created USDC token account"
                return False, f"Insufficient USDC balance: {usdc_balance}"
                
            return True, "Sufficient balances"
        except Exception as e:
            return False, f"Error checking balances: {str(e)}"

    def execute_trade(self, trade_request: TradeRequest) -> Optional[str]:
        """Execute trade based on trade request"""
        if not self.active:
            cprint(f"❌ Instance {self.instance_id} is not active", "red")
            return None
        try:
            if not trade_request.output_token:
                cprint("❌ Trade failed: No token specified", "red")
                return None
                
            # Check balances first
            balances_ok, reason = self.check_balances()
            if not balances_ok:
                cprint(f"❌ Trade failed: {reason}", "red")
                return None
                
            # Get current positions and calculate total position value
            positions_df = fetch_wallet_holdings_og(os.getenv("WALLET_ADDRESS", ""))
            total_position = positions_df['USD Value'].sum()
            max_trade_size = float(os.getenv("SOL_BALANCE", "0")) * self.max_position_size
            
            # Check if new trade would exceed max position size
            if total_position + trade_request.amount_sol > max_trade_size:
                cprint(f"❌ Trade would exceed max position size of {max_trade_size} SOL", "red")
                return None
                
            jupiter = JupiterClient()
            
            # Calculate SOL amount for trade
            trade_amount = min(trade_request.amount_sol, MAX_ORDER_SIZE_SOL)
            client = ChainStackClient()
            start_balance = client.get_wallet_balance(os.getenv("WALLET_ADDRESS"))
            
            # Get quote with optimized parameters
            quote = jupiter.get_quote(
                trade_request.input_token,
                trade_request.output_token,
                str(int(trade_amount * 1e9)),
                use_shared_accounts=trade_request.use_shared_accounts,
                force_simpler_route=trade_request.force_simpler_route
            )
            if not quote:
                cprint("❌ Failed to get quote", "red")
                return None
                
            # Execute swap
            signature = jupiter.execute_swap(
                quote,
                os.getenv("WALLET_ADDRESS"),
                use_shared_accounts=trade_request.use_shared_accounts
            )
                
            if signature:
                end_balance = client.get_wallet_balance(os.getenv("WALLET_ADDRESS"))
                gas_cost = start_balance - end_balance - trade_amount
                metrics = {
                    'instance_id': self.instance_id,
                    'token': trade_request.output_token,
                    'direction': 'BUY',
                    'amount': trade_amount,
                    'execution_time': 0,  # Will be set by caller
                    'slippage': trade_request.slippage_bps / 100,
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
            
    def _check_risk_limits(self) -> bool:
        """Check risk management limits with circuit breakers"""
        try:
            positions = fetch_wallet_holdings_og(os.getenv("WALLET_ADDRESS", ""))
            if positions.empty:
                return True
                
            total_value = positions['USD Value'].sum()
            
            # Prepare trade data
            trade_data = {
                'portfolio_value': total_value,
                'portfolio_volatility': self._calculate_portfolio_volatility(positions),
                'market_volatility': self.calculate_volatility("SOL"),  # Use SOL as market indicator
            }
            
            # Check individual position sizes
            for _, pos in positions.iterrows():
                size_percentage = (pos['USD Value'] / total_value) * 100
                trade_data['unrealized_loss_percentage'] = -pos.get('unrealized_pnl_percentage', 0)
                
                # Check circuit breakers
                is_safe, reason = self.check_circuit_breakers(trade_data)
                if not is_safe:
                    print(f"🚨 Circuit breaker: {reason}")
                    return False
                    
            return True
            
        except Exception as e:
            print(f"Error checking risk limits: {e}")
            return False
            
    def _calculate_portfolio_volatility(self, positions: pd.DataFrame) -> float:
        """Calculate portfolio volatility"""
        try:
            # Simple volatility calculation based on position values
            if positions.empty:
                return 0
                
            values = positions['USD Value']
            return float(values.std() / values.mean()) if values.mean() > 0 else 0
            
        except Exception as e:
            print(f"Error calculating portfolio volatility: {e}")
            return 1.0  # Return high volatility on error

    def get_token_data(self, token: str) -> dict:
        """Get token market data"""
        try:
            from src.data.chainstack_client import ChainStackClient
            client = ChainStackClient()
            return client.get_token_data(token)
        except Exception as e:
            print(f"Error getting token data: {e}")
            return {}

    def calculate_volatility(self, token: str) -> float:
        """Calculate token volatility using ATR"""
        try:
            token_data = self.get_token_data(token)
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
            print(f"Error calculating volatility: {e}")
            return 0.2

    def generate_trading_signal(self, token: str) -> dict:
        """Generate trading signal using DeepSeek model and Snap strategy"""
        try:
            token_data = self.get_token_data(token)
            if not token_data:
                return {
                    'signal': 0.0,
                    'direction': 'NEUTRAL',
                    'confidence': 0.0,
                    'metadata': {}
                }
                
            analysis = self.analyze_market_data(token_data)
            return {
                'signal': analysis['confidence'],
                'direction': analysis['action'],
                'confidence': analysis['confidence'],
                'metadata': analysis['metadata']
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

    def run(self, instance_config: Optional[Dict[str, Any]] = None):
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
        
        last_trade_time = datetime.now() - timedelta(minutes=trading_interval)
        
        try:
            while True:
                # Check system health
                self.system_monitor.check_system_health()
                
                for token in instance_config.get('tokens', FOCUS_TOKENS):
                    try:
                        if not self.active:
                            cprint(f"⏹️ Instance {self.instance_id} stopped", "yellow")
                            return
                            
                        # Get market data
                        token_data = self.get_token_data(token)
                        if not token_data:
                            continue
                            
                        # Analyze with Snap strategy and DeepSeek
                        analysis = self.analyze_market_data(token_data)
                        
                        # Execute trade if signal is strong
                        if analysis['confidence'] > 0.7 and analysis['action'] != 'NEUTRAL':
                            trade_size = instance_config.get('amount_sol', MIN_TRADE_SIZE_SOL)
                            if analysis['metadata'].get('params'):
                                params = analysis['metadata']['params']
                                trade_size *= min(params.get('size', 1.0), instance_config.get('max_position_multiplier', 1.0))
                                
                            start_time = time.time()
                            trade_request = TradeRequest(
                                input_token="So11111111111111111111111111111111111111112",
                                output_token=token,
                                amount_sol=trade_size,
                                slippage_bps=self.slippage,
                                use_shared_accounts=True,
                                force_simpler_route=True
                            )
                            success = self.execute_trade(trade_request)
                            execution_time = int((time.time() - start_time) * 1000)
                            
                            self.performance_monitor.log_trade_metrics({
                                'token': token,
                                'direction': analysis['action'],
                                'amount': trade_size,
                                'execution_time': execution_time,
                                'slippage': self.slippage * 100,
                                'gas_cost': 0.000005,
                                'success': success
                            })
                            
                            if success:
                                cprint(f"✅ Trade executed for {token}", "green")
                                cprint(f"💡 Reason: {analysis['reason']}", "cyan")
                                
                            self.system_monitor.monitor_trading_interval(token, last_trade_time)
                            last_trade_time = datetime.now()
                            
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
                    health_metrics = self.system_monitor.check_system_health()
                    if health_metrics.get('rpc_latency', 0) > 5000:  # 5s latency threshold
                        cprint("⚠️ High RPC latency detected!", "yellow")
                    if health_metrics.get('cpu_usage', 0) > 80:
                        cprint("⚠️ High CPU usage detected!", "yellow")
                        
                time.sleep(TRADE_INTERVAL)
                
        except KeyboardInterrupt:
            print("\nTrading Agent shutting down...")
            self.performance_monitor.print_summary()
            
        except Exception as e:
            cprint(f"❌ Critical error: {str(e)}", "red")
            self.performance_monitor.print_summary()

if __name__ == "__main__":
    agent = TradingAgent()
    agent.run()
