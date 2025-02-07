import time
import os
from datetime import datetime, timedelta
from termcolor import cprint
from src.data.jupiter_client import JupiterClient

# Token addresses
AI16Z_TOKEN = "HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC"
SWARM_TOKEN = "8sN9549P3Zn6xpQRqpApN57xzkCh6sJxLwuEjcG2W4Ji"
SOL_TOKEN = "So11111111111111111111111111111111111111112"

# Trading parameters
TRADE_AMOUNT_SOL = 0.001
TRADE_INTERVAL_SECONDS = 15 * 60  # 15 minutes
VERIFICATION_DURATION_HOURS = 2

def execute_trade(client: JupiterClient, input_token: str, output_token: str, amount_lamports: int) -> bool:
    try:
        quote = client.get_quote(input_token, output_token, str(amount_lamports))
        if not quote:
            return False
            
        signature = client.execute_swap(quote, os.getenv("WALLET_ADDRESS"))
        if not signature:
            return False
            
        cprint(f"✅ Trade executed: {signature}", "green")
        cprint(f"🔍 View on Solscan: https://solscan.io/tx/{signature}", "cyan")
        return True
    except Exception as e:
        cprint(f"❌ Trade failed: {str(e)}", "red")
        return False

def main():
    client = JupiterClient()
    wallet_address = os.getenv("WALLET_ADDRESS")
    if not wallet_address:
        cprint("❌ WALLET_ADDRESS environment variable not set", "red")
        return
        
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=VERIFICATION_DURATION_HOURS)
    trade_amount_lamports = int(TRADE_AMOUNT_SOL * 1e9)
    
    cprint(f"🚀 Starting trading verification for {VERIFICATION_DURATION_HOURS} hours", "cyan")
    cprint(f"⏰ Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}", "cyan")
    cprint(f"⏰ End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}", "cyan")
    cprint(f"💰 Trade amount: {TRADE_AMOUNT_SOL} SOL", "cyan")
    cprint(f"⏱️ Trade interval: {TRADE_INTERVAL_SECONDS} seconds", "cyan")
    
    last_trade_time = datetime.now() - timedelta(seconds=TRADE_INTERVAL_SECONDS)
    
    while datetime.now() < end_time:
        try:
            current_time = datetime.now()
            time_since_last_trade = (current_time - last_trade_time).total_seconds()
            
            if time_since_last_trade >= TRADE_INTERVAL_SECONDS:
                cprint("\n🔄 Executing trades...", "cyan")
                
                # Trade SOL for AI16z
                cprint("\n💱 Trading SOL for AI16z...", "cyan")
                success = execute_trade(client, SOL_TOKEN, AI16Z_TOKEN, trade_amount_lamports)
                if success:
                    cprint("✅ AI16z trade completed", "green")
                
                time.sleep(5)  # Wait 5 seconds between trades
                
                # Trade SOL for SWARM
                cprint("\n💱 Trading SOL for SWARM...", "cyan")
                success = execute_trade(client, SOL_TOKEN, SWARM_TOKEN, trade_amount_lamports)
                if success:
                    cprint("✅ SWARM trade completed", "green")
                
                last_trade_time = current_time
                
            time_left = end_time - current_time
            cprint(f"\n⏳ Time remaining: {str(time_left).split('.')[0]}", "cyan")
            time.sleep(60)  # Check every minute
            
        except Exception as e:
            cprint(f"❌ Error: {str(e)}", "red")
            time.sleep(60)  # Wait a minute before retrying
            
    cprint("\n✅ Trading verification completed!", "green")

if __name__ == "__main__":
    main()
