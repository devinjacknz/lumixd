import os
import time
from datetime import datetime, timedelta
import requests
from termcolor import cprint
import pandas as pd
from src.data.chainstack_client import ChainStackClient
from src.agents.sentiment_agent import SentimentAgent

def get_latest_sentiment_time() -> datetime:
    """Get timestamp of latest sentiment data"""
    try:
        agent = SentimentAgent()
        return agent.get_latest_sentiment_time()
    except Exception as e:
        cprint(f"Error getting sentiment time: {e}", "red")
        return datetime.min

def monitor_trading_metrics():
    """Monitor key trading metrics"""
    retry_count = 0
    max_retries = 3
    
    try:
        while True:
            try:
                # Check API latency
                start_time = time.time()
                endpoint = os.getenv('RPC_ENDPOINT')
                if not endpoint:
                    cprint("⚠️ RPC_ENDPOINT not set", "yellow")
                    time.sleep(10)
                    continue
                    
                response = requests.get(endpoint, timeout=5)  # 5 second timeout
                latency = (time.time() - start_time) * 1000
                
                if latency > 150:
                    cprint(f"⚠️ High API latency: {latency:.2f}ms", "yellow")
                    
                # Reset retry count on success
                retry_count = 0
                
                # Check sentiment data freshness
                last_sentiment = get_latest_sentiment_time()
                if (datetime.now() - last_sentiment).seconds > 300:
                    cprint("⚠️ Sentiment data stale (>5 minutes old)", "yellow")
                    
            except requests.exceptions.RequestException as e:
                retry_count += 1
                if retry_count >= max_retries:
                    cprint(f"❌ API failed after {max_retries} retries", "red")
                    retry_count = 0  # Reset for next attempt
                else:
                    cprint(f"⚠️ API error (attempt {retry_count}/{max_retries})", "yellow")
                    
            except Exception as e:
                cprint(f"❌ Error in monitoring loop: {str(e)}", "red")
                
            time.sleep(10)  # Check every 10 seconds
            
    except KeyboardInterrupt:
        cprint("Monitoring stopped by user", "yellow")
    except Exception as e:
        cprint(f"❌ Fatal error in monitoring: {str(e)}", "red")

def verify_trading(duration_minutes=5, wallet_address="4BKPzFyjBaRP3L1PNDf3xTerJmbbxxESmDmZJ2CZYdQ5"):
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=duration_minutes)
    
    cprint(f"\n🔍 Starting trading verification for {wallet_address}", "cyan")
    cprint(f"📅 Verifying from {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n", "cyan")
    
    client = ChainStackClient()
    trades_verified = 0
    total_volume = 0
    
    # Verify USDC ATA and balances
    from src.agents.trading_agent import TradingAgent
    agent = TradingAgent()
    balances_ok, reason = agent.check_balances()
    cprint(f"\n💰 Balance check: {'✅' if balances_ok else '❌'} {reason}", "green" if balances_ok else "red")
    
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
    
    # Check transaction logs
    log_file = f"logs/transactions_{datetime.now().strftime('%Y%m%d')}.log"
    if os.path.exists(log_file):
        with open(log_file) as f:
            logs = f.read()
            cprint(f"\n📝 Transaction logs found: {len(logs.split('\\n'))} entries", "green")
    else:
        cprint("\n⚠️ No transaction logs found", "yellow")
    
    cprint("\n📊 Trading Verification Summary:", "cyan")
    cprint(f"✅ Verified Trades: {trades_verified}", "green")
    cprint(f"💰 Total Volume: {total_volume:.2f} USDC", "green")
    cprint(f"⏱️ Duration: {duration_minutes} minutes", "cyan")
    cprint(f"🔍 Monitored from {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "cyan")

if __name__ == "__main__":
    try:
        # Run monitoring in parallel with verification
        from multiprocessing import Process
        monitor_process = Process(target=monitor_trading_metrics)
        monitor_process.start()
        
        verify_trading()
        
        monitor_process.terminate()
        monitor_process.join()
    except KeyboardInterrupt:
        cprint("\n👋 Verification stopped by user", "yellow")
    except Exception as e:
        cprint(f"\n❌ Fatal error: {e}", "red")
