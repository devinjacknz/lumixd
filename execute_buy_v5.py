import os
import json
import asyncio
import aiohttp
from typing import Optional, Dict, Any, Tuple
from decimal import Decimal
from src.data.jupiter_client_v3 import jupiter_client
from src.data.raydium_sdk_client import raydium_sdk_client
from src.services.logging_service import logging_service

# Constants
SLIPPAGE_BPS = 250  # 2.5%
SOL_DECIMALS = 9
LAMPORTS_PER_SOL = 1_000_000_000  # 10^9

# Token addresses
SOL_MINT = "So11111111111111111111111111111111111111112"
VINE_MINT = "6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump"

async def get_best_quote() -> Tuple[Optional[Dict], str]:
    """Get best quote from available DEXes"""
    amount = str(5 * LAMPORTS_PER_SOL)  # 5 SOL in lamports
    
    print("\n🔄 获取报价中... | Getting quotes...")
    print(f"输入代币 | Input token: SOL ({SOL_MINT})")
    print(f"输出代币 | Output token: VINE ({VINE_MINT})")
    print(f"数量 | Amount: 5 SOL")
    print(f"滑点 | Slippage: {SLIPPAGE_BPS/100}%")
    
    # Try Jupiter first
    jupiter_quote = await jupiter_client.get_quote(
        input_mint=SOL_MINT,
        output_mint=VINE_MINT,
        amount=amount
    )
    
    if jupiter_quote:
        return jupiter_quote, 'jupiter'
        
    print("\n⚠️ Jupiter报价失败，尝试Raydium | Jupiter quote failed, trying Raydium...")
    
    # Try Raydium as fallback
    raydium_quote = await raydium_sdk_client.get_quote(
        input_mint=SOL_MINT,
        output_mint=VINE_MINT,
        amount=amount
    )
    
    if raydium_quote:
        return raydium_quote, 'raydium'
        
    return None, ''

async def execute_buy() -> None:
    """Execute buy trade for VINE token"""
    try:
        # Get best quote
        quote, dex = await get_best_quote()
        
        if not quote:
            print("\n❌ 获取报价失败 | Failed to get quote from all DEXes")
            return
            
        print(f"\n📊 交易详情 | Trade details:")
        print(f"交易所 | DEX: {dex.upper()}")
        print(f"预计获得 | Expected output: {quote.get('outAmount', 'unknown')} VINE")
        print(f"价格影响 | Price impact: {quote.get('priceImpact', quote.get('priceImpactPct', '0'))}%")
        
        # Execute swap
        wallet_key = os.getenv('WALLET_KEY')
        if not wallet_key:
            print("\n❌ 钱包密钥未设置 | Wallet key not set")
            return
            
        print("\n🔄 执行交易中... | Executing trade...")
        
        # Execute on selected DEX
        if dex == 'jupiter':
            signature = await jupiter_client.execute_swap(quote, wallet_key)
        else:
            signature = await raydium_sdk_client.execute_swap(quote, wallet_key)
            
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
                    'dex': dex,
                    'status': 'success'
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
                    'amount': str(5 * LAMPORTS_PER_SOL),
                    'dex': dex,
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
