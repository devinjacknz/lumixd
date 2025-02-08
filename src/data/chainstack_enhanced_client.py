import os
import json
import base64
import asyncio
import aiohttp
from typing import Dict, Optional
from src.services.logging_service import logging_service

# Bilingual error messages
ERROR_MESSAGES = {
    'token_info_failed': {
        'en': 'Failed to get token info from Chainstack',
        'zh': '从Chainstack获取代币信息失败'
    },
    'pool_info_failed': {
        'en': 'Failed to get pool info',
        'zh': '获取池信息失败'
    },
    'network_error': {
        'en': 'Network connection error',
        'zh': '网络连接错误'
    }
}

class ChainstackEnhancedClient:
    def __init__(self):
        self.rpc_url = os.getenv('RPC_ENDPOINT', 'https://solana-mainnet.core.chainstack.com/')
        self.headers = {
            "Content-Type": "application/json"
        }
        
    async def get_token_info(self, token_address: str) -> Optional[Dict]:
        """Get token information using Chainstack Enhanced RPC"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "chainstack_getTokenInfo",
                "params": [token_address]
            }
            
            print(f"\n🔍 获取代币信息中... | Getting token info...")
            print(f"代币地址 | Token address: {token_address}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.rpc_url, json=payload, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'result' in data:
                            print(f"\n✅ 获取代币信息成功 | Token info received successfully")
                            print(f"代币名称 | Token name: {data['result'].get('name', 'unknown')}")
                            print(f"代币符号 | Token symbol: {data['result'].get('symbol', 'unknown')}")
                            print(f"精度 | Decimals: {data['result'].get('decimals', 'unknown')}")
                            return data['result']
                    
                    error_msg = ERROR_MESSAGES['token_info_failed']
                    error_text = await response.text()
                    print(f"\n❌ 获取代币信息失败 | Failed to get token info: {error_text}")
                    return None
                    
        except Exception as e:
            print(f"\n❌ 错误 | Error: {str(e)}")
            return None
            
    async def get_pool_info(self, pool_address: str) -> Optional[Dict]:
        """Get pool information using Chainstack Enhanced RPC"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "chainstack_getDexPoolInfo",
                "params": [pool_address]
            }
            
            print(f"\n🔍 获取池信息中... | Getting pool info...")
            print(f"池子地址 | Pool address: {pool_address}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.rpc_url, json=payload, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'result' in data:
                            print(f"\n✅ 获取池信息成功 | Pool info received successfully")
                            print(f"流动性 | Liquidity: {data['result'].get('liquidity', 'unknown')}")
                            print(f"交易量24h | Volume 24h: {data['result'].get('volume24h', 'unknown')}")
                            print(f"价格 | Price: {data['result'].get('price', 'unknown')}")
                            return data['result']
                    
                    error_msg = ERROR_MESSAGES['pool_info_failed']
                    error_text = await response.text()
                    print(f"\n❌ 获取池信息失败 | Failed to get pool info: {error_text}")
                    return None
                    
        except Exception as e:
            print(f"\n❌ 错误 | Error: {str(e)}")
            return None
            
    async def get_market_depth(self, pool_address: str) -> Optional[Dict]:
        """Get market depth information"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "chainstack_getMarketDepth",
                "params": [pool_address]
            }
            
            print(f"\n🔍 获取市场深度... | Getting market depth...")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.rpc_url, json=payload, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'result' in data:
                            return data['result']
                    return None
                    
        except Exception as e:
            print(f"\n❌ 错误 | Error: {str(e)}")
            return None
            
    async def get_price_history(self, token_address: str, interval: str = "1h", limit: int = 24) -> Optional[Dict]:
        """Get token price history"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "chainstack_getTokenPriceHistory",
                "params": [token_address, interval, limit]
            }
            
            print(f"\n🔍 获取价格历史... | Getting price history...")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.rpc_url, json=payload, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'result' in data:
                            return data['result']
                    return None
                    
        except Exception as e:
            print(f"\n❌ 错误 | Error: {str(e)}")
            return None
            
    async def analyze_token_and_pool(self, token_address: str, pool_address: str) -> Optional[Dict]:
        """Analyze token and pool information"""
        try:
            # Get token info
            token_info = await self.get_token_info(token_address)
            if not token_info:
                return None
                
            # Get pool info
            pool_info = await self.get_pool_info(pool_address)
            if not pool_info:
                return None
                
            # Get market depth
            market_depth = await self.get_market_depth(pool_address)
            
            # Get price history
            price_history = await self.get_price_history(token_address)
            
            # Calculate price volatility
            if price_history and len(price_history.get('prices', [])) > 0:
                prices = price_history['prices']
                max_price = max(p['price'] for p in prices)
                min_price = min(p['price'] for p in prices)
                volatility = ((max_price - min_price) / min_price) * 100 if min_price > 0 else 0
            else:
                volatility = 0
                
            # Analyze liquidity depth
            buy_depth = sum(level['amount'] for level in market_depth.get('bids', [])) if market_depth else 0
            sell_depth = sum(level['amount'] for level in market_depth.get('asks', [])) if market_depth else 0
            
            # Combine and analyze data
            analysis = {
                'token': token_info,
                'pool': pool_info,
                'market_depth': {
                    'buy_depth': buy_depth,
                    'sell_depth': sell_depth
                },
                'analysis': {
                    'price': pool_info.get('price', 0),
                    'liquidity': pool_info.get('liquidity', 0),
                    'volume24h': pool_info.get('volume24h', 0),
                    'priceChange24h': pool_info.get('priceChange24h', 0),
                    'volatility24h': volatility,
                    'buy_pressure': buy_depth / (buy_depth + sell_depth) if (buy_depth + sell_depth) > 0 else 0
                }
            }
            
            print(f"\n📊 分析结果 | Analysis results:")
            print(f"当前价格 | Current price: ${analysis['analysis']['price']}")
            print(f"24h交易量 | 24h volume: ${analysis['analysis']['volume24h']}")
            print(f"流动性 | Liquidity: ${analysis['analysis']['liquidity']}")
            print(f"24h价格变化 | 24h price change: {analysis['analysis']['priceChange24h']}%")
            print(f"24h波动率 | 24h volatility: {analysis['analysis']['volatility24h']}%")
            print(f"买入压力 | Buy pressure: {analysis['analysis']['buy_pressure']*100:.2f}%")
            
            return analysis
            
        except Exception as e:
            print(f"\n❌ 错误 | Error: {str(e)}")
            return None

chainstack_enhanced_client = ChainstackEnhancedClient()  # Singleton instance
