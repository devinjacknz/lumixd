import os
import json
import asyncio
import aiohttp
from typing import Optional, Dict
from src.data.chainstack_enhanced_client import chainstack_enhanced_client
from src.data.dexscreener_client import dexscreener_client
from src.services.logging_service import logging_service

# Token addresses from DexScreener URL
VINE_TOKEN = "6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump"
POOL_ADDRESS = "58fzJMbX5PatnfJPqWWsqkVFPRKptkbb5r2vCw4Qq3z9"

async def get_comprehensive_analysis() -> Optional[Dict]:
    """Get analysis from both Chainstack and DexScreener"""
    try:
        print("\n🔍 开始全面分析... | Starting comprehensive analysis...")
        
        # Get DexScreener analysis
        dex_analysis = await dexscreener_client.analyze_token_pair(POOL_ADDRESS)
        if not dex_analysis:
            print("\n⚠️ DexScreener分析失败，尝试Chainstack... | DexScreener analysis failed, trying Chainstack...")
            
        # Get Chainstack analysis
        chain_analysis = await chainstack_enhanced_client.analyze_token_and_pool(VINE_TOKEN, POOL_ADDRESS)
        if not chain_analysis:
            print("\n⚠️ Chainstack分析失败 | Chainstack analysis failed")
            
        # Combine analyses
        if dex_analysis or chain_analysis:
            combined = {
                'dexscreener': dex_analysis,
                'chainstack': chain_analysis,
                'summary': {
                    'price': dex_analysis.get('price', {}).get('current') if dex_analysis else chain_analysis.get('analysis', {}).get('price'),
                    'volume24h': dex_analysis.get('volume', {}).get('usd24h') if dex_analysis else chain_analysis.get('analysis', {}).get('volume24h'),
                    'liquidity': dex_analysis.get('liquidity', {}).get('usd') if dex_analysis else chain_analysis.get('analysis', {}).get('liquidity'),
                    'price_change24h': dex_analysis.get('price', {}).get('change24h') if dex_analysis else chain_analysis.get('analysis', {}).get('priceChange24h')
                }
            }
            return combined
            
        return None
        
    except Exception as e:
        print(f"\n❌ 错误 | Error: {str(e)}")
        return None

async def analyze_token() -> Optional[Dict]:
    """Analyze token and pool information from DexScreener URL"""
    try:
        print("\n🔍 开始分析代币... | Starting token analysis...")
        print(f"代币地址 | Token address: {VINE_TOKEN}")
        print(f"池子地址 | Pool address: {POOL_ADDRESS}")
        
        # Get comprehensive analysis from both sources
        dex_analysis = await dexscreener_client.analyze_token_pair(POOL_ADDRESS)
        chain_analysis = await chainstack_enhanced_client.analyze_token_and_pool(VINE_TOKEN, POOL_ADDRESS)
        
        if not dex_analysis and not chain_analysis:
            print("\n❌ 分析失败 | Analysis failed")
            return None
            
        # Combine analyses
        combined_analysis = {
            'token': {
                'address': VINE_TOKEN,
                'name': dex_analysis.get('token', {}).get('name') if dex_analysis else 'VINE',
                'symbol': dex_analysis.get('token', {}).get('symbol') if dex_analysis else 'VINE'
            },
            'market_data': {
                'price': dex_analysis.get('price', {}).get('current') if dex_analysis else chain_analysis.get('analysis', {}).get('price'),
                'price_change_24h': dex_analysis.get('price', {}).get('change24h') if dex_analysis else chain_analysis.get('analysis', {}).get('priceChange24h'),
                'volume_24h': dex_analysis.get('volume', {}).get('usd24h') if dex_analysis else chain_analysis.get('analysis', {}).get('volume24h'),
                'liquidity': dex_analysis.get('liquidity', {}).get('usd') if dex_analysis else chain_analysis.get('analysis', {}).get('liquidity')
            },
            'analysis': {
                'price_trend': dex_analysis.get('analysis', {}).get('price_trend') if dex_analysis else ('up' if chain_analysis.get('analysis', {}).get('priceChange24h', 0) > 0 else 'down'),
                'liquidity_rating': dex_analysis.get('analysis', {}).get('liquidity_rating') if dex_analysis else chain_analysis.get('analysis', {}).get('liquidity_rating', 'unknown'),
                'volume_to_liquidity_ratio': dex_analysis.get('analysis', {}).get('volume_to_liquidity_ratio') if dex_analysis else 0,
                'volatility_24h': chain_analysis.get('analysis', {}).get('volatility24h') if chain_analysis else 0,
                'buy_pressure': chain_analysis.get('analysis', {}).get('buy_pressure') if chain_analysis else 0
            },
            'source': {
                'dexscreener': bool(dex_analysis),
                'chainstack': bool(chain_analysis)
            }
        }
        
        # Print analysis summary
        print("\n📊 分析结果 | Analysis results:")
        print(f"代币名称 | Token name: {combined_analysis['token']['name']} ({combined_analysis['token']['symbol']})")
        print(f"当前价格 | Current price: ${combined_analysis['market_data']['price']}")
        print(f"24h价格变化 | 24h price change: {combined_analysis['market_data']['price_change_24h']}%")
        print(f"24h交易量 | 24h volume: ${combined_analysis['market_data']['volume_24h']}")
        print(f"流动性 | Liquidity: ${combined_analysis['market_data']['liquidity']}")
        print(f"价格趋势 | Price trend: {combined_analysis['analysis']['price_trend']}")
        print(f"流动性评级 | Liquidity rating: {combined_analysis['analysis']['liquidity_rating']}")
        print(f"24h波动率 | 24h volatility: {combined_analysis['analysis']['volatility_24h']}%")
        print(f"买入压力 | Buy pressure: {combined_analysis['analysis']['buy_pressure']*100:.2f}%")
        
        # Log analysis results
        await logging_service.log_user_action(
            'token_analyzed',
            {
                'token': VINE_TOKEN,
                'pool': POOL_ADDRESS,
                'analysis': combined_analysis
            },
            'system'
        )
        
        return combined_analysis
        
    except Exception as e:
        print(f"\n❌ 错误 | Error: {str(e)}")
        await logging_service.log_error(str(e), locals(), 'system')

async def main() -> None:
    """Main entry point"""
    try:
        await analyze_token()
    except KeyboardInterrupt:
        print("\n👋 退出程序 | Exiting program")
    except Exception as e:
        print(f"\n❌ 错误 | Error: {str(e)}")
        await logging_service.log_error(str(e), locals(), 'system')

if __name__ == "__main__":
    asyncio.run(main())
