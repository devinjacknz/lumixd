import os
import json
import aiohttp
import asyncio
from typing import Dict, Any, Optional
from decimal import Decimal
import logging
from src.services.logging_service import logging_service

logger = logging.getLogger(__name__)

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
    """Client for interacting with Raydium V3 API with bilingual support"""
    
    API_URL = "https://api-v3.raydium.io"  # For price, pool info, etc.
    TRANSACTION_URL = "https://transaction-v1.raydium.io"  # For quotes and swaps
    
    def __init__(self, retry_attempts: int = 3, retry_delay: float = 1.0, timeout: int = 30):
        """Initialize Raydium client with retry settings
        
        Args:
            retry_attempts: Number of retry attempts for failed requests
            retry_delay: Initial delay between retries in seconds (uses exponential backoff)
            timeout: Request timeout in seconds
        """
        self.session = None
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.slippage_bps = int(os.getenv('DEFAULT_SLIPPAGE_BPS', '250'))
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
    async def __aenter__(self):
        """Set up async context with aiohttp session"""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources on context exit"""
        if self.session:
            await self.session.close()
            
    async def _make_request(self, method: str, endpoint: str, base_url: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with retry logic
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            base_url: Base URL to use (defaults to API_URL)
            **kwargs: Additional arguments for request
            
        Returns:
            API response data
            
        Raises:
            Exception: If request fails after all retries
        """
        attempt = 0
        last_error = None
        base_url = base_url or self.API_URL
        
        while attempt < self.retry_attempts:
            try:
                async with getattr(self.session, method.lower())(f"{base_url}{endpoint}", **kwargs) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    if not data.get("success"):
                        raise Exception(f"API error: {data.get('msg')}")
                        
                    return data["data"]
                    
            except Exception as e:
                last_error = e
                attempt += 1
                if attempt < self.retry_attempts:
                    delay = self.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                    logger.warning(f"Request failed, retrying in {delay}s... ({attempt}/{self.retry_attempts})")
                    await asyncio.sleep(delay)
                    
        raise Exception(f"Request failed after {self.retry_attempts} attempts: {str(last_error)}")
        
    async def get_quote(self, input_mint: str, output_mint: str, amount: str, swap_mode: str = 'ExactIn') -> Optional[Dict]:
        """Get quote from Raydium V3 API using compute/swap-base-in endpoint
        
        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Amount in smallest denomination (e.g., lamports for SOL)
            swap_mode: 'ExactIn' for exact input amount, 'ExactOut' for exact output amount
            
        Returns:
            Quote data or None if error occurs
        """
        try:
            endpoint = '/compute/swap-base-in' if swap_mode == 'ExactIn' else '/compute/swap-base-out'
            params = {
                'inputMint': input_mint,
                'outputMint': output_mint,
                'amount': amount,
                'slippageBps': self.slippage_bps,  # Using 250 bps (2.5%) for optimal execution
                'txVersion': 'V0'  # Use versioned transactions
            }
            
            print(f"\n🔍 请求报价参数 | Quote request parameters:")
            print(f"输入代币 | Input token: {input_mint}")
            print(f"输出代币 | Output token: {output_mint}")
            print(f"数量 | Amount: {amount}")
            print(f"滑点 | Slippage: {self.slippage_bps/100}%")
            
            try:
                data = await self._make_request('get', endpoint, params=params, base_url=self.TRANSACTION_URL, headers=self.headers)
                print(f"\n✅ 获取报价成功 | Quote received successfully")
                print(f"输入代币 | Input token: {input_mint}")
                print(f"输出代币 | Output token: {output_mint}")
                print(f"输入数量 | Input amount: {amount}")
                print(f"输出数量 | Output amount: {data.get('outAmount', 'unknown')}")
                print(f"价格影响 | Price impact: {data.get('priceImpact', '0')}%")
                print(f"交易版本 | Transaction version: {params['txVersion']}")
                print(f"交易模式 | Swap mode: {swap_mode}")
                print(f"滑点设置 | Slippage: {self.slippage_bps/100}%")
                
                await logging_service.log_user_action(
                    'quote_received',
                    {
                        'quote': data,
                        'params': {
                            'input_mint': input_mint,
                            'output_mint': output_mint,
                            'amount': amount,
                            'swap_mode': swap_mode,
                            'slippage_bps': self.slippage_bps
                        }
                    },
                    'system'
                )
                return data
            except Exception as e:
                error_msg = ERROR_MESSAGES['quote_failed']
                print(f"\n❌ 获取报价失败 | Failed to get quote: {str(e)}")
                
                await logging_service.log_error(
                    f"{error_msg['zh']} | {error_msg['en']}",
                    {
                        'error': str(e),
                        'params': {
                            'input_mint': input_mint,
                            'output_mint': output_mint,
                            'amount': amount,
                            'swap_mode': swap_mode,
                            'slippage_bps': self.slippage_bps,
                            'endpoint': endpoint
                        }
                    },
                    'system'
                )
                return None
                
        except ValueError as e:
            error_msg = ERROR_MESSAGES['quote_failed']
            print(f"\n❌ Invalid swap mode: {swap_mode}. Must be 'ExactIn' or 'ExactOut'")
            await logging_service.log_error(
                f"{error_msg['zh']} | {error_msg['en']}",
                {'error': f"Invalid swap mode: {swap_mode}"},
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
            
    async def get_pool_info(self, pool_ids: list[str]) -> Dict[str, Any]:
        """Get pool information for specified pool IDs
        
        Args:
            pool_ids: List of pool IDs to fetch information for
            
        Returns:
            Dictionary containing pool information
            
        Raises:
            Exception: If API request fails
        """
        try:
            params = {"ids": ",".join(pool_ids)}
            return await self._make_request('get', '/pools/info/ids', params=params, headers=self.headers)
        except Exception as e:
            error_msg = ERROR_MESSAGES['network_error']
            await logging_service.log_error(
                f"{error_msg['zh']} | {error_msg['en']}",
                {
                    'error': str(e),
                    'pool_ids': pool_ids
                },
                'system'
            )
            raise
            
    async def get_token_price(self, mint_address: str) -> Decimal:
        """Get token price from Raydium
        
        Args:
            mint_address: Token mint address
            
        Returns:
            Token price as Decimal
            
        Raises:
            Exception: If API request fails
        """
        try:
            params = {"mint": mint_address}
            data = await self._make_request('get', '/mint/price', params=params, headers=self.headers)
            return Decimal(str(data["price"]))
        except Exception as e:
            error_msg = ERROR_MESSAGES['quote_failed']
            await logging_service.log_error(
                f"{error_msg['zh']} | {error_msg['en']}",
                {
                    'error': str(e),
                    'mint_address': mint_address
                },
                'system'
            )
            raise
            
    async def get_priority_fee(self) -> Dict[str, Any]:
        """Get priority fee tiers from Raydium API
        
        Returns:
            Dictionary containing priority fee tiers (vh: very high, h: high, m: medium)
            
        Raises:
            Exception: If API request fails
        """
        try:
            data = await self._make_request('get', '/priority-fee', base_url=self.TRANSACTION_URL, headers=self.headers)
            return data.get('default', {'vh': 1500, 'h': 1000, 'm': 500})  # Default values if not available
        except Exception as e:
            logger.warning(f"Failed to get priority fee: {str(e)}")
            return {'vh': 1500, 'h': 1000, 'm': 500}  # Fallback priority fees
            
    async def execute_swap(self, quote: Dict, wallet_key: str) -> Optional[str]:
        """Execute swap with proper error handling using Raydium V3 API"""
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
                'swapResponse': quote,
                'txVersion': 'V0',  # Use versioned transactions
                'wallet': wallet_key,
                'wrapSol': True,  # Handle SOL wrapping
                'unwrapSol': True  # Handle SOL unwrapping
            }
            
            await logging_service.log_user_action(
                'execute_swap',
                {'swap_data': {**swap_data, 'userPublicKey': '[REDACTED]'}},
                'system'
            )
            
            try:
                # Get priority fee for better execution
                priority_fee = await self.get_priority_fee()
                swap_data['computeUnitPriceMicroLamports'] = str(priority_fee['h'])  # Use high priority
                
                data = await self._make_request('post', '/transaction/swap-base-in', json=swap_data, base_url=self.TRANSACTION_URL, headers=self.headers)
                txid = data.get('txid')
                
                if txid:
                    await logging_service.log_user_action(
                        'swap_success',
                        {
                            'txid': txid,
                            'status': 'success',
                            'priority_fee': priority_fee['h']
                        },
                        'system'
                    )
                    return txid
                    
                error_msg = ERROR_MESSAGES['swap_failed']
                await logging_service.log_error(
                    f"{error_msg['zh']} | {error_msg['en']}",
                    {
                        'error': 'No transaction ID in response',
                        'swap_data': {**swap_data, 'userPublicKey': '[REDACTED]'}
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
