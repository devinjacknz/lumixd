import os
import json
import asyncio
import aiohttp
from typing import Optional, Dict, Any
from decimal import Decimal
from src.data.jupiter_client_v3 import jupiter_client
from src.services.logging_service import logging_service

# Constants
SLIPPAGE_BPS = 250  # 2.5%
JUPITER_API_URL = "https://quote-api.jup.ag/v6"
SOL_DECIMALS = 9
LAMPORTS_PER_SOL = 1_000_000_000  # 10^9

# Token addresses
SOL_MINT = "So11111111111111111111111111111111111111112"
VINE_MINT = "6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump"

async def get_quote(input_mint: str, output_mint: str, amount: str) -> Optional[Dict[str, Any]]:
    """Get quote from Jupiter API"""
    try:
        url = f"{JUPITER_API_URL}/quote"
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": amount,
            "slippageBps": SLIPPAGE_BPS
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    print(f"\n❌ API错误 | API error: {await response.text()}")
                    return None
                return await response.json()
    except Exception as e:
        print(f"\n❌ 获取报价错误 | Quote error: {str(e)}")
        return None

async def execute_buy() -> None:
    """Execute buy trade for VINE token"""
    try:
        # Parameters for Jupiter API
        input_mint = SOL_MINT
        output_mint = VINE_MINT
        amount = str(5 * LAMPORTS_PER_SOL)  # 5 SOL in lamports
        
        print("\n🔄 获取报价中... | Getting quote...")
        print(f"输入代币 | Input token: SOL ({input_mint})")
        print(f"输出代币 | Output token: VINE ({output_mint})")
        print(f"数量 | Amount: 5 SOL")
        print(f"滑点 | Slippage: {SLIPPAGE_BPS/100}%")
        
        # Get quote
        quote = await get_quote(input_mint, output_mint, amount)
        
        if not quote:
            print("\n❌ 获取报价失败 | Failed to get quote")
            return
            
        print(f"\n📊 交易详情 | Trade details:")
        print(f"预计获得 | Expected output: {quote.get('outAmount', 'unknown')} VINE")
        print(f"价格影响 | Price impact: {quote.get('priceImpactPct', '0')}%")
        
        # Execute swap
        wallet_key = os.getenv('WALLET_KEY')
        if not wallet_key:
            print("\n❌ 钱包密钥未设置 | Wallet key not set")
            return
            
        print("\n🔄 执行交易中... | Executing trade...")
        
        # Execute swap with proper error handling
        try:
            signature = await jupiter_client.execute_swap(quote, wallet_key)
            if not signature:
                raise Exception("No signature returned from swap execution")
                
            print(f"\n✅ 交易成功 | Trade successful")
            print(f"交易签名 | Transaction signature: {signature}")
            print(f"查看交易 | View transaction: https://solscan.io/tx/{signature}")
            
            await logging_service.log_user_action(
                'buy_executed',
                {
                    'token': 'VINE',
                    'amount': '5 SOL worth',
                    'signature': signature,
                    'status': 'success'
                },
                'system'
            )
        except Exception as e:
            print(f"\n❌ 交易执行错误 | Trade execution error: {str(e)}")
            await logging_service.log_error(
                "Trade execution error",
                {
                    'error': str(e),
                    'input_mint': input_mint,
                    'output_mint': output_mint,
                    'amount': amount,
                    'status': 'failed'
                },
                'system'
            )
            return None
        
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
                    'status': 'success'
                },
                'system'
            )
        else:
            print("\n❌ 交易失败 | Trade failed")
            await logging_service.log_error(
                "Trade execution failed",
                {
                    'input_mint': input_mint,
                    'output_mint': output_mint,
                    'amount': amount,
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
