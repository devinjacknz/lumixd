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
from solders.hash import Hash
from solders.message import Message
from dotenv import load_dotenv

os.makedirs("logs", exist_ok=True)
load_dotenv()

class JupiterClient:
    def __init__(self):
        self.base_url = "https://quote-api.jup.ag/v6"
        self.headers = {"Content-Type": "application/json"}
        self.slippage_bps = 250
        self.max_retries = 3
        self.retry_delay = 1000
        self.last_request_time = 0
        self.min_request_interval = 1.0
        self.rpc_url = os.getenv("RPC_ENDPOINT")
        self.sol_token = "So11111111111111111111111111111111111111112"
        if not self.rpc_url:
            raise ValueError("RPC_ENDPOINT environment variable is required")
        
    def _rate_limit(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
        
    def get_quote(self, input_mint: str, output_mint: str, amount: str, use_shared_accounts: bool = True, force_simpler_route: bool = True) -> Optional[Dict]:
        try:
            self._rate_limit()
            url = f"{self.base_url}/quote"
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": amount,
                "slippageBps": 250,
                "platformFeeBps": 0
            }
            cprint(f"🔄 Getting quote with params: {json.dumps(params, indent=2)}", "cyan")
            response = requests.get(url, params=params)
            response.raise_for_status()
            quote = response.json()
            cprint(f"✅ Got quote: {json.dumps(quote, indent=2)}", "green")
            return quote
        except Exception as e:
            cprint(f"❌ Failed to get quote: {str(e)}", "red")
            return None
            
    def execute_swap(self, quote_response: Dict, wallet_pubkey: str, use_shared_accounts: bool = True) -> Optional[str]:
        try:
            self._rate_limit()
            cprint(f"🔄 Requesting swap with optimized parameters", "cyan")
            response = requests.post(
                f"{self.base_url}/swap",
                headers=self.headers,
                json={
                    "quoteResponse": quote_response,
                    "userPublicKey": wallet_pubkey,
                    "wrapUnwrapSOL": True
                }
            )
            response.raise_for_status()
            tx_data = response.json().get("swapTransaction")
            if not tx_data:
                raise ValueError("No swap transaction returned")

            # Sign transaction
            wallet_key = Keypair.from_base58_string(os.getenv("SOLANA_PRIVATE_KEY"))
            tx_bytes = base64.b64decode(tx_data)
            tx = Transaction.from_bytes(tx_bytes)
            
            # Get recent blockhash
            response = requests.post(
                self.rpc_url,
                headers=self.headers,
                json={
                    "jsonrpc": "2.0",
                    "id": "get-blockhash",
                    "method": "getLatestBlockhash",
                    "params": [{"commitment": "finalized"}]
                }
            )
            response.raise_for_status()
            blockhash = response.json().get("result", {}).get("value", {}).get("blockhash")
            if not blockhash:
                raise ValueError("Failed to get blockhash")
            
            # Sign with blockhash
            tx.sign([wallet_key], Hash.from_string(blockhash))
            signed_tx = base64.b64encode(bytes(tx)).decode('utf-8')
            
            # Send transaction
            response = requests.post(
                self.rpc_url,
                headers=self.headers,
                json={
                    "jsonrpc": "2.0",
                    "id": "send-tx",
                    "method": "sendTransaction",
                    "params": [
                        signed_tx,
                        {
                            "encoding": "base64",
                            "maxRetries": 3,
                            "skipPreflight": True,
                            "preflightCommitment": "finalized",
                            "minContextSlot": quote_response.get("contextSlot")
                        }
                    ]
                }
            )
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                cprint(f"❌ RPC error: {json.dumps(result['error'], indent=2)}", "red")
                return None
                
            signature = result.get("result")
            if signature and self.monitor_transaction(signature):
                cprint(f"✅ Transaction confirmed: {signature}", "green")
                cprint(f"🔍 View on Solscan: https://solscan.io/tx/{signature}", "cyan")
                return signature
            return None

            
        except Exception as e:
            cprint(f"❌ Failed to execute swap: {str(e)}", "red")
            return None
            
    def _create_ata_transaction(self, mint: str, owner: str, ata: str) -> Optional[str]:
        try:
            response = requests.post(
                self.rpc_url,
                headers=self.headers,
                json={
                    "jsonrpc": "2.0",
                    "id": "create-ata-tx",
                    "method": "getMinimumBalanceForRentExemption",
                    "params": [165]
                }
            )
            rent = response.json().get("result", 0)
            
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
                
            create_tx = self._create_ata_transaction(mint, owner, ata)
            if not create_tx:
                return None
                
            tx = Transaction.from_bytes(bytes.fromhex(create_tx))
            tx.sign([wallet_key])
            self._log_transaction("Create ATA", {
                "mint": mint,
                "owner": owner,
                "ata": ata,
                "transaction": base64.b64encode(bytes(tx)).decode('utf-8')
            })
            return self._send_and_confirm_transaction(tx)
        except Exception as e:
            cprint(f"❌ Failed to create token account: {str(e)}", "red")
            return None

    def _send_and_confirm_transaction(self, tx_data: str) -> Optional[str]:
        try:
            # Load private key
            wallet_key = Keypair.from_base58_string(os.getenv("SOLANA_PRIVATE_KEY"))
            
            # Decode base64 transaction
            tx_bytes = base64.b64decode(tx_data)
            tx = Transaction.from_bytes(tx_bytes)
            
            # Get recent blockhash
            response = requests.post(
                self.rpc_url,
                headers=self.headers,
                json={
                    "jsonrpc": "2.0",
                    "id": "get-blockhash",
                    "method": "getLatestBlockhash",
                    "params": [{"commitment": "finalized"}]
                }
            )
            response.raise_for_status()
            blockhash = response.json().get("result", {}).get("value", {}).get("blockhash")
            if not blockhash:
                raise ValueError("Failed to get blockhash")
                
            # Sign transaction
            tx.sign([wallet_key], Hash.from_string(blockhash))
            signed_tx = base64.b64encode(bytes(tx)).decode('utf-8')
            
            # Send transaction
            response = requests.post(
                self.rpc_url,
                headers=self.headers,
                json={
                    "jsonrpc": "2.0",
                    "id": "send-tx",
                    "method": "sendTransaction",
                    "params": [
                        signed_tx,
                        {
                            "encoding": "base64",
                            "maxRetries": 3,
                            "skipPreflight": True,
                            "preflightCommitment": "finalized"
                        }
                    ]
                }
            )
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                cprint(f"❌ RPC error: {json.dumps(result['error'], indent=2)}", "red")
                return None
                
            signature = result.get("result")
            if signature and self.monitor_transaction(signature):
                return signature
            return None
        except Exception as e:
            cprint(f"❌ Failed to send transaction: {str(e)}", "red")
            return None

    def _log_transaction(self, action: str, details: dict):
        try:
            log_file = f"logs/transactions_{datetime.now().strftime('%Y%m%d')}.log"
            with open(log_file, "a") as f:
                f.write(f"{datetime.now().isoformat()} - {action}\n")
                f.write(json.dumps(details, indent=2) + "\n\n")
        except Exception as e:
            cprint(f"❌ Failed to log transaction: {str(e)}", "red")

    def monitor_transaction(self, signature: str, max_retries: int = 10) -> bool:
        try:
            retry_count = 0
            delay = 1.0
            
            while retry_count < max_retries:
                self._rate_limit()
                response = requests.post(
                    self.rpc_url,
                    headers=self.headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": "get-tx-status",
                        "method": "getSignatureStatuses",
                        "params": [[signature], {"searchTransactionHistory": True}]
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
                    delay *= 1.5
                
            cprint(f"❌ Transaction {signature[:8]}... timed out after {max_retries} retries", "red")
            return False
            
        except Exception as e:
            cprint(f"❌ Transaction monitoring failed: {str(e)}", "red")
            return False
