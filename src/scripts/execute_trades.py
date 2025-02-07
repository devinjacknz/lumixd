import os
from termcolor import cprint
from src.nice_funcs import market_buy

def execute_ai16z_trades():
    """Execute two small trades for AI16z token"""
    try:
        ai16z_address = "HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC"
        trade_size = 0.001  # 0.001 SOL per trade
        
        for i in range(2):
            cprint(f"\n🔄 Executing trade {i+1} of 2 for {trade_size} SOL...", "cyan")
            cprint(f"💰 Trading {trade_size} SOL ({int(trade_size * 1e9)} lamports)...", "yellow")
            
            success = market_buy(ai16z_address, str(int(trade_size * 1e9)))
            if not success:
                cprint(f"❌ Trade {i+1} failed\n", "red")
            else:
                cprint(f"✅ Trade {i+1} completed successfully\n", "green")
                
    except Exception as e:
        cprint(f"❌ Error executing trades: {str(e)}", "red")
    finally:
        cprint("🧹 Cleaning up temporary data...", "cyan")

if __name__ == "__main__":
    execute_ai16z_trades()
