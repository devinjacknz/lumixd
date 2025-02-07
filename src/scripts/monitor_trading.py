import time
from datetime import datetime, timedelta
import requests
from termcolor import cprint

def monitor_trading(duration_hours=2, wallet_address="4BKPzFyjBaRP3L1PNDf3xTerJmbbxxESmDmZJ2CZYdQ5"):
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=duration_hours)
    
    cprint(f"\n🔍 Starting trading monitor for {wallet_address}", "cyan")
    cprint(f"📅 Monitoring from {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n", "cyan")
    
    retry_count = 0
    max_retries = 3
    
    while datetime.now() < end_time:
        try:
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
                    cprint(f"[{current_time}] Transaction: {tx_hash}", "cyan")
                    
                    # Get detailed transaction info
                    tx_response = requests.get(
                        f"https://public-api.solscan.io/transaction/{tx_hash}",
                        headers={"accept": "application/json"}
                    )
                    
                    if tx_response.status_code == 200:
                        tx_details = tx_response.json()
                        status = "✅" if tx_details.get("status") == "Success" else "❌"
                        fee = tx_details.get("fee", 0) / 1e9
                        
                        cprint(f"  Status: {status} {tx_details.get('status', 'Unknown')}", "green" if status == "✅" else "red")
                        cprint(f"  Fee: {fee:.6f} SOL", "cyan")
                        cprint(f"  View on Solscan: https://solscan.io/tx/{tx_hash}", "cyan")
                        
                        # Check for Jupiter swaps
                        for log in tx_details.get("logMessages", []):
                            if "Program log: Instruction: Swap" in log:
                                cprint(f"  Type: Jupiter Swap ♻️", "magenta")
                                break
                        
                        retry_count = 0  # Reset retry count on success
                    else:
                        cprint(f"  ⚠️ Could not fetch transaction details", "yellow")
            else:
                retry_count += 1
                if retry_count >= max_retries:
                    cprint(f"❌ Error: API failed after {max_retries} retries", "red")
                    retry_count = 0
                    time.sleep(60)  # Longer sleep after max retries
                else:
                    cprint(f"⚠️ API error (attempt {retry_count}/{max_retries})", "yellow")
                    time.sleep(10 * retry_count)  # Exponential backoff
            
            time.sleep(60)
            
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                cprint(f"❌ Error after {max_retries} retries: {e}", "red")
                retry_count = 0
                time.sleep(60)
            else:
                cprint(f"⚠️ Error (attempt {retry_count}/{max_retries}): {e}", "yellow")
                time.sleep(10 * retry_count)
            
    cprint("\n✅ Trading verification complete!", "green")
    cprint(f"📊 Monitored from {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "green")

if __name__ == "__main__":
    try:
        monitor_trading()
    except KeyboardInterrupt:
        cprint("\n👋 Monitoring stopped by user", "yellow")
    except Exception as e:
        cprint(f"\n❌ Fatal error: {e}", "red")
