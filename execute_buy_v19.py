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
POOL_ADDRESS = "58fzJMbX5PatnfJPqWWsqkVFPRKptkbb5r2vCw4Qq3z9"

async def get_pool_info() -> Optional[Dict]:
    """Get pool information from Raydium API"""
    try:
        url = "https://api.raydium.io/v2/main/pool"
        params = {
            "id": POOL_ADDRESS
        }
        
        print("\n🔍 获取池信息中... | Getting pool info...")
        print(f"池子地址 | Pool address: {POOL_ADDRESS}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"\n✅ 获取池信息成功 | Pool info received")
                    print(f"流动性 | Liquidity: ${data.get('liquidity', 0)}")
                    print(f"24h交易量 | 24h volume: ${data.get('volume24h', 0)}")
                    return data
                    
                error_text = await response.text()
                print(f"\n❌ 获取池信息失败 | Failed to get pool info: {error_text}")
                return None
                
    except Exception as e:
        print(f"\n❌ 错误 | Error: {str(e)}")
        return None

async def get_quote() -> Optional[Dict]:
    """Get quote from Raydium API"""
    try:
        url = "https://api.raydium.io/v2/main/quote"
        quote_data = {
            "inputMint": SOL_MINT,
            "outputMint": VINE_MINT,
            "amount": str(POSITION_SIZE),
            "slippage": SLIPPAGE_BPS,
            "onlyDirectRoute": False
        }
        
        print("\n🔍 获取报价中... | Getting quote...")
        print(f"输入代币 | Input token: SOL ({SOL_MINT})")
        print(f"输出代币 | Output token: VINE ({VINE_MINT})")
        print(f"数量 | Amount: 5 SOL")
        print(f"滑点 | Slippage: {SLIPPAGE_BPS/100}%")
        
        headers = {"Content-Type": "application/json"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=quote_data, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"\n✅ 获取报价成功 | Quote received")
                    print(f"输出数量 | Output amount: {int(data.get('outAmount', 0))/1_000_000:.2f} VINE")
                    print(f"价格影响 | Price impact: {data.get('priceImpact', 0)}%")
                    return data
                    
                error_text = await response.text()
                print(f"\n❌ 获取报价失败 | Failed to get quote: {error_text}")
                return None
                
    except Exception as e:
        print(f"\n❌ 错误 | Error: {str(e)}")
        return None

async def get_swap_instructions(quote: Dict, wallet_key: str) -> Optional[Dict]:
    """Get swap instructions from Raydium API"""
    try:
        if not quote:
            print("\n❌ 无报价信息 | No quote provided")
            return None
            
        url = "https://api.raydium.io/v2/main/swap"
        swap_data = {
            "ownerAddress": wallet_key,
            "quoteMint": SOL_MINT,
            "targetMint": VINE_MINT,
            "amount": str(POSITION_SIZE),
            "slippage": SLIPPAGE_BPS,
            "onlyDirectRoute": False
        }
        
        print("\n🔄 获取交易指令中... | Getting swap instructions...")
        
        headers = {"Content-Type": "application/json"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=swap_data, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"\n✅ 获取交易指令成功 | Swap instructions received")
                    return data
                    
                error_text = await response.text()
                print(f"\n❌ 获取交易指令失败 | Failed to get swap instructions: {error_text}")
                return None
                
    except Exception as e:
        print(f"\n❌ 错误 | Error: {str(e)}")
        return None

async def execute_swap(swap_response: Dict, wallet_key: str) -> Optional[str]:
    """Execute swap using Raydium API"""
    try:
        if not swap_response:
            print("\n❌ 无交易指令 | No swap instructions")
            return None
            
        url = "https://api.raydium.io/v2/main/swap/execute"
        execute_data = {
            "ownerAddress": wallet_key,
            "swapTransaction": swap_response.get('swapTransaction')
        }
        
        print("\n🔄 执行交易中... | Executing swap...")
        
        headers = {"Content-Type": "application/json"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=execute_data, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    signature = data.get('signature')
                    if signature:
                        print(f"\n✅ 交易成功 | Trade successful")
                        print(f"交易签名 | Transaction signature: {signature}")
                        print(f"查看交易 | View transaction: https://solscan.io/tx/{signature}")
                        
                        # Verify transaction
                        print("\n🔍 验证交易中... | Verifying transaction...")
                        await verify_transaction(signature)
                        
                        return signature
                        
                error_text = await response.text()
                print(f"\n❌ 交易失败 | Trade failed: {error_text}")
                return None
                
    except Exception as e:
        print(f"\n❌ 错误 | Error: {str(e)}")
        return None

async def verify_transaction(signature: str) -> bool:
    """Verify transaction on Solana"""
    try:
        url = os.getenv('RPC_ENDPOINT', 'https://api.mainnet-beta.solana.com')
        verify_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                signature,
                {"encoding": "json", "commitment": "confirmed"}
            ]
        }
        
        headers = {"Content-Type": "application/json"}
        
        for attempt in range(3):
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=verify_data, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('result'):
                            print(f"\n✅ 交易已确认 | Transaction confirmed")
                            return True
                            
            print(f"\n⏳ 等待交易确认... | Waiting for confirmation... (attempt {attempt + 1}/3)")
            await asyncio.sleep(1)
            
        print("\n❌ 交易未确认 | Transaction not confirmed")
        return False
        
    except Exception as e:
        print(f"\n❌ 验证错误 | Verification error: {str(e)}")
        return False

async def execute_buy() -> None:
    """Execute buy trade for VINE token"""
    try:
        # Get pool info first
        pool_info = await get_pool_info()
        if not pool_info:
            return
            
        # Get quote
        quote = await get_quote()
        if not quote:
            return
            
        # Get wallet key from environment
        wallet_key = os.getenv('WALLET_KEY')
        if not wallet_key:
            print("\n❌ 钱包密钥未设置 | Wallet key not set")
            return
            
        # Get swap instructions
        swap_response = await get_swap_instructions(quote, wallet_key)
        if not swap_response:
            return
            
        # Execute swap
        signature = await execute_swap(swap_response, wallet_key)
        
        if signature:
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
