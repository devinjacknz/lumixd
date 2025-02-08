from typing import Dict, Any, Optional
from src.strategies.base_strategy import BaseStrategy
from src.data.chainstack_client import ChainStackClient
from termcolor import cprint

class MultiFactorStrategy(BaseStrategy):
    def __init__(self, params: Dict[str, Any]):
        super().__init__(name="multi_factor")
        self.max_position_size = float(params.get('max_position_size', 0.2))
        self.stop_loss = float(params.get('stop_loss', -0.05))
        self.take_profit = float(params.get('take_profit', 0.1))
        self.slippage_bps = int(params.get('slippage_bps', 250))
        self.cash_buffer = float(params.get('cash_buffer', 0.3))
        self.client = ChainStackClient()
        
    def generate_signals(self) -> dict:
        try:
            market_data = self.get_market_data()
            if not market_data:
                return {
                    'token': self.token,
                    'signal': 0,
                    'direction': 'NEUTRAL',
                    'metadata': {'error': 'No market data available'}
                }
                
            current_price = float(market_data.get('price', 0))
            volume_24h = float(market_data.get('volume_24h', 0))
            liquidity = float(market_data.get('liquidity', 0))
            
            # Calculate signal strength (0-1)
            signal_strength = min(1.0, max(0.0, liquidity / volume_24h if volume_24h > 0 else 0))
            
            # Determine direction based on market conditions
            direction = 'NEUTRAL'
            if signal_strength > 0.7:
                direction = 'BUY'
            elif signal_strength < 0.3:
                direction = 'SELL'
                
            return {
                'token': self.token,
                'signal': signal_strength,
                'direction': direction,
                'metadata': {
                    'price': current_price,
                    'volume_24h': volume_24h,
                    'liquidity': liquidity
                }
            }
        except Exception as e:
            cprint(f"❌ Error generating signals: {str(e)}", "red")
            return {
                'token': self.token,
                'signal': 0,
                'direction': 'NEUTRAL',
                'metadata': {'error': str(e)}
            }
