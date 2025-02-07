"""
Lumix Base Strategy Class
All custom strategies should inherit from this
"""

class BaseStrategy:
    def __init__(self, name: str):
        self.name = name
        self.token = None
        
    def get_market_data(self) -> dict:
        """Get market data for analysis"""
        from src.data.chainstack_client import ChainStackClient
        client = ChainStackClient()
        return client.get_token_data(self.token)
        
    def set_token(self, token: str):
        """Set token for analysis"""
        self.token = token

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
        raise NotImplementedError("Strategy must implement generate_signals()")   