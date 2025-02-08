import asyncio
import os
from dotenv import load_dotenv
from src.agents.trading_agent import TradingAgent

async def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize trading agent
    agent = TradingAgent()
    
    # Token address to trade
    token_address = "6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump"
    
    print(f"🔄 Starting trade sequence for token: {token_address}")
    
    # Execute trades
    results = await agent.execute_small_trades_sequence(token_address)
    
    # Print results
    for i, result in enumerate(results, 1):
        if result['status'] == 'success':
            print(f"✅ Trade {i}: {result['direction'].upper()} {result['amount']} SOL - Signature: {result['signature']}")
        else:
            print(f"❌ Trade {i}: {result['direction'].upper()} {result['amount']} SOL - Failed: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(main())
