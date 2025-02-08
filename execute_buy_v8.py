import os
import json
import asyncio
import aiohttp
from typing import Optional, Dict, Any
from decimal import Decimal
from src.data.chainstack_enhanced_client import chainstack_enhanced_client
from src.data.jupiter_client_v3 import jupiter_client
from src.services.logging_service import logging_service

# Constants
SLIPPAGE_BPS = 250  # 2.5%
SOL_DECIMALS = 9
LAMPORTS_PER_SOL = 1_000_000_000  # 10^9

# Token addresses
SOL_MINT = "So11111111111111111111111111111111111111112"
VINE_MINT = "6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump"
POOL_ADDRESS = "58fzJMbX5PatnfJPqWWsqkVFPRKptkbb5r2vCw4Qq3z9"

async def analyze_market() -> Optional[Dict]:
    """Analyze market conditions using Chainstack Enhanced RPC"""
    try:
        print("\n🔍 分析市场中... | Analyzing market...")
        analysis = await chainstack_enhanced_client.analyze_token_and_pool(VINE_MINT, POOL_ADDRESS)
        
        if not analysis:
            print("\n❌ 市场分析失败 | Market analysis failed")
            return None
            
        # Calculate trade amount (half position = 5 SOL)
        amount = str(5 * LAMPORTS_PER_SOL)
        
        return {
            'analysis': analysis,
            'amount': amount,
            'input_mint': SOL_MINT,
            'output_mint': VINE_MINT
        }
        
    except Exception as e:
        print(f"\n❌ 错误 | Error: {str(e)}")
        return None

async def execute_buy(market_data: Dict) -> None:
    """Execute buy trade for VINE token"""
    try:
        if not market_data:
            print("\n❌ 无市场数据 | No market data")
            return
            
        # Get quote
        quote = await jupiter_client.get_quote(
            input_mint=market_data['input_mint'],
            output_mint=market_data['output_mint'],
            amount=market_data['amount']
        )
        
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
        signature = await jupiter_client.execute_swap(quote, wallet_key)
        
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
                    'market_data': market_data['analysis']
                },
                'system'
            )
        else:
            print("\n❌ 交易失败 | Trade failed")
            await logging_service.log_error(
                "Trade execution failed",
                {
                    'input_mint': market_data['input_mint'],
                    'output_mint': market_data['output_mint'],
                    'amount': market_data['amount'],
                    'status': 'failed',
                    'market_data': market_data['analysis']
                },
                'system'
            )
            
    except Exception as e:
        print(f"\n❌ 错误 | Error: {str(e)}")
        await logging_service.log_error(str(e), locals(), 'system')

async def main() -> None:
    """Main entry point"""
    try:
        # First analyze market
        market_data = await analyze_market()
        if not market_data:
            return
            
        # Execute buy if market analysis is successful
        await execute_buy(market_data)
        
    except KeyboardInterrupt:
        print("\n👋 退出程序 | Exiting program")
    except Exception as e:
        print(f"\n❌ 错误 | Error: {str(e)}")
        await logging_service.log_error(str(e), locals(), 'system')

if __name__ == "__main__":
    asyncio.run(main())
