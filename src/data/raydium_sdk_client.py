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
        'en': 'Failed to get quote from Raydium',
        'zh': '从Raydium获取报价失败'
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

class RaydiumSDKClient:
    def __init__(self):
        self.api_url = "https://api.raydium.io/v2"
        self.pool_id = "58fzJMbX5PatnfJPqWWsqkVFPRKptkbb5r2vCw4Qq3z9"
        self.slippage_bps = int(os.getenv('DEFAULT_SLIPPAGE_BPS', '250'))
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
    async def get_pool_info(self) -> Optional[Dict]:
        """Get pool information from Raydium"""
        try:
            url = f"{self.api_url}/main/pool/{self.pool_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"\n✅ 获取池信息成功 | Pool info received successfully")
                        print(f"池子ID | Pool ID: {self.pool_id}")
                        print(f"流动性 | Liquidity: {data.get('liquidity', 'unknown')}")
                        print(f"价格 | Price: {data.get('price', 'unknown')}")
                        return data
                    else:
                        error_msg = ERROR_MESSAGES['quote_failed']
                        error_text = await response.text()
                        print(f"\n❌ 获取池信息失败 | Failed to get pool info: {error_text}")
                        return None
                        
        except Exception as e:
            print(f"\n❌ 错误 | Error: {str(e)}")
            return None
            
    async def get_quote(self, input_mint: str, output_mint: str, amount: str) -> Optional[Dict]:
        """Get quote from Raydium pool"""
        try:
            pool_info = await self.get_pool_info()
            if not pool_info:
                return None
                
            params = {
                'id': self.pool_id,
                'inputMint': input_mint,
                'outputMint': output_mint,
                'amount': amount,
                'slippage': self.slippage_bps/10000  # Convert to decimal
            }
            
            print(f"\n🔍 请求报价参数 | Quote request parameters:")
            print(f"输入代币 | Input token: {input_mint}")
            print(f"输出代币 | Output token: {output_mint}")
            print(f"数量 | Amount: {amount}")
            print(f"滑点 | Slippage: {self.slippage_bps/100}%")
            
            url = f"{self.api_url}/ammV3/quote"
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=params, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"\n✅ 获取报价成功 | Quote received successfully")
                        print(f"输出数量 | Output amount: {data.get('outAmount', 'unknown')}")
                        print(f"价格影响 | Price impact: {data.get('priceImpact', '0')}%")
                        return data
                    else:
                        error_msg = ERROR_MESSAGES['quote_failed']
                        error_text = await response.text()
                        print(f"\n❌ 获取报价失败 | Failed to get quote: {error_text}")
                        return None
                        
        except Exception as e:
            print(f"\n❌ 错误 | Error: {str(e)}")
            return None
            
    async def execute_swap(self, quote: Dict, wallet_key: str) -> Optional[str]:
        """Execute swap using Raydium SDK"""
        try:
            if not quote:
                print("\n❌ 无报价信息 | No quote provided")
                return None
                
            swap_data = {
                'id': self.pool_id,
                'quote': quote,
                'userPublicKey': wallet_key
            }
            
            url = f"{self.api_url}/ammV3/swap"
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=swap_data, headers=self.headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        txid = result.get('txid')
                        if txid:
                            print(f"\n✅ 交易成功 | Trade successful")
                            print(f"交易签名 | Transaction signature: {txid}")
                            return txid
                    
                    error_msg = ERROR_MESSAGES['swap_failed']
                    error_text = await response.text()
                    print(f"\n❌ 交易失败 | Trade failed: {error_text}")
                    return None
                    
        except Exception as e:
            print(f"\n❌ 错误 | Error: {str(e)}")
            return None

raydium_sdk_client = RaydiumSDKClient()  # Singleton instance
