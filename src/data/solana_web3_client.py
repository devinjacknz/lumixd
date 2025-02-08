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
        'en': 'Failed to get quote',
        'zh': '获取报价失败'
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

class SolanaWeb3Client:
    def __init__(self):
        self.rpc_url = os.getenv('RPC_ENDPOINT', 'https://api.mainnet-beta.solana.com')
        self.pool_id = "58fzJMbX5PatnfJPqWWsqkVFPRKptkbb5r2vCw4Qq3z9"
        self.slippage_bps = int(os.getenv('DEFAULT_SLIPPAGE_BPS', '250'))
        self.headers = {
            "Content-Type": "application/json"
        }
        
    async def get_pool_info(self) -> Optional[Dict]:
        """Get pool information using Solana RPC"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [
                    self.pool_id,
                    {"encoding": "jsonParsed"}
                ]
            }
            
            print(f"\n🔍 获取池信息中... | Getting pool info...")
            print(f"池子ID | Pool ID: {self.pool_id}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.rpc_url, json=payload, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'result' in data and data['result']:
                            print(f"\n✅ 获取池信息成功 | Pool info received successfully")
                            return data['result']
                    
                    error_msg = ERROR_MESSAGES['quote_failed']
                    error_text = await response.text()
                    print(f"\n❌ 获取池信息失败 | Failed to get pool info: {error_text}")
                    return None
                    
        except Exception as e:
            print(f"\n❌ 错误 | Error: {str(e)}")
            return None
            
    async def get_token_accounts(self, wallet_key: str) -> Optional[Dict]:
        """Get token accounts for wallet"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenAccountsByOwner",
                "params": [
                    wallet_key,
                    {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                    {"encoding": "jsonParsed"}
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.rpc_url, json=payload, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'result' in data and data['result']:
                            return data['result']
                    return None
                    
        except Exception as e:
            print(f"\n❌ 错误 | Error: {str(e)}")
            return None
            
    async def execute_swap(self, wallet_key: str, amount: str) -> Optional[str]:
        """Execute swap using Solana Web3"""
        try:
            # First get pool info
            pool_info = await self.get_pool_info()
            if not pool_info:
                return None
                
            # Get token accounts
            token_accounts = await self.get_token_accounts(wallet_key)
            if not token_accounts:
                return None
                
            print(f"\n📊 交易详情 | Trade details:")
            print(f"钱包地址 | Wallet address: {wallet_key}")
            print(f"交易数量 | Amount: {amount} SOL")
            print(f"滑点 | Slippage: {self.slippage_bps/100}%")
            
            # Build and send transaction
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "sendTransaction",
                "params": [
                    # Transaction data would go here
                    # This is a placeholder as we need the actual Raydium program instructions
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.rpc_url, json=payload, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'result' in data:
                            txid = data['result']
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

solana_web3_client = SolanaWeb3Client()  # Singleton instance
