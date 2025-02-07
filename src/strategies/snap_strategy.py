from .base_strategy import BaseStrategy
import numpy as np
from src.nice_funcs import calculate_atr
from src.data.chainstack_client import ChainStackClient

class SnapStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(name="Snap Strategy")
        self.description = "Dynamic Parameter Snap Strategy"
        self.client = ChainStackClient()
        
    def get_dynamic_params(self, atr: float, liq_score: float) -> dict:
        base = {
            'low': {'tp': 0.08, 'sl': 0.03, 'size': 0.05},
            'mid': {'tp': 0.12, 'sl': 0.05, 'size': 0.03},
            'high': {'tp': 0.18, 'sl': 0.08, 'size': 0.02}
        }
        return base['high'] if liq_score > 0.8 else base['low'] if atr < 0.5 else base['mid']
        
    def calculate_liquidity_score(self, data: dict) -> float:
        try:
            volume = float(data.get('volume', 0))
            market_cap = float(data.get('market_cap', 0))
            if market_cap == 0:
                return 0.0
            return min(1.0, volume / market_cap)
        except:
            return 0.0
            
    def calculate_signal_strength(self, data: dict) -> float:
        try:
            prices = data.get('close_prices', [])
            if len(prices) < 20:
                return 0.0
                
            # Calculate momentum
            momentum = (prices[-1] / prices[-20] - 1) if prices[-20] > 0 else 0
            
            # Calculate volatility
            returns = np.diff(prices) / prices[:-1]
            volatility = float(np.std(returns))
            
            # Calculate volume trend
            volumes = data.get('volumes', [])
            vol_ma = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else 0
            vol_trend = volumes[-1] / vol_ma if vol_ma > 0 else 0
            
            # Combine factors
            signal = (
                0.4 * min(1.0, abs(momentum)) +
                0.3 * (1.0 - min(1.0, volatility)) +
                0.3 * min(1.0, vol_trend)
            )
            
            return float(signal)
        except:
            return 0.0
            
    def determine_direction(self, data: dict) -> str:
        try:
            prices = data.get('close_prices', [])
            if len(prices) < 20:
                return 'NEUTRAL'
                
            momentum = prices[-1] / prices[-20] - 1
            return 'BUY' if momentum > 0 else 'SELL'
        except:
            return 'NEUTRAL'
            
    def generate_signals(self) -> dict:
        try:
            data = self.get_market_data()
            if not data:
                return {
                    'token': self.token,
                    'signal': 0.0,
                    'direction': 'NEUTRAL',
                    'metadata': {'error': 'No market data'}
                }
                
            atr = calculate_atr(
                data.get('high_prices', []),
                data.get('low_prices', []),
                data.get('close_prices', [])
            )
            
            liq_score = self.calculate_liquidity_score(data)
            params = self.get_dynamic_params(atr, liq_score)
            signal = self.calculate_signal_strength(data)
            direction = self.determine_direction(data)
            
            return {
                'token': self.token,
                'signal': signal,
                'direction': direction,
                'metadata': {
                    'params': params,
                    'atr': float(atr),
                    'liq_score': float(liq_score)
                }
            }
        except Exception as e:
            return {
                'token': self.token,
                'signal': 0.0,
                'direction': 'NEUTRAL',
                'metadata': {'error': str(e)}
            }
