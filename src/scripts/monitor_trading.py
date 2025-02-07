import time
from datetime import datetime, timedelta
import requests
from termcolor import cprint

def monitor_trading(duration_hours=2, wallet_address="4BKPzFyjBaRP3L1PNDf3xTerJmbbxxESmDmZJ2CZYdQ5"):
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=duration_hours)
    
    cprint(f"\n🔍 Starting trading monitor for {wallet_address}", "cyan")
    cprint(f"📅 Monitoring from {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n", "cyan")
    
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
                    cprint(f"[{current_time}] Transaction: {tx['txHash']}", "cyan")
                    if "status" in tx:
                        status = "✅" if tx["status"] == "Success" else "❌"
                        cprint(f"  Status: {status} {tx['status']}", "green" if status == "✅" else "red")
            else:
                cprint(f"❌ Error: API returned status code {response.status_code}", "red")
            
            time.sleep(60)
            
        except Exception as e:
            cprint(f"❌ Error monitoring transactions: {e}", "red")
            time.sleep(10)
            
    cprint("\n✅ Trading verification complete!", "green")
    cprint(f"📊 Monitored from {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "green")

if __name__ == "__main__":
    monitor_trading()
