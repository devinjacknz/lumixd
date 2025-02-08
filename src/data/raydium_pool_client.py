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

class RaydiumPoolClient:
    def __init__(self):
        self.api_url = "https://api.raydium.io/v2/main"
        self.pool_id = "58fzJMbX5PatnfJPqWWsqkVFPRKptkbb5r2vCw4Qq3z9"
        self.slippage_bps = int(os.getenv('DEFAULT_SLIPPAGE_BPS', '250'))
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
    async def get_pool_info(self) -> Optional[Dict]:
        """Get pool information from Raydium"""
        try:
            url = f"{self.api_url}/pool/{self.pool_id}"
            
            print(f"\n🔍 获取池信息中... | Getting pool info...")
            print(f"池子ID | Pool ID: {self.pool_id}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"\n✅ 获取池信息成功 | Pool info received successfully")
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
                
            # Calculate expected output based on pool info
            input_amount = int(amount)
            pool_price = float(pool_info.get('price', 0))
            expected_output = int(input_amount * pool_price * (1 - self.slippage_bps/10000))
            
            quote = {
                'pool': self.pool_id,
                'inAmount': str(input_amount),
                'outAmount': str(expected_output),
                'priceImpact': pool_info.get('priceImpact', '0'),
                'price': pool_info.get('price', '0')
            }
            
            print(f"\n📊 交易详情 | Trade details:")
            print(f"输入数量 | Input amount: {input_amount} SOL")
            print(f"预计获得 | Expected output: {expected_output} VINE")
            print(f"价格 | Price: {pool_price}")
            
            return quote
            
        except Exception as e:
            print(f"\n❌ 错误 | Error: {str(e)}")
            return None
            
    async def execute_swap(self, quote: Dict, wallet_key: str) -> Optional[str]:
        """Execute swap using Raydium pool"""
        try:
            if not quote:
                print("\n❌ 无报价信息 | No quote provided")
                return None
                
            swap_data = {
                'pool': self.pool_id,
                'userPublicKey': wallet_key,
                'inAmount': quote['inAmount'],
                'minOutAmount': quote['outAmount'],
                'slippage': self.slippage_bps/10000
            }
            
            url = f"{self.api_url}/swap"
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

raydium_pool_client = RaydiumPoolClient()  # Singleton instance
