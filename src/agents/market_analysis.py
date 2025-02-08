"""
Market Analysis Service
Provides price trend and liquidity analysis using Chainstack RPC and DeepSeek model
"""

from typing import Dict, List, Optional
import pandas as pd
from termcolor import cprint
from src.data.chainstack_client import ChainStackClient
from src.models.deepseek_model import DeepSeekModel
from src.config.settings import TRADING_CONFIG

class MarketAnalysisService:
    def __init__(self):
        self.chain_client = ChainStackClient()
        self.model = DeepSeekModel()
        self.config = TRADING_CONFIG["risk_parameters"]
        
    async def analyze_price_trend(self, token_address: str, days: int = 7) -> Dict:
        """Analyze token price trends using historical data"""
        try:
            # Get historical token data
            token_data = await self.chain_client.get_token_data(token_address, days_back=days)
            if token_data.empty:
                return {"error": "No price data available"}
                
            # Calculate technical indicators
            token_data['MA20'] = token_data['Close'].rolling(window=20).mean()
            token_data['MA40'] = token_data['Close'].rolling(window=40).mean()
            token_data['RSI'] = self._calculate_rsi(token_data['Close'])
            
            # Get recent price movement
            current_price = token_data['Close'].iloc[-1]
            price_change_24h = (current_price - token_data['Close'].iloc[-2]) / token_data['Close'].iloc[-2] * 100
            
            # Analyze trend using DeepSeek
            trend_analysis = await self._analyze_trend_with_ai(token_data)
            
            return {
                "current_price": current_price,
                "price_change_24h": price_change_24h,
                "ma20": token_data['MA20'].iloc[-1],
                "ma40": token_data['MA40'].iloc[-1],
                "rsi": token_data['RSI'].iloc[-1],
                "trend": trend_analysis,
                "indicators": {
                    "price_above_ma20": current_price > token_data['MA20'].iloc[-1],
                    "ma20_above_ma40": token_data['MA20'].iloc[-1] > token_data['MA40'].iloc[-1],
                    "rsi_oversold": token_data['RSI'].iloc[-1] < 30,
                    "rsi_overbought": token_data['RSI'].iloc[-1] > 70
                }
            }
        except Exception as e:
            cprint(f"❌ Failed to analyze price trend: {str(e)}", "red")
            return {"error": str(e)}
            
    async def analyze_liquidity(self, token_address: str) -> Dict:
        """Analyze token liquidity using on-chain data"""
        try:
            # Get token holders
            holders = await self.chain_client.get_token_holders(token_address)
            
            # Get recent transactions
            transactions = await self.chain_client.get_signatures_for_address(token_address, limit=100)
            
            # Calculate concentration metrics
            total_supply = sum(float(h["amount"]) for h in holders)
            top_holders = sorted(holders, key=lambda x: float(x["amount"]), reverse=True)[:10]
            top_holders_share = sum(float(h["amount"]) for h in top_holders) / total_supply
            
            # Calculate transaction metrics
            tx_count = len(transactions)
            
            # Get market data for volume analysis
            token_data = await self.chain_client.get_token_data(token_address)
            daily_volume = token_data['Volume'].sum() if not token_data.empty else 0
            
            return {
                "liquidity_metrics": {
                    "total_supply": total_supply,
                    "holder_count": len(holders),
                    "top_holders_share": top_holders_share,
                    "daily_volume": daily_volume,
                    "tx_count_24h": tx_count
                },
                "risk_assessment": {
                    "concentration_risk": self._assess_concentration_risk(top_holders_share),
                    "volume_adequacy": self._assess_volume_adequacy(daily_volume),
                    "holder_distribution": self._assess_holder_distribution(holders)
                }
            }
        except Exception as e:
            cprint(f"❌ Failed to analyze liquidity: {str(e)}", "red")
            return {"error": str(e)}
            
    def _calculate_rsi(self, prices: pd.Series, periods: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        deltas = prices.diff()
        gain = (deltas.where(deltas.gt(0), 0)).rolling(window=periods).mean()
        loss = (-deltas.where(deltas.lt(0), 0)).rolling(window=periods).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
        
    async def _analyze_trend_with_ai(self, token_data: pd.DataFrame) -> Dict:
        """Use DeepSeek model to analyze price trends"""
        try:
            # Prepare data summary for AI analysis
            data_summary = f"""
            Price Analysis:
            - Current Price: {token_data['Close'].iloc[-1]:.6f}
            - 24h Change: {((token_data['Close'].iloc[-1] - token_data['Close'].iloc[-2]) / token_data['Close'].iloc[-2] * 100):.2f}%
            - 7d High: {token_data['High'].max():.6f}
            - 7d Low: {token_data['Low'].min():.6f}
            - Volume Trend: {'Increasing' if token_data['Volume'].iloc[-1] > token_data['Volume'].mean() else 'Decreasing'}
            - MA20 vs MA40: {'Bullish' if token_data['MA20'].iloc[-1] > token_data['MA40'].iloc[-1] else 'Bearish'}
            - RSI: {token_data['RSI'].iloc[-1]:.2f}
            """
            
            # Get AI analysis
            response = self.model.generate_response(
                system_prompt="You are a crypto market analyst. Analyze the given price data and provide a concise trend assessment.",
                user_content=data_summary,
                temperature=0.7,
                max_tokens=200
            )
            
            return {
                "ai_analysis": response.content,
                "confidence": "high" if "confidence" in response.content.lower() else "medium"
            }
        except Exception as e:
            cprint(f"❌ Failed to get AI analysis: {str(e)}", "red")
            return {
                "ai_analysis": "AI analysis unavailable",
                "confidence": "low"
            }
            
    def _assess_concentration_risk(self, top_holders_share: float) -> str:
        """Assess risk based on token concentration"""
        if top_holders_share > 0.7:  # 70% held by top holders
            return "HIGH"
        elif top_holders_share > 0.5:  # 50% held by top holders
            return "MEDIUM"
        return "LOW"
        
    def _assess_volume_adequacy(self, daily_volume: float) -> str:
        """Assess if trading volume is adequate"""
        if daily_volume < 1000:
            return "LOW"
        elif daily_volume < 10000:
            return "MEDIUM"
        return "HIGH"
        
    def _assess_holder_distribution(self, holders: List[Dict]) -> str:
        """Assess token holder distribution"""
        if len(holders) < 100:
            return "HIGH"  # High risk due to low holder count
        elif len(holders) < 1000:
            return "MEDIUM"
        return "LOW"  # Low risk with good distribution
