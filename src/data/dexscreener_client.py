import os
import json
import asyncio
import aiohttp
from typing import Dict, Optional
from src.services.logging_service import logging_service

class DexScreenerClient:
    def __init__(self):
        self.api_url = "https://api.dexscreener.com/latest/dex"
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
    async def get_pair_info(self, pair_address: str) -> Optional[Dict]:
        """Get pair information from DexScreener"""
        try:
            url = f"{self.api_url}/pairs/solana/{pair_address}"
            
            print(f"\n🔍 获取交易对信息中... | Getting pair info...")
            print(f"交易对地址 | Pair address: {pair_address}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'pairs' in data and len(data['pairs']) > 0:
                            pair = data['pairs'][0]
                            print(f"\n✅ 获取交易对信息成功 | Pair info received successfully")
                            print(f"代币名称 | Token name: {pair.get('baseToken', {}).get('name')}")
                            print(f"代币价格 | Token price: ${pair.get('priceUsd')}")
                            print(f"24h交易量 | 24h volume: ${pair.get('volume', {}).get('h24')}")
                            print(f"流动性 | Liquidity: ${pair.get('liquidity', {}).get('usd')}")
                            return pair
                    
                    error_text = await response.text()
                    print(f"\n❌ 获取交易对信息失败 | Failed to get pair info: {error_text}")
                    return None
                    
        except Exception as e:
            print(f"\n❌ 错误 | Error: {str(e)}")
            return None
            
    async def analyze_token_pair(self, pair_address: str) -> Optional[Dict]:
        """Analyze token pair information"""
        try:
            # Get pair info
            pair_info = await self.get_pair_info(pair_address)
            if not pair_info:
                return None
                
            # Calculate additional metrics
            price_change_24h = float(pair_info.get('priceChange', {}).get('h24', 0))
            volume_24h = float(pair_info.get('volume', {}).get('h24', 0))
            liquidity_usd = float(pair_info.get('liquidity', {}).get('usd', 0))
            
            # Analyze trading activity
            analysis = {
                'token': {
                    'name': pair_info.get('baseToken', {}).get('name'),
                    'symbol': pair_info.get('baseToken', {}).get('symbol'),
                    'address': pair_info.get('baseToken', {}).get('address')
                },
                'price': {
                    'current': float(pair_info.get('priceUsd', 0)),
                    'change24h': price_change_24h
                },
                'volume': {
                    'usd24h': volume_24h
                },
                'liquidity': {
                    'usd': liquidity_usd
                },
                'analysis': {
                    'price_trend': 'up' if price_change_24h > 0 else 'down',
                    'liquidity_rating': 'high' if liquidity_usd > 100000 else 'medium' if liquidity_usd > 10000 else 'low',
                    'volume_to_liquidity_ratio': volume_24h / liquidity_usd if liquidity_usd > 0 else 0
                }
            }
            
            print(f"\n📊 分析结果 | Analysis results:")
            print(f"代币名称 | Token name: {analysis['token']['name']} ({analysis['token']['symbol']})")
            print(f"当前价格 | Current price: ${analysis['price']['current']}")
            print(f"24h价格变化 | 24h price change: {analysis['price']['change24h']}%")
            print(f"24h交易量 | 24h volume: ${analysis['volume']['usd24h']}")
            print(f"流动性 | Liquidity: ${analysis['liquidity']['usd']}")
            print(f"流动性评级 | Liquidity rating: {analysis['analysis']['liquidity_rating']}")
            print(f"成交量/流动性比率 | Volume/Liquidity ratio: {analysis['analysis']['volume_to_liquidity_ratio']:.2f}")
            
            return analysis
            
        except Exception as e:
            print(f"\n❌ 错误 | Error: {str(e)}")
            return None

dexscreener_client = DexScreenerClient()  # Singleton instance
