import requests
import json
import os
import time
from datetime import datetime
from termcolor import cprint

class TradeVerifier:
    def __init__(self):
        self.rpc_url = os.getenv("RPC_ENDPOINT")
        if not self.rpc_url:
            raise ValueError("RPC_ENDPOINT environment variable is required")
        self.headers = {"Content-Type": "application/json"}
        self.wallet_address = os.getenv("WALLET_KEY")
        if not self.wallet_address:
            raise ValueError("WALLET_KEY environment variable is required")
        self.token_address = "6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump"
        
    def verify_transaction(self, signature):
        """Verify transaction status and details"""
        try:
            # Check transaction status
            response = requests.post(
                self.rpc_url,
                headers=self.headers,
                json={
                    "jsonrpc": "2.0",
                    "id": "verify-tx",
                    "method": "getSignatureStatuses",
                    "params": [[signature], {"searchTransactionHistory": True}]
                }
            )
            response.raise_for_status()
            result = response.json().get("result", {}).get("value", [{}])[0]
            
            if result:
                confirmation_status = result.get("confirmationStatus")
                error = result.get("err")
                
                print("\n交易验证 Transaction Verification:")
                print("================================")
                print(f"签名 Signature: {signature}")
                print(f"状态 Status: {confirmation_status}")
                print(f"错误 Error: {error if error else 'None'}")
                print(f"确认数 Confirmations: {result.get('confirmations', 'max')}")
                print(f"🔍 Solscan链接 Link: https://solscan.io/tx/{signature}")
                
                return confirmation_status == "finalized" and not error
            return False
            
        except Exception as e:
            print(f"❌ 验证失败 Verification failed: {str(e)}")
            return False
            
    def check_token_balance(self):
        """Check token balance for the wallet"""
        try:
            response = requests.post(
                self.rpc_url,
                headers=self.headers,
                json={
                    "jsonrpc": "2.0",
                    "id": "get-token-balance",
                    "method": "getTokenAccountsByOwner",
                    "params": [
                        self.wallet_address,
                        {"mint": self.token_address},
                        {"encoding": "jsonParsed"}
                    ]
                }
            )
            response.raise_for_status()
            accounts = response.json().get("result", {}).get("value", [])
            
            if accounts:
                balance = accounts[0].get("account", {}).get("data", {}).get("parsed", {}).get("info", {}).get("tokenAmount", {}).get("uiAmount", 0)
                print(f"\n代币余额 Token Balance: {balance}")
                return balance
            return 0
            
        except Exception as e:
            print(f"❌ 余额查询失败 Balance check failed: {str(e)}")
            return 0
            
    def monitor_trade_execution(self, signature, max_retries=10):
        """Monitor trade execution with retries"""
        print("\n监控交易执行 Monitoring Trade Execution:")
        print("===================================")
        
        retry_count = 0
        delay = 1.0
        
        while retry_count < max_retries:
            if self.verify_transaction(signature):
                print("\n✅ 交易已确认 Transaction confirmed")
                initial_balance = self.check_token_balance()
                print(f"初始余额 Initial Balance: {initial_balance}")
                return True
                
            retry_count += 1
            if retry_count < max_retries:
                print(f"\n⏳ 重试中 Retrying ({retry_count}/{max_retries})...")
                time.sleep(delay)
                delay *= 1.5
                
        print("\n❌ 交易确认超时 Transaction confirmation timed out")
        return False

def main():
    try:
        # Test transaction signature from our test execution
        test_signature = "37Yj1wHEXiaqYr23qjWj28ry6yGdUJcEyA8Sg9WyqUbicHTwyDaxwFQufyLExsadR17fYjctPDGrar3yEiDxRM4L"
        
        verifier = TradeVerifier()
        if verifier.monitor_trade_execution(test_signature):
            print("\n✅ 交易验证完成 Trade verification completed")
            print("🔍 查看交易详情 View transaction details:")
            print(f"https://solscan.io/tx/{test_signature}")
        else:
            print("\n❌ 交易验证失败 Trade verification failed")
    except Exception as e:
        print(f"\n❌ 验证过程出错 Verification process error: {str(e)}")

if __name__ == "__main__":
    main()
