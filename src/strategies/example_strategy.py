"""
Example Strategy
Simple Moving Average Crossover Strategy Example
A basic strategy implementation using TA-Lib indicators
"""

from .base_strategy import BaseStrategy
import talib
import numpy as np

class ExampleStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(name="Example Strategy")
        self.description = "Simple Moving Average Crossover Strategy"
        self.fast_period = 20
        self.slow_period = 50
        
    def generate_signals(self) -> dict:
        try:
            data = self.get_market_data()
            close = data['close'].values
            
            # Calculate SMAs
            sma_fast = talib.SMA(close, timeperiod=self.fast_period)
            sma_slow = talib.SMA(close, timeperiod=self.slow_period)
            
            # Generate signal
            signal = 0
            if sma_fast[-1] > sma_slow[-1] and sma_fast[-2] <= sma_slow[-2]:
                signal = 1  # Buy signal
            elif sma_fast[-1] < sma_slow[-1] and sma_fast[-2] >= sma_slow[-2]:
                signal = -1  # Sell signal
                
            return {
                'token': self.token,
                'signal': abs(signal),
                'direction': 'BUY' if signal > 0 else 'SELL' if signal < 0 else 'NEUTRAL',
                'metadata': {
                    'sma_fast': float(sma_fast[-1]),
                    'sma_slow': float(sma_slow[-1])
                }
            }
        except Exception as e:
            print(f"Error generating signals: {e}")
            return {
                'token': self.token,
                'signal': 0.0,
                'direction': 'NEUTRAL',
                'metadata': {'error': str(e)}
            }
