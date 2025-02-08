import os
import json
import base64
import asyncio
import aiohttp
from typing import Dict, Optional
from src.services.logging_service import logging_service

# Bilingual error messages
ERROR_MESSAGES = {
    'quote_failed': {
        'en': 'Failed to get quote from Birdeye',
        'zh': '从Birdeye获取报价失败'
    },
    'swap_failed': {
        'en': 'Failed to execute swap',
        'zh': '执行交易失败'
    },
    'network_error': {
        'en': 'Network connection error',
        'zh': '网络连接错误'
    }
}

class BirdeyeClient:
    def __init__(self):
        self.api_url = "https://public-api.birdeye.so/v1"
        self.token_address = "6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump"
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-API-KEY": "YOUR_API_KEY"  # We'll get this from env var
        }
        
    async def get_token_info(self) -> Optional[Dict]:
        """Get token information from Birdeye"""
        try:
            url = f"{self.api_url}/token/info"
            params = {
                'address': self.token_address
            }
            
            print(f"\n🔍 获取代币信息中... | Getting token info...")
            print(f"代币地址 | Token address: {self.token_address}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"\n✅ 获取代币信息成功 | Token info received successfully")
                        print(f"代币名称 | Token name: {data.get('data', {}).get('name', 'unknown')}")
                        print(f"代币价格 | Token price: {data.get('data', {}).get('price', 'unknown')}")
                        return data.get('data')
                    else:
                        error_msg = ERROR_MESSAGES['quote_failed']
                        error_text = await response.text()
                        print(f"\n❌ 获取代币信息失败 | Failed to get token info: {error_text}")
                        return None
                        
        except Exception as e:
            print(f"\n❌ 错误 | Error: {str(e)}")
            return None
            
    async def get_pools(self) -> Optional[Dict]:
        """Get pool information from Birdeye"""
        try:
            url = f"{self.api_url}/dex/pools"
            params = {
                'token': self.token_address
            }
            
            print(f"\n🔍 获取池信息中... | Getting pool info...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"\n✅ 获取池信息成功 | Pool info received successfully")
                        return data.get('data')
                    else:
                        error_msg = ERROR_MESSAGES['quote_failed']
                        error_text = await response.text()
                        print(f"\n❌ 获取池信息失败 | Failed to get pool info: {error_text}")
                        return None
                        
        except Exception as e:
            print(f"\n❌ 错误 | Error: {str(e)}")
            return None
            
    async def get_price(self) -> Optional[float]:
        """Get current price from Birdeye"""
        try:
            url = f"{self.api_url}/token/price"
            params = {
                'address': self.token_address
            }
            
            print(f"\n🔍 获取价格中... | Getting price...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = data.get('data', {}).get('value')
                        print(f"\n✅ 获取价格成功 | Price received successfully")
                        print(f"当前价格 | Current price: ${price}")
                        return price
                    else:
                        error_msg = ERROR_MESSAGES['quote_failed']
                        error_text = await response.text()
                        print(f"\n❌ 获取价格失败 | Failed to get price: {error_text}")
                        return None
                        
        except Exception as e:
            print(f"\n❌ 错误 | Error: {str(e)}")
            return None

birdeye_client = BirdeyeClient()  # Singleton instance
