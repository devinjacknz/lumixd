import os
import json
import asyncio
import aiohttp
from typing import Optional, Dict
from src.data.raydium_clmm_client import raydium_clmm_client
from src.services.logging_service import logging_service

# Constants
SLIPPAGE_BPS = 250  # 2.5%
SOL_DECIMALS = 9
LAMPORTS_PER_SOL = 1_000_000_000  # 10^9
POSITION_SIZE = 5 * LAMPORTS_PER_SOL  # 5 SOL

# Token addresses
SOL_MINT = "So11111111111111111111111111111111111111112"
VINE_MINT = "6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump"
POOL_ADDRESS = "58fzJMbX5PatnfJPqWWsqkVFPRKptkbb5r2vCw4Qq3z9"

async def execute_buy() -> None:
    """Execute buy trade for VINE token using Raydium CLMM"""
    try:
        # Get pool info first
        pool_info = await raydium_clmm_client.get_pool_info()
        if not pool_info:
            print("\n❌ 获取池信息失败 | Failed to get pool info")
            return
            
        # Get quote
        quote = await raydium_clmm_client.get_quote(
            input_mint=SOL_MINT,
            output_mint=VINE_MINT,
            amount=str(POSITION_SIZE)
        )
        
        if not quote:
            print("\n❌ 获取报价失败 | Failed to get quote")
            return
            
        # Get wallet key from environment
        wallet_key = os.getenv('WALLET_KEY')
        if not wallet_key:
            print("\n❌ 钱包密钥未设置 | Wallet key not set")
            return
            
        # Execute swap
        signature = await raydium_clmm_client.execute_swap(quote, wallet_key)
        
        if signature:
            print(f"\n✅ 交易成功 | Trade successful")
            print(f"交易签名 | Transaction signature: {signature}")
            print(f"查看交易 | View transaction: https://solscan.io/tx/{signature}")
            
            await logging_service.log_user_action(
                'buy_executed',
                {
                    'token': 'VINE',
                    'amount': '5 SOL worth',
                    'signature': signature,
                    'status': 'success',
                    'quote': quote
                },
                'system'
            )
        else:
            print("\n❌ 交易失败 | Trade failed")
            await logging_service.log_error(
                "Trade execution failed",
                {
                    'input_mint': SOL_MINT,
                    'output_mint': VINE_MINT,
                    'amount': str(POSITION_SIZE),
                    'status': 'failed'
                },
                'system'
            )
            
    except Exception as e:
        print(f"\n❌ 错误 | Error: {str(e)}")
        await logging_service.log_error(str(e), locals(), 'system')

async def main() -> None:
    """Main entry point"""
    try:
        await execute_buy()
    except KeyboardInterrupt:
        print("\n👋 退出程序 | Exiting program")
    except Exception as e:
        print(f"\n❌ 错误 | Error: {str(e)}")
        await logging_service.log_error(str(e), locals(), 'system')

if __name__ == "__main__":
    asyncio.run(main())
