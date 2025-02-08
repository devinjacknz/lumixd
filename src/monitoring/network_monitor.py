import time
import asyncio
from typing import Dict, Optional
from src.data.chainstack_client import ChainStackClient
from src.data.jupiter_client_v2 import jupiter_client_v2
from src.services.logging_service import logging_service

# Bilingual error messages
ERROR_MESSAGES = {
    'rpc_error': {
        'en': 'RPC endpoint health check failed',
        'zh': 'RPC端点健康检查失败'
    },
    'jupiter_error': {
        'en': 'Jupiter API health check failed',
        'zh': 'Jupiter API健康检查失败'
    },
    'network_error': {
        'en': 'Network connection error',
        'zh': '网络连接错误'
    }
}

class NetworkMonitor:
    def __init__(self):
        self.last_check = time.time()
        self.check_interval = 60  # seconds
        self.chainstack_client = ChainStackClient()
        self.jupiter_client = jupiter_client_v2
        
    async def check_network_health(self) -> Dict[str, bool]:
        """Check health of all network services"""
        try:
            current_time = time.time()
            if current_time - self.last_check < self.check_interval:
                return {
                    'rpc': True,
                    'jupiter': True
                }
                
            self.last_check = current_time
            
            # Check RPC endpoint
            try:
                rpc_response = await self.chainstack_client._post_rpc("getHealth", [])
                rpc_healthy = bool(rpc_response.get("result"))
                if not rpc_healthy:
                    error_msg = ERROR_MESSAGES['rpc_error']
                    await logging_service.log_error(
                        f"{error_msg['zh']} | {error_msg['en']}",
                        {'response': rpc_response},
                        'system'
                    )
            except Exception as e:
                error_msg = ERROR_MESSAGES['rpc_error']
                await logging_service.log_error(
                    f"{error_msg['zh']} | {error_msg['en']}",
                    {'error': str(e)},
                    'system'
                )
                rpc_healthy = False
                
            # Check Jupiter API
            try:
                quote = await self.jupiter_client.get_quote(
                    "So11111111111111111111111111111111111111112",  # SOL
                    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
                    "1000000000"  # 1 SOL
                )
                jupiter_healthy = bool(quote)
                if not jupiter_healthy:
                    error_msg = ERROR_MESSAGES['jupiter_error']
                    await logging_service.log_error(
                        f"{error_msg['zh']} | {error_msg['en']}",
                        {'error': 'Failed to get test quote'},
                        'system'
                    )
            except Exception as e:
                error_msg = ERROR_MESSAGES['jupiter_error']
                await logging_service.log_error(
                    f"{error_msg['zh']} | {error_msg['en']}",
                    {'error': str(e)},
                    'system'
                )
                jupiter_healthy = False
                
            # Log overall health status
            await logging_service.log_user_action(
                'network_health_check',
                {
                    'rpc_healthy': rpc_healthy,
                    'jupiter_healthy': jupiter_healthy,
                    'timestamp': current_time
                },
                'system'
            )
            
            return {
                'rpc': rpc_healthy,
                'jupiter': jupiter_healthy
            }
            
        except Exception as e:
            error_msg = ERROR_MESSAGES['network_error']
            await logging_service.log_error(
                f"{error_msg['zh']} | {error_msg['en']}",
                {'error': str(e)},
                'system'
            )
            return {
                'rpc': False,
                'jupiter': False
            }
            
    async def start_monitoring(self):
        """Start continuous network monitoring"""
        while True:
            await self.check_network_health()
            await asyncio.sleep(self.check_interval)

network_monitor = NetworkMonitor()  # Singleton instance
