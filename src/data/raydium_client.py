import os
import json
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

class RaydiumClient:
    def __init__(self):
        self.api_url = "https://api.raydium.io/v2"
        self.slippage_bps = int(os.getenv('DEFAULT_SLIPPAGE_BPS', '250'))
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
    async def get_quote(self, input_mint: str, output_mint: str, amount: str) -> Optional[Dict]:
        """Get quote from Raydium API"""
        try:
            params = {
                'inputMint': input_mint,
                'outputMint': output_mint,
                'amount': amount,
                'slippage': self.slippage_bps/10000,  # Convert to decimal
                'version': 2
            }
            
            print(f"\n🔍 请求报价参数 | Quote request parameters:")
            print(f"输入代币 | Input token: {input_mint}")
            print(f"输出代币 | Output token: {output_mint}")
            print(f"数量 | Amount: {amount}")
            print(f"滑点 | Slippage: {self.slippage_bps/100}%")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/quote", params=params, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"\n✅ 获取报价成功 | Quote received successfully")
                        print(f"输出数量 | Output amount: {data.get('outAmount', 'unknown')}")
                        print(f"价格影响 | Price impact: {data.get('priceImpact', '0')}%")
                        
                        await logging_service.log_user_action(
                            'quote_received',
                            {'quote': data},
                            'system'
                        )
                        return data
                    else:
                        error_msg = ERROR_MESSAGES['quote_failed']
                        error_text = await response.text()
                        print(f"\n❌ 获取报价失败 | Failed to get quote: {error_text}")
                        
                        await logging_service.log_error(
                            f"{error_msg['zh']} | {error_msg['en']}",
                            {
                                'status_code': response.status,
                                'error_text': error_text,
                                'params': params
                            },
                            'system'
                        )
                        return None
                        
        except aiohttp.ClientError as e:
            error_msg = ERROR_MESSAGES['network_error']
            await logging_service.log_error(
                f"{error_msg['zh']} | {error_msg['en']}",
                {
                    'error': str(e),
                    'params': locals()
                },
                'system'
            )
            return None
            
        except Exception as e:
            error_msg = ERROR_MESSAGES['quote_failed']
            await logging_service.log_error(
                f"{error_msg['zh']} | {error_msg['en']}",
                {
                    'error': str(e),
                    'params': locals()
                },
                'system'
            )
            return None
            
    async def execute_swap(self, quote: Dict, wallet_key: str) -> Optional[str]:
        """Execute swap with proper error handling"""
        try:
            if not quote:
                error_msg = ERROR_MESSAGES['swap_failed']
                await logging_service.log_error(
                    f"{error_msg['zh']} | {error_msg['en']}",
                    {'error': 'No quote provided'},
                    'system'
                )
                return None
                
            swap_data = {
                'quote': quote,
                'userPublicKey': wallet_key,
                'version': 2
            }
            
            await logging_service.log_user_action(
                'execute_swap',
                {'swap_data': {**swap_data, 'userPublicKey': '[REDACTED]'}},
                'system'
            )
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_url}/swap", json=swap_data, headers=self.headers) as response:
                    if response.status == 200:
                        swap_result = await response.json()
                        txid = swap_result.get('txid')
                        
                        if txid:
                            await logging_service.log_user_action(
                                'swap_success',
                                {
                                    'txid': txid,
                                    'status': 'success'
                                },
                                'system'
                            )
                            return txid
                            
                    error_msg = ERROR_MESSAGES['swap_failed']
                    error_text = await response.text()
                    await logging_service.log_error(
                        f"{error_msg['zh']} | {error_msg['en']}",
                        {
                            'status_code': response.status,
                            'error_text': error_text,
                            'swap_data': {**swap_data, 'userPublicKey': '[REDACTED]'}
                        },
                        'system'
                    )
                    return None
                    
        except aiohttp.ClientError as e:
            error_msg = ERROR_MESSAGES['network_error']
            await logging_service.log_error(
                f"{error_msg['zh']} | {error_msg['en']}",
                {
                    'error': str(e),
                    'swap_data': {**locals(), 'wallet_key': '[REDACTED]'}
                },
                'system'
            )
            return None
            
        except Exception as e:
            error_msg = ERROR_MESSAGES['swap_failed']
            await logging_service.log_error(
                f"{error_msg['zh']} | {error_msg['en']}",
                {
                    'error': str(e),
                    'swap_data': {**locals(), 'wallet_key': '[REDACTED]'}
                },
                'system'
            )
            return None

raydium_client = RaydiumClient()  # Singleton instance
