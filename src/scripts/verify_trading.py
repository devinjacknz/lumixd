import time
import os
import requests
from datetime import datetime, timedelta
from termcolor import cprint
from src.data.jupiter_client import JupiterClient
from src.agents.risk_agent import RiskAgent


# Token addresses
AI16Z_TOKEN = "HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC"
SWARM_TOKEN = "GHoewwgqzpyr4honfYZXDjWVqEQf4UVnNkbzqpqzwxPr"  # Updated SWARM token address
SOL_TOKEN = "So11111111111111111111111111111111111111112"

# Trading parameters
TRADE_AMOUNT_SOL = 0.0001
TRADE_INTERVAL_SECONDS = 15 * 60  # 15 minutes
VERIFICATION_DURATION_HOURS = 2

def execute_trade(client: JupiterClient, risk_agent: RiskAgent, input_token: str, output_token: str, amount_lamports: int) -> bool:
    try:
        # Check risk limits first
        if not risk_agent.check_risk_limits(amount_lamports / 1e9):
            cprint("❌ Risk limits exceeded", "red")
            return False
            
        # Check wallet balance
        response = requests.post(
            os.getenv("RPC_ENDPOINT"),
            headers={"Content-Type": "application/json"},
            json={
                "jsonrpc": "2.0",
                "id": "get-balance",
                "method": "getBalance",
                "params": [os.getenv("WALLET_ADDRESS")]
            }
        )
        response.raise_for_status()
        balance = float(response.json().get("result", {}).get("value", 0)) / 1e9
        
        if balance < amount_lamports / 1e9 * 1.1:  # Add 10% buffer for fees
            cprint(f"❌ Insufficient balance: {balance} SOL", "red")
            return False
            
        # Add delay between trades
        time.sleep(5)
            
        # Check wallet balance
        response = requests.post(
            os.getenv("RPC_ENDPOINT"),
            headers={"Content-Type": "application/json"},
            json={
                "jsonrpc": "2.0",
                "id": "get-balance",
                "method": "getBalance",
                "params": [os.getenv("WALLET_ADDRESS")]
            }
        )
        response.raise_for_status()
        balance = float(response.json().get("result", {}).get("value", 0)) / 1e9
        
        if balance < amount_lamports / 1e9 * 1.1:  # Add 10% buffer for fees
            cprint(f"❌ Insufficient balance: {balance} SOL", "red")
            return False
            
        # Get quote with optimized parameters
        quote = client.get_quote(
            input_token, 
            output_token, 
            str(amount_lamports),
            use_shared_accounts=True,
            force_simpler_route=True
        )
        if not quote:
            cprint("❌ Failed to get quote", "red")
            return False
            
        # Check if route is too complex
        route_plan = quote.get("routePlan", [])
        if len(route_plan) > 2:
            cprint("⚠️ Route too complex, retrying with simpler route", "yellow")
            quote = client.get_quote(
                input_token,
                output_token,
                str(amount_lamports),
                use_shared_accounts=True,
                force_simpler_route=True
            )
        if not quote:
            return False
            
        signature = client.execute_swap(
            quote, 
            os.getenv("WALLET_ADDRESS"),
            use_shared_accounts=True
        )
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
    risk_agent = RiskAgent()
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
                success = execute_trade(client, risk_agent, SOL_TOKEN, AI16Z_TOKEN, trade_amount_lamports)
                if success:
                    cprint("✅ AI16z trade completed", "green")
                
                time.sleep(30)  # Wait 30 seconds between trades
                
                # Trade SOL for SWARM
                cprint("\n💱 Trading SOL for SWARM...", "cyan")
                success = execute_trade(client, risk_agent, SOL_TOKEN, SWARM_TOKEN, trade_amount_lamports)
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
