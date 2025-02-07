"""
Trading Agent
Handles automated trading execution and analysis
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from termcolor import cprint
from dotenv import load_dotenv
from src import nice_funcs as n
from src.data.ohlcv_collector import collect_all_tokens
from src.agents.focus_agent import MODEL_TYPE, MODEL_NAME
from src.models import ModelFactory
from src.data.jupiter_client import JupiterClient
from src.config import (
    USDC_SIZE,
    MAX_LOSS_PERCENTAGE,
    SLIPPAGE
)
from src.nice_funcs import (
    market_buy,
    market_sell,
    fetch_wallet_holdings_og,
    calculate_atr
)

# Load environment variables
load_dotenv()

class TradingAgent:
    def __init__(self, model_type=MODEL_TYPE, model_name=MODEL_NAME):
        self.model_type = model_type
        self.model_name = model_name
        self.model_factory = ModelFactory()
        self.model = self.model_factory.get_model(self.model_type)
        self.min_trade_size = 0.01
        self.max_position_size = 0.20
        self.cash_buffer = 0.30
        self.slippage = 0.025
        
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
        """Analyze market data for trading opportunities using multi-factor model"""
        if not token_data or not isinstance(token_data, dict):
            return {
                'action': 'hold',
                'confidence': 0.0,
                'reason': 'Invalid token data',
                'metadata': {}
            }
            
        try:
            context = f"""
            Token: {token_data.get('symbol')}
            Price: {token_data.get('price')}
            Volume: {token_data.get('volume')}
            Market Cap: {token_data.get('market_cap')}
            """
            
            if not self.model:
                return {
                    'action': 'hold',
                    'confidence': 0.0,
                    'reason': 'Model not initialized',
                    'metadata': {}
                }
                
            # Get AI analysis
            response = self.model.generate_response(
                system_prompt="You are the Trading Analysis AI. Analyze market data.",
                user_content=context,
                temperature=0.7
            )
            analysis = self._parse_analysis(response)
            
            if analysis:
                # Calculate composite signal
                strategy_signal = float(analysis.get('confidence', 0))
                sentiment_score = float(token_data.get('sentiment_score', 0))
                volatility = float(token_data.get('volatility', 0.2))
                
                # Adjust weights based on market condition
                market_condition = self.detect_market_condition(token_data)
                if market_condition == 'trending':
                    signal_strength = self.calculate_signal_strength(
                        strategy_signal * 1.2,  # Boost strategy signal in trends
                        sentiment_score * 0.8,  # Reduce sentiment impact
                        volatility
                    )
                else:
                    signal_strength = self.calculate_signal_strength(
                        strategy_signal,
                        sentiment_score,
                        volatility
                    )
                
                # Execute trade if signal is strong enough
                if signal_strength > 0.7 and analysis.get('action') != 'hold':
                    position_size = self.calculate_position_size(token_data)
                    if position_size > 0:
                        self.execute_trade(
                            token=str(token_data.get('symbol')),
                            direction=analysis.get('action', 'NEUTRAL').upper(),
                            amount=position_size
                        )
                        
                analysis['signal_strength'] = signal_strength
                return analysis
                
            return {
                'action': 'hold',
                'confidence': 0.0,
                'reason': 'Analysis failed',
                'metadata': {}
            }
                
        except Exception as e:
            print(f"Error analyzing market data: {e}")
            return {
                'action': 'hold',
                'confidence': 0.0,
                'reason': f'Error: {str(e)}',
                'metadata': {}
            }
            
    def execute_trade(self, token: str | None, direction: str, amount: float) -> bool:
        """Execute trade based on signal"""
        try:
            if not token or not self._check_risk_limits():
                return False
                
            jupiter = JupiterClient()
            jupiter.slippage_bps = int(self.slippage * 100)
            
            if direction == 'BUY':
                success = market_buy(str(token), amount, int(self.slippage * 100))
            elif direction == 'SELL':
                success = market_sell(str(token), amount, int(self.slippage * 100))
            else:
                return False
                
            return success
        except Exception as e:
            print(f"Error executing trade: {e}")
            return False
            
    def _check_risk_limits(self) -> bool:
        """Check risk management limits with circuit breakers"""
        try:
            positions = fetch_wallet_holdings_og(os.getenv("WALLET_ADDRESS", ""))
            if positions.empty:
                return True
                
            total_value = positions['USD Value'].sum()
            
            # Check individual position sizes
            for _, pos in positions.iterrows():
                size_percentage = (pos['USD Value'] / total_value) * 100
                
                # Circuit breaker 1: Position size limit
                if size_percentage > self.max_position_size:
                    print(f"🚨 Circuit breaker: Position size {size_percentage:.2f}% exceeds limit {self.max_position_size}%")
                    return False
                    
                # Circuit breaker 2: Loss limit per position
                if pos.get('unrealized_pnl_percentage', 0) < -MAX_LOSS_PERCENTAGE:
                    print(f"🚨 Circuit breaker: Loss {pos.get('unrealized_pnl_percentage', 0):.2f}% exceeds limit {MAX_LOSS_PERCENTAGE}%")
                    return False
                    
            # Circuit breaker 3: Portfolio volatility
            portfolio_volatility = self._calculate_portfolio_volatility(positions)
            if portfolio_volatility > 0.3:  # 30% volatility threshold
                print(f"🚨 Circuit breaker: Portfolio volatility {portfolio_volatility:.2f} exceeds threshold")
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
        """Generate trading signal with weighted factors"""
        try:
            # Get strategy signal (60%)
            strategy_signal = self.analyze_market_data({'symbol': token}).get('confidence', 0)
            strategy_weight = 0.6
            
            # Get sentiment signal (30%)
            from src.agents.sentiment_agent import SentimentAgent
            sentiment_agent = SentimentAgent()
            sentiment_score = sentiment_agent.get_latest_sentiment_time()
            sentiment_weight = 0.3
            
            # Get volatility signal (10%)
            volatility = self.calculate_volatility(token)
            volatility_signal = 1 if volatility < 0.3 else 0
            volatility_weight = 0.1
            
            # Combine signals
            total_signal = (
                strategy_signal * strategy_weight +
                sentiment_score * sentiment_weight +
                volatility_signal * volatility_weight
            )
            
            return {
                'signal': total_signal,
                'strategy': strategy_signal,
                'sentiment': sentiment_score,
                'volatility': volatility_signal
            }
        except Exception as e:
            print(f"❌ Error generating trading signal: {str(e)}", "red")
            return None

    def run(self):
        """Main processing loop"""
        print("\nTrading Agent starting...")
        print("Ready to analyze market data!")
        
        try:
            while True:
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\nTrading Agent shutting down...")

if __name__ == "__main__":
    agent = TradingAgent()
    agent.run()
