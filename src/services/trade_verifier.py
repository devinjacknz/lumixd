import aiohttp
from typing import Dict, Optional
from src.services.logging_service import logging_service

# Bilingual error messages
ERROR_MESSAGES = {
    'verification_failed': {
        'en': 'Transaction verification failed',
        'zh': '交易验证失败'
    },
    'network_error': {
        'en': 'Network connection error',
        'zh': '网络连接错误'
    },
    'invalid_signature': {
        'en': 'Invalid transaction signature',
        'zh': '无效的交易签名'
    }
}

class TradeVerifier:
    def __init__(self):
        self.solscan_url = "https://api.solscan.io/transaction"
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "Solana/DeFi-Agent"
        }
        
    async def verify_transaction(self, signature: str) -> Dict[str, bool | str | None]:
        """Verify transaction status using Solscan API"""
        try:
            if not signature or len(signature) < 32:
                error_msg = ERROR_MESSAGES['invalid_signature']
                await logging_service.log_error(
                    f"{error_msg['zh']} | {error_msg['en']}",
                    {'signature': signature},
                    'system'
                )
                return {
                    'verified': False,
                    'error': f"{error_msg['zh']} | {error_msg['en']}"
                }
                
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.solscan_url}?tx={signature}",
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        is_success = data.get("status") == "Success"
                        
                        # Log verification result
                        await logging_service.log_user_action(
                            'transaction_verification',
                            {
                                'signature': signature,
                                'verified': is_success,
                                'status': data.get("status")
                            },
                            'system'
                        )
                        
                        return {
                            'verified': is_success,
                            'error': None if is_success else 'Transaction failed on-chain'
                        }
                    else:
                        error_msg = ERROR_MESSAGES['verification_failed']
                        await logging_service.log_error(
                            f"{error_msg['zh']} | {error_msg['en']}",
                            {
                                'status_code': response.status,
                                'signature': signature
                            },
                            'system'
                        )
                        return {
                            'verified': False,
                            'error': f"{error_msg['zh']} | {error_msg['en']}"
                        }
                        
        except aiohttp.ClientError as e:
            error_msg = ERROR_MESSAGES['network_error']
            await logging_service.log_error(
                f"{error_msg['zh']} | {error_msg['en']}",
                {
                    'error': str(e),
                    'signature': signature
                },
                'system'
            )
            return {
                'verified': False,
                'error': f"{error_msg['zh']} | {error_msg['en']}"
            }
            
        except Exception as e:
            error_msg = ERROR_MESSAGES['verification_failed']
            await logging_service.log_error(
                f"{error_msg['zh']} | {error_msg['en']}",
                {
                    'error': str(e),
                    'signature': signature
                },
                'system'
            )
            return {
                'verified': False,
                'error': f"{error_msg['zh']} | {error_msg['en']}"
            }
            
    async def get_transaction_details(self, signature: str) -> Optional[Dict]:
        """Get detailed transaction information from Solscan"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.solscan_url}?tx={signature}",
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        return await response.json()
            return None
        except Exception as e:
            await logging_service.log_error(
                str(e),
                {
                    'error': str(e),
                    'signature': signature
                },
                'system'
            )
            return None

trade_verifier = TradeVerifier()  # Singleton instance
