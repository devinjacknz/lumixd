import asyncio
import os
from dotenv import load_dotenv
from src.agents.trading_agent import TradingAgent
from termcolor import cprint

async def test_raydium_trade():
    """Test Raydium trade execution with specific token"""
    # Load environment variables
    load_dotenv()
    
    # Initialize trading agent
    agent = TradingAgent(instance_id='test')
    
    try:
        # Check initial balance
        balances_ok, reason = await agent.check_balances()
        if not balances_ok:
            cprint(f"❌ Balance check failed: {reason}", "red")
            return
            
        # Prepare trade request
        trade_request = {
            'token': "6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump",
            'direction': 'buy',
            'amount': 0.02,  # Fixed 0.02 SOL amount
            'slippage_bps': 250  # 2.5% slippage
        }
        
        # Execute trade
        cprint("\n🔄 Executing test trade...", "cyan")
        signature = await agent.execute_trade(trade_request)
        
        if signature:
            cprint(f"\n✅ Trade successful!", "green")
            cprint(f"Transaction signature: {signature}", "cyan")
            cprint(f"View on Solscan: https://solscan.io/tx/{signature}", "cyan")
            
            # Check final balance
            final_balances_ok, final_reason = await agent.check_balances()
            cprint(f"\nFinal balance check: {final_reason}", "cyan")
        else:
            cprint("\n❌ Trade failed", "red")
            
    except Exception as e:
        cprint(f"\n❌ Test failed: {str(e)}", "red")
        
if __name__ == "__main__":
    asyncio.run(test_raydium_trade())
