import os
import json
import base64
import asyncio
import aiohttp
from typing import Optional, Dict
from src.services.logging_service import logging_service

# Constants
SLIPPAGE_BPS = 250  # 2.5%
SOL_DECIMALS = 9
LAMPORTS_PER_SOL = 1_000_000_000  # 10^9
POSITION_SIZE = 5 * LAMPORTS_PER_SOL  # 5 SOL

# Token addresses
SOL_MINT = "So11111111111111111111111111111111111111112"
VINE_MINT = "6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump"

async def get_whirlpool_info() -> Optional[Dict]:
    """Get whirlpool information from Orca"""
    try:
        url = "https://api.orca.so/v1/whirlpool/list"
        params = {
            "tokenMintA": SOL_MINT,
            "tokenMintB": VINE_MINT
        }
        
        print("\n🔍 获取交易池信息中... | Getting whirlpool info...")
        print(f"代币A | Token A: SOL ({SOL_MINT})")
        print(f"代币B | Token B: VINE ({VINE_MINT})")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('whirlpools'):
                        pool = data['whirlpools'][0]
                        print(f"\n✅ 获取交易池信息成功 | Whirlpool info received")
                        print(f"池地址 | Pool address: {pool.get('address')}")
                        print(f"流动性 | Liquidity: {pool.get('liquidity')}")
                        return pool
                    
                error_text = await response.text()
                print(f"\n❌ 获取交易池信息失败 | Failed to get whirlpool info: {error_text}")
                return None
                
    except Exception as e:
        print(f"\n❌ 错误 | Error: {str(e)}")
        return None

async def get_quote(pool_info: Dict) -> Optional[Dict]:
    """Get quote from Orca"""
    try:
        if not pool_info:
            print("\n❌ 无交易池信息 | No pool info")
            return None
            
        url = "https://api.orca.so/v1/quote"
        quote_data = {
            "inAmount": str(POSITION_SIZE),
            "inputMint": SOL_MINT,
            "outputMint": VINE_MINT,
            "slippage": SLIPPAGE_BPS,
            "whirlpoolAddress": pool_info['address']
        }
        
        print("\n🔍 获取报价中... | Getting quote...")
        print(f"数量 | Amount: 5 SOL")
        print(f"滑点 | Slippage: {SLIPPAGE_BPS/100}%")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=quote_data) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"\n✅ 获取报价成功 | Quote received")
                    print(f"预计获得 | Expected output: {int(data.get('outAmount', 0))/1_000_000:.2f} VINE")
                    print(f"价格影响 | Price impact: {data.get('priceImpact', 0)}%")
                    return data
                    
                error_text = await response.text()
                print(f"\n❌ 获取报价失败 | Failed to get quote: {error_text}")
                return None
                
    except Exception as e:
        print(f"\n❌ 错误 | Error: {str(e)}")
        return None

async def execute_swap(pool_info: Dict, quote: Dict, wallet_key: str) -> Optional[str]:
    """Execute swap on Orca"""
    try:
        if not pool_info or not quote:
            print("\n❌ 无交易池信息或报价 | No pool info or quote")
            return None
            
        url = "https://api.orca.so/v1/swap"
        swap_data = {
            "owner": wallet_key,
            "whirlpoolAddress": pool_info['address'],
            "quote": quote
        }
        
        print("\n🔄 执行交易中... | Executing swap...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=swap_data) as response:
                if response.status == 200:
                    data = await response.json()
                    signature = data.get('signature')
                    if signature:
                        print(f"\n✅ 交易成功 | Trade successful")
                        print(f"交易签名 | Transaction signature: {signature}")
                        print(f"查看交易 | View transaction: https://solscan.io/tx/{signature}")
                        return signature
                        
                error_text = await response.text()
                print(f"\n❌ 交易失败 | Trade failed: {error_text}")
                return None
                
    except Exception as e:
        print(f"\n❌ 错误 | Error: {str(e)}")
        return None

async def execute_buy() -> None:
    """Execute buy trade for VINE token"""
    try:
        # Get whirlpool info
        pool_info = await get_whirlpool_info()
        if not pool_info:
            return
            
        # Get quote
        quote = await get_quote(pool_info)
        if not quote:
            return
            
        # Get wallet key from environment
        wallet_key = os.getenv('WALLET_KEY')
        if not wallet_key:
            print("\n❌ 钱包密钥未设置 | Wallet key not set")
            return
            
        # Execute swap
        signature = await execute_swap(pool_info, quote, wallet_key)
        
        if signature:
            await logging_service.log_user_action(
                'buy_executed',
                {
                    'token': 'VINE',
                    'amount': '5 SOL worth',
                    'signature': signature,
                    'status': 'success',
                    'pool': pool_info,
                    'quote': quote
                },
                'system'
            )
        else:
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
