import os
import json
import aiohttp
from typing import Dict, Optional
from src.services.logging_service import logging_service

# Bilingual error messages
ERROR_MESSAGES = {
    'quote_failed': {
        'en': 'Failed to get quote from Jupiter',
        'zh': '从Jupiter获取报价失败'
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

class JupiterClient:
    def __init__(self):
        self.api_url = os.getenv('JUPITER_API_URL', 'https://quote-api.jup.ag/v6')
        self.slippage_bps = int(os.getenv('DEFAULT_SLIPPAGE_BPS', '250'))
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
    async def get_quote(self, input_mint: str, output_mint: str, amount: str) -> Optional[Dict]:
        """Get quote from Jupiter API with proper parameters"""
        try:
            # Prepare request URL with query parameters
            url = f"{self.api_url}/quote"
            params = {
                'inputMint': input_mint,
                'outputMint': output_mint,
                'amount': amount,
                'slippageBps': self.slippage_bps
            }
            
            print(f"\n🔍 请求报价参数 | Quote request parameters:")
            print(f"输入代币 | Input token: {input_mint}")
            print(f"输出代币 | Output token: {output_mint}")
            print(f"数量 | Amount: {amount}")
            print(f"滑点 | Slippage: {self.slippage_bps/100}%")
            print(f"API URL: {url}")
            
            await logging_service.log_user_action(
                'get_quote',
                {'params': params},
                'system'
            )
            
            async with aiohttp.ClientSession() as session:
                # First try to get all tokens to verify input/output mints
                async with session.get("https://token.jup.ag/all") as tokens_response:
                    if tokens_response.status == 200:
                        tokens = await tokens_response.json()
                        input_valid = any(t['address'] == input_mint for t in tokens)
                        output_valid = any(t['address'] == output_mint for t in tokens)
                        
                        if not input_valid or not output_valid:
                            print("\n❌ 无效代币地址 | Invalid token addresses")
                            print(f"Input token valid: {input_valid}")
                            print(f"Output token valid: {output_valid}")
                            return None
                            
                # Get quote with validated tokens
                async with session.get(f"{self.api_url}/quote", params=params, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"\n✅ 获取报价成功 | Quote received successfully")
                        print(f"输出数量 | Output amount: {data.get('outAmount', 'unknown')}")
                        print(f"价格影响 | Price impact: {data.get('priceImpactPct', '0')}%")
                        
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
                'quoteResponse': quote,
                'userPublicKey': wallet_key,
                'wrapUnwrapSOL': True,
                'computeUnitPriceMicroLamports': 'auto',
                'asLegacyTransaction': False,
                'useSharedAccounts': True,
                'maxAccounts': 64
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

jupiter_client = JupiterClient()  # Singleton instance
