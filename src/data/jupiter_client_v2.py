import aiohttp
import json
import os
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

class JupiterClientV2:
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
            params = {
                'inputMint': input_mint,
                'outputMint': output_mint,
                'amount': amount,
                'slippageBps': self.slippage_bps,
                'feeBps': 0,
                'onlyDirectRoutes': False,
                'asLegacyTransaction': False,
                'useSharedAccounts': True,
                'maxAccounts': 54
            }
            
            await logging_service.log_user_action(
                'get_quote',
                {'params': params},
                'system'
            )
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/quote", params=params, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        await logging_service.log_user_action(
                            'quote_received',
                            {'quote': data},
                            'system'
                        )
                        return data
                    else:
                        error_msg = ERROR_MESSAGES['quote_failed']
                        await logging_service.log_error(
                            f"{error_msg['zh']} | {error_msg['en']}",
                            {
                                'status_code': response.status,
                                'error_text': await response.text(),
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
                'maxAccounts': 54
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
                        await logging_service.log_user_action(
                            'swap_success',
                            {
                                'txid': swap_result.get('txid'),
                                'status': 'success'
                            },
                            'system'
                        )
                        return swap_result.get('txid')
                    else:
                        error_msg = ERROR_MESSAGES['swap_failed']
                        await logging_service.log_error(
                            f"{error_msg['zh']} | {error_msg['en']}",
                            {
                                'status_code': response.status,
                                'error_text': await response.text(),
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

jupiter_client_v2 = JupiterClientV2()  # Singleton instance
