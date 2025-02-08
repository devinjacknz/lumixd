"""
Token Information Module
Provides token lookup and market data functionality using Chainstack RPC
"""

from typing import Dict, Optional, List
import pandas as pd
from termcolor import cprint
from src.data.chainstack_client import ChainStackClient
from src.config.settings import TRADING_CONFIG

class TokenInfoModule:
    def __init__(self):
        self.client = ChainStackClient()
        self.tokens = TRADING_CONFIG["tokens"]
        
    async def get_token_info(self, identifier: str) -> Dict:
        """Get token information by name, address, or symbol"""
        try:
            # Check if identifier is a known token symbol
            if identifier.upper() in self.tokens:
                address = self.tokens[identifier.upper()]
            else:
                address = identifier
                
            # Get token metadata
            metadata = await self.client.get_token_metadata(address)
            if not metadata:
                raise ValueError(f"Token not found: {identifier}")
                
            # Get market data
            market_data = await self.get_market_data(address)
            
            return {
                "address": address,
                "metadata": metadata,
                "market": market_data
            }
        except Exception as e:
            cprint(f"❌ Failed to get token info: {str(e)}", "red")
            return {}
            
    async def get_market_data(self, token_address: str) -> Dict:
        """Get token market data including price, volume, and liquidity"""
        try:
            # Get token data with market metrics
            token_data = await self.client.get_token_data(token_address)
            
            # Get token supply info
            supply_info = await self.client.get_token_supply(token_address)
            
            # Get top token holders
            holders = await self.client.get_token_holders(token_address)
            
            # Calculate liquidity score based on holder distribution
            liquidity_score = self._calculate_liquidity_score(holders)
            
            return {
                "price": token_data["Close"].iloc[-1] if not token_data.empty else 0,
                "volume_24h": token_data["Volume"].sum() if not token_data.empty else 0,
                "liquidity_score": liquidity_score,
                "supply": supply_info,
                "holders": holders[:10]  # Top 10 holders
            }
        except Exception as e:
            cprint(f"❌ Failed to get market data: {str(e)}", "red")
            return {}
            
    def _calculate_liquidity_score(self, holders: List[Dict]) -> float:
        """Calculate liquidity score based on holder distribution"""
        try:
            if not holders:
                return 0.0
                
            total_supply = sum(float(h["amount"]) for h in holders)
            if total_supply == 0:
                return 0.0
                
            # Calculate Herfindahl-Hirschman Index (HHI) for concentration
            holder_shares = [(float(h["amount"]) / total_supply) ** 2 for h in holders]
            hhi = sum(holder_shares)
            
            # Convert HHI to liquidity score (0-1)
            # Lower HHI means better distribution
            liquidity_score = 1 - (hhi - (1/len(holders))) / (1 - (1/len(holders)))
            return max(0.0, min(1.0, liquidity_score))
        except Exception as e:
            cprint(f"❌ Failed to calculate liquidity score: {str(e)}", "red")
            return 0.0
            
    async def get_token_history(self, token_address: str, days: int = 7) -> pd.DataFrame:
        """Get token trading history"""
        try:
            # Get historical token data
            token_data = await self.client.get_token_data(token_address, days_back=days)
            
            # Get recent transactions
            transactions = await self.client.get_signatures_for_address(token_address, limit=100)
            
            return {
                "price_history": token_data,
                "transactions": transactions
            }
        except Exception as e:
            cprint(f"❌ Failed to get token history: {str(e)}", "red")
            return {
                "price_history": pd.DataFrame(),
                "transactions": []
            }
            
    async def analyze_position(self, token_address: str, position_size: float) -> Dict:
        """Analyze token position"""
        try:
            market_data = await self.get_market_data(token_address)
            token_data = await self.client.get_token_data(token_address)
            
            if token_data.empty:
                return {}
                
            # Calculate position metrics
            position_value = position_size * market_data["price"]
            daily_volume = market_data["volume_24h"]
            
            return {
                "position_value": position_value,
                "position_size": position_size,
                "volume_ratio": position_value / daily_volume if daily_volume > 0 else 0,
                "liquidity_score": market_data["liquidity_score"],
                "risk_level": self._calculate_risk_level(position_value, daily_volume, market_data["liquidity_score"])
            }
        except Exception as e:
            cprint(f"❌ Failed to analyze position: {str(e)}", "red")
            return {}
            
    def _calculate_risk_level(self, position_value: float, daily_volume: float, liquidity_score: float) -> str:
        """Calculate risk level based on position metrics"""
        try:
            # Volume impact
            volume_impact = position_value / daily_volume if daily_volume > 0 else float('inf')
            
            if volume_impact > 0.1 or liquidity_score < 0.3:
                return "HIGH"
            elif volume_impact > 0.05 or liquidity_score < 0.5:
                return "MEDIUM"
            else:
                return "LOW"
        except Exception:
            return "UNKNOWN"
