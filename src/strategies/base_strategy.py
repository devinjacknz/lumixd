"""
Lumix Base Strategy Class
All custom strategies should inherit from this
"""

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from termcolor import cprint

class BaseStrategy(ABC):
    def __init__(self, name: str, params: Dict[str, Any] = None):
        self.name = name
        self.token = None
        params = params or {}
        self.max_position_size = float(params.get('max_position_size', 0.2))
        self.stop_loss = float(params.get('stop_loss', -0.05))
        self.take_profit = float(params.get('take_profit', 0.1))
        self.slippage_bps = int(params.get('slippage_bps', 250))
        self.cash_buffer = float(params.get('cash_buffer', 0.3))
        self.use_shared_accounts = bool(params.get('use_shared_accounts', True))
        self.force_simpler_route = bool(params.get('force_simpler_route', True))
        
    def get_market_data(self) -> dict:
        """Get market data for analysis"""
        from src.data.chainstack_client import ChainStackClient
        client = ChainStackClient()
        return client.get_token_data(self.token)
        
    def set_token(self, token: str):
        """Set token for analysis"""
        self.token = token

    @abstractmethod
    def generate_signals(self) -> dict:
        """
        Generate trading signals
        Returns:
            dict: {
                'token': str,          # Token address
                'signal': float,       # Signal strength (0-1)
                'direction': str,      # 'BUY', 'SELL', or 'NEUTRAL'
                'metadata': dict       # Optional strategy-specific data
            }
        """
        pass
        
    def get_trade_parameters(self) -> Dict[str, Any]:
        """Get strategy trade parameters"""
        return {
            "max_position_size": self.max_position_size,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "slippage_bps": self.slippage_bps,
            "cash_buffer": self.cash_buffer,
            "use_shared_accounts": self.use_shared_accounts,
            "force_simpler_route": self.force_simpler_route
        }
        
    def validate_trade(self, amount: float, balance: float) -> bool:
        """Validate trade against strategy parameters"""
        try:
            if amount <= 0:
                cprint("❌ Invalid trade amount", "red")
                return False
                
            if balance <= 0:
                cprint("❌ Insufficient balance", "red")
                return False
                
            position_value = amount
            total_value = balance
            
            # Check position size
            if position_value / total_value > self.max_position_size:
                cprint(f"❌ Position size {position_value/total_value:.1%} exceeds max {self.max_position_size:.1%}", "red")
                return False
                
            # Check cash buffer
            remaining_cash = (total_value - position_value) / total_value
            if remaining_cash < self.cash_buffer:
                cprint(f"❌ Remaining cash {remaining_cash:.1%} below buffer {self.cash_buffer:.1%}", "red")
                return False
                
            return True
        except Exception as e:
            cprint(f"❌ Error validating trade: {str(e)}", "red")
            return False            