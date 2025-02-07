import time
from datetime import datetime, timedelta
import requests
from termcolor import cprint
import pandas as pd
from src.data.chainstack_client import ChainStackClient

def verify_trading(duration_hours=2, wallet_address="4BKPzFyjBaRP3L1PNDf3xTerJmbbxxESmDmZJ2CZYdQ5"):
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=duration_hours)
    
    cprint(f"\n🔍 Starting trading verification for {wallet_address}", "cyan")
    cprint(f"📅 Verifying from {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n", "cyan")
    
    client = ChainStackClient()
    trades_verified = 0
    total_volume = 0
    
    while datetime.now() < end_time:
        try:
            # Get wallet balance
            sol_balance = client.get_wallet_balance(wallet_address)
            cprint(f"Current SOL Balance: {sol_balance:.6f} SOL", "cyan")
            
            # Check Solscan for recent transactions
            response = requests.get(
                f"https://public-api.solscan.io/account/transactions",
                params={"account": wallet_address, "limit": 10},
                headers={"accept": "application/json"}
            )
            
            if response.status_code == 200:
                transactions = response.json()
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                for tx in transactions:
                    tx_hash = tx.get('txHash', '')
                    
                    # Get detailed transaction info
                    tx_response = requests.get(
                        f"https://public-api.solscan.io/transaction/{tx_hash}",
                        headers={"accept": "application/json"}
                    )
                    
                    if tx_response.status_code == 200:
                        tx_details = tx_response.json()
                        status = tx_details.get("status") == "Success"
                        fee = tx_details.get("fee", 0) / 1e9
                        
                        # Verify Jupiter swap
                        is_swap = False
                        swap_amount = 0
                        for log in tx_details.get("logMessages", []):
                            if "Program log: Instruction: Swap" in log:
                                is_swap = True
                                # Extract swap amount from logs if possible
                                try:
                                    amount_str = log.split("amount: ")[1].split()[0]
                                    swap_amount = float(amount_str) / 1e6  # Convert from lamports
                                except:
                                    pass
                        
                        if is_swap and status:
                            trades_verified += 1
                            total_volume += swap_amount
                            cprint(f"\n[{current_time}] ✅ Verified Trade:", "green")
                            cprint(f"  Transaction: {tx_hash}", "cyan")
                            cprint(f"  Amount: {swap_amount:.2f} USDC", "cyan")
                            cprint(f"  Fee: {fee:.6f} SOL", "cyan")
                            cprint(f"  View: https://solscan.io/tx/{tx_hash}", "cyan")
                        elif is_swap:
                            cprint(f"\n[{current_time}] ❌ Failed Trade:", "red")
                            cprint(f"  Transaction: {tx_hash}", "red")
                            cprint(f"  View: https://solscan.io/tx/{tx_hash}", "red")
            
            time.sleep(60)
            
        except Exception as e:
            cprint(f"❌ Error verifying trades: {e}", "red")
            time.sleep(10)
    
    cprint("\n📊 Trading Verification Summary:", "cyan")
    cprint(f"✅ Verified Trades: {trades_verified}", "green")
    cprint(f"💰 Total Volume: {total_volume:.2f} USDC", "green")
    cprint(f"⏱️ Duration: {duration_hours} hours", "cyan")
    cprint(f"🔍 Monitored from {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "cyan")

if __name__ == "__main__":
    try:
        verify_trading()
    except KeyboardInterrupt:
        cprint("\n👋 Verification stopped by user", "yellow")
    except Exception as e:
        cprint(f"\n❌ Fatal error: {e}", "red")
