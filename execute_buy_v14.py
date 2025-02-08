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

# OpenBook program ID
OPENBOOK_PROGRAM_ID = "srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX"

async def get_market_info() -> Optional[Dict]:
    """Get market information from OpenBook"""
    try:
        url = "https://api.openbook-solana.com/v1/markets"
        params = {
            "baseToken": VINE_MINT,
            "quoteToken": SOL_MINT
        }
        
        print("\n🔍 获取市场信息中... | Getting market info...")
        print(f"基础代币 | Base token: VINE ({VINE_MINT})")
        print(f"计价代币 | Quote token: SOL ({SOL_MINT})")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('markets'):
                        market = data['markets'][0]
                        print(f"\n✅ 获取市场信息成功 | Market info received")
                        print(f"市场地址 | Market address: {market.get('address')}")
                        print(f"当前价格 | Current price: {market.get('price')}")
                        return market
                    
                error_text = await response.text()
                print(f"\n❌ 获取市场信息失败 | Failed to get market info: {error_text}")
                return None
                
    except Exception as e:
        print(f"\n❌ 错误 | Error: {str(e)}")
        return None

async def get_quote(market_info: Dict) -> Optional[Dict]:
    """Get quote for trade"""
    try:
        if not market_info:
            print("\n❌ 无市场信息 | No market info")
            return None
            
        url = "https://api.openbook-solana.com/v1/quote"
        quote_data = {
            "marketAddress": market_info['address'],
            "side": "buy",
            "amount": str(POSITION_SIZE),
            "slippageBps": str(SLIPPAGE_BPS)
        }
        
        print("\n🔍 获取报价中... | Getting quote...")
        print(f"数量 | Amount: 5 SOL")
        print(f"滑点 | Slippage: {SLIPPAGE_BPS/100}%")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=quote_data) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"\n✅ 获取报价成功 | Quote received")
                    print(f"预计获得 | Expected output: {data.get('expectedOutput')} VINE")
                    print(f"价格影响 | Price impact: {data.get('priceImpact')}%")
                    return data
                    
                error_text = await response.text()
                print(f"\n❌ 获取报价失败 | Failed to get quote: {error_text}")
                return None
                
    except Exception as e:
        print(f"\n❌ 错误 | Error: {str(e)}")
        return None

async def execute_trade(market_info: Dict, quote: Dict, wallet_key: str) -> Optional[str]:
    """Execute trade on OpenBook"""
    try:
        if not market_info or not quote:
            print("\n❌ 无市场信息或报价 | No market info or quote")
            return None
            
        url = "https://api.openbook-solana.com/v1/trade"
        trade_data = {
            "marketAddress": market_info['address'],
            "ownerAddress": wallet_key,
            "side": "buy",
            "amount": str(POSITION_SIZE),
            "slippageBps": str(SLIPPAGE_BPS),
            "quote": quote
        }
        
        print("\n🔄 执行交易中... | Executing trade...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=trade_data) as response:
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
        # Get market info
        market_info = await get_market_info()
        if not market_info:
            return
            
        # Get quote
        quote = await get_quote(market_info)
        if not quote:
            return
            
        # Get wallet key from environment
        wallet_key = os.getenv('WALLET_KEY')
        if not wallet_key:
            print("\n❌ 钱包密钥未设置 | Wallet key not set")
            return
            
        # Execute trade
        signature = await execute_trade(market_info, quote, wallet_key)
        
        if signature:
            await logging_service.log_user_action(
                'buy_executed',
                {
                    'token': 'VINE',
                    'amount': '5 SOL worth',
                    'signature': signature,
                    'status': 'success',
                    'market': market_info,
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
