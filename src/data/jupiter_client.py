from typing import Dict, Optional
import requests
import json
import time
import os
import base64
from datetime import datetime
from termcolor import cprint
from solders.keypair import Keypair
from solders.transaction import Transaction
from dotenv import load_dotenv

# Create logs directory
os.makedirs("logs", exist_ok=True)

load_dotenv()

class JupiterClient:
    def __init__(self):
        self.base_url = "https://quote-api.jup.ag/v6"
        self.headers = {"Content-Type": "application/json"}
        self.slippage_bps = 250  # 2.5% slippage
        self.max_retries = 3
        self.retry_delay = 1000  # 1 second initial delay
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 second between requests
        self.rpc_url = os.getenv("RPC_ENDPOINT")
        if not self.rpc_url:
            raise ValueError("RPC_ENDPOINT environment variable is required")
        
    def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
        
    def get_quote(self, input_mint: str, output_mint: str, amount: float) -> Optional[Dict]:
        """Get quote for token swap"""
        try:
            self._rate_limit()
            url = f"{self.base_url}/quote"
            
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(amount),  # Convert to string to avoid integer overflow
                "slippageBps": self.slippage_bps,
                "maxAccounts": 54
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            cprint(f"❌ Failed to get quote: {str(e)}", "red")
            return None
            
    def execute_swap(self, quote_response: Dict, wallet_pubkey: str) -> Optional[str]:
        """Execute swap transaction using Jupiter API"""
        try:
            self._rate_limit()
            url = f"{self.base_url}/swap"
            payload = {
                "quoteResponse": quote_response,
                "userPublicKey": wallet_pubkey,
                "wrapAndUnwrapSol": True,
                "prioritizationFeeLamports": {
                    "priorityLevelWithMaxLamports": {
                        "maxLamports": 10000000,
                        "priorityLevel": "veryHigh"
                    }
                },
                "dynamicComputeUnitLimit": True
            }
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Get unsigned transaction
            unsigned_tx = data.get("swapTransaction")
            if not unsigned_tx:
                return None
                
            # Sign and send transaction
            wallet_key = Keypair.from_base58_string(os.getenv("SOLANA_PRIVATE_KEY"))
            tx_bytes = base64.b64decode(unsigned_tx)
            tx = Transaction.from_bytes(tx_bytes)
            tx.sign([wallet_key])
            
            # Submit transaction
            response = requests.post(
                self.rpc_url,
                headers=self.headers,
                json={
                    "jsonrpc": "2.0",
                    "id": "submit-tx",
                    "method": "sendTransaction",
                    "params": [
                        tx.to_string(),
                        {"encoding": "base64", "maxRetries": 3}
                    ]
                }
            )
            response.raise_for_status()
            data = response.json()
            signature = data.get("result")
            
            # Monitor transaction
            if signature and self.monitor_transaction(signature):
                return signature
            return None
            
        except Exception as e:
            cprint(f"❌ Failed to execute swap: {str(e)}", "red")
            return None
            
    def _create_ata_transaction(self, mint: str, owner: str, ata: str) -> Optional[str]:
        """Create ATA transaction instruction"""
        try:
            response = requests.post(
                self.rpc_url,
                headers=self.headers,
                json={
                    "jsonrpc": "2.0",
                    "id": "create-ata-tx",
                    "method": "getMinimumBalanceForRentExemption",
                    "params": [165]  # Size of token account
                }
            )
            rent = response.json().get("result", 0)
            
            # Create ATA instruction
            create_ata_ix = {
                "programId": "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",
                "keys": [
                    {"pubkey": owner, "isSigner": True, "isWritable": True},
                    {"pubkey": ata, "isSigner": False, "isWritable": True},
                    {"pubkey": owner, "isSigner": False, "isWritable": False},
                    {"pubkey": mint, "isSigner": False, "isWritable": False},
                    {"pubkey": "11111111111111111111111111111111", "isSigner": False, "isWritable": False},
                    {"pubkey": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA", "isSigner": False, "isWritable": False},
                    {"pubkey": "SysvarRent111111111111111111111111111111111", "isSigner": False, "isWritable": False}
                ],
                "data": f"{rent}"
            }
            
            # Build transaction
            response = requests.post(
                self.rpc_url,
                headers=self.headers,
                json={
                    "jsonrpc": "2.0",
                    "id": "build-tx",
                    "method": "buildTransaction",
                    "params": {
                        "feePayer": owner,
                        "instructions": [create_ata_ix],
                        "recentBlockhash": None
                    }
                }
            )
            return response.json().get("result")
        except Exception as e:
            cprint(f"❌ Failed to create ATA transaction: {str(e)}", "red")
            return None

    def create_token_account(self, mint: str, owner: str) -> Optional[str]:
        """Create Associated Token Account if missing"""
        try:
            wallet_key = Keypair.from_base58_string(os.getenv("SOLANA_PRIVATE_KEY"))
            response = requests.post(
                self.rpc_url,
                headers=self.headers,
                json={
                    "jsonrpc": "2.0",
                    "id": "create-ata",
                    "method": "getAssociatedTokenAddress",
                    "params": [mint, owner]
                }
            )
            ata = response.json().get("result")
            if not ata:
                return None
                
            # Create ATA transaction
            create_tx = self._create_ata_transaction(mint, owner, ata)
            if not create_tx:
                return None
                
            # Sign and send transaction
            tx = Transaction.from_bytes(bytes.fromhex(create_tx))
            tx.sign([wallet_key])
            self._log_transaction("Create ATA", {
                "mint": mint,
                "owner": owner,
                "ata": ata,
                "transaction": tx.to_string()
            })
            return self._send_and_confirm_transaction(tx)
        except Exception as e:
            cprint(f"❌ Failed to create token account: {str(e)}", "red")
            return None

    def _send_and_confirm_transaction(self, tx: Transaction) -> Optional[str]:
        """Send and confirm transaction"""
        try:
            response = requests.post(
                self.rpc_url,
                headers=self.headers,
                json={
                    "jsonrpc": "2.0",
                    "id": "send-tx",
                    "method": "sendTransaction",
                    "params": [
                        tx.to_string(),
                        {"encoding": "base64", "maxRetries": 3}
                    ]
                }
            )
            signature = response.json().get("result")
            if signature and self.monitor_transaction(signature):
                return signature
            return None
        except Exception as e:
            cprint(f"❌ Failed to send transaction: {str(e)}", "red")
            return None

    def _log_transaction(self, action: str, details: dict):
        """Log transaction details for debugging"""
        try:
            log_file = f"logs/transactions_{datetime.now().strftime('%Y%m%d')}.log"
            with open(log_file, "a") as f:
                f.write(f"{datetime.now().isoformat()} - {action}\n")
                f.write(json.dumps(details, indent=2) + "\n\n")
        except Exception as e:
            cprint(f"❌ Failed to log transaction: {str(e)}", "red")

    def monitor_transaction(self, signature: str, max_retries: int = 5) -> bool:
        """Monitor transaction status with exponential backoff"""
        try:
            retry_count = 0
            delay = 1.0  # Initial delay in seconds
            
            while retry_count < max_retries:
                self._rate_limit()
                response = requests.post(
                    self.base_url,
                    headers=self.headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": "get-tx-status",
                        "method": "getSignatureStatuses",
                        "params": [[signature]]
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                if "result" in data and data["result"]["value"][0]:
                    status = data["result"]["value"][0]
                    if status.get("confirmationStatus") == "finalized":
                        cprint(f"✅ Transaction {signature[:8]}... confirmed", "green")
                        return True
                    elif status.get("err"):
                        cprint(f"❌ Transaction {signature[:8]}... failed: {status['err']}", "red")
                        return False
                
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                
            cprint(f"❌ Transaction {signature[:8]}... timed out after {max_retries} retries", "red")
            return False
            
        except Exception as e:
            cprint(f"❌ Transaction monitoring failed: {str(e)}", "red")
            return False
