from typing import Dict, Optional
import aiohttp
import asyncio
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
from solders.pubkey import Pubkey as PublicKey
from solders.instruction import AccountMeta, Instruction as TransactionInstruction
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
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
        self.rpc_url = os.getenv("RPC_ENDPOINT", "")  # Add default empty string
        self.sol_token = "So11111111111111111111111111111111111111112"
        if not self.rpc_url:
            raise ValueError("RPC_ENDPOINT environment variable is required")
        
    async def _rate_limit(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
        
    async def get_quote(self, input_mint: str, output_mint: str, amount: str, use_shared_accounts: bool = True, force_simpler_route: bool = True) -> Optional[Dict]:
        try:
            # For testing, return mock quotes
            if os.getenv("TESTING", "false").lower() == "true":
                return {
                    "inAmount": amount,
                    "outAmount": str(int(float(amount) * 0.95)),  # 5% slippage for testing
                    "priceImpactPct": 0.1,
                    "slippageBps": int(os.getenv("DEFAULT_SLIPPAGE_BPS", "250")),
                    "otherAmountThreshold": str(int(float(amount) * 0.93))  # 7% max slippage
                }
            
            await self._rate_limit()
            url = f"{self.base_url}/quote"
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": amount,
                "slippageBps": int(os.getenv("DEFAULT_SLIPPAGE_BPS", "250")),
                "onlyDirectRoutes": "false",
                "asLegacyTransaction": "true",
                "wrapUnwrapSOL": "true",
                "useSharedAccounts": "true" if use_shared_accounts else "false",
                "platformFeeBps": "0"
            }
            cprint(f"🔄 Getting quote with params: {json.dumps(params, indent=2)}", "cyan")
            
            retry_count = 0
            max_retries = 3
            retry_delay = 1.0
            
            while retry_count < max_retries:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params) as response:
                        if response.status >= 500:
                            response.raise_for_status()
                            
                        quote = await response.json()
                        if response.status == 200 and not quote.get("error"):
                            cprint(f"✅ Got quote: {json.dumps(quote, indent=2)}", "green")
                            return quote
                        
                        if quote.get("error"):
                            cprint(f"⚠️ API error: {quote['error']}", "yellow")
                        
                        retry_count += 1
                        if retry_count < max_retries:
                            cprint(f"⚠️ Retrying quote request (attempt {retry_count})", "yellow")
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2
                        else:
                            cprint(f"❌ Failed to get quote after {max_retries} retries", "red")
                            return None
        except Exception as e:
            cprint(f"❌ Failed to get quote: {str(e)}", "red")
            return None
            
    async def execute_swap(self, quote_response: Dict, wallet_pubkey: str, use_shared_accounts: bool = True) -> Optional[str]:
        try:
            await self._rate_limit()
            cprint(f"🔄 Requesting swap with optimized parameters", "cyan")
            
            async with aiohttp.ClientSession() as session:
                # Get swap transaction with minimal parameters
                async with session.post(
                    f"{self.base_url}/swap",
                    headers=self.headers,
                    json={
                        "quoteResponse": quote_response,
                        "userPublicKey": wallet_pubkey,
                        "wrapAndUnwrapSol": True,
                        "useSharedAccounts": True,
                        "feeAccount": wallet_pubkey,
                        "computeUnitPriceMicroLamports": 1000,
                        "asLegacyTransaction": True,
                        "useTokenLedger": True,
                        "destinationTokenAccount": None,
                        "dynamicComputeUnitLimit": True,
                        "prioritizationFeeLamports": 10000,
                        "skipUserAccountsCheck": True
                    },
                    timeout=60
                ) as response:
                    response.raise_for_status()
                    tx_data = (await response.json()).get("swapTransaction")
                    if not tx_data:
                        raise ValueError("No swap transaction returned")

            try:
                private_key = os.getenv("SOLANA_PRIVATE_KEY")
                if not private_key:
                    raise ValueError("SOLANA_PRIVATE_KEY environment variable is required")
                    
                wallet_key = Keypair.from_base58_string(private_key)
                if not wallet_key:
                    raise ValueError("Invalid wallet key")
                    
                if not tx_data:
                    raise ValueError("No transaction data received")
                    
                # Get recent blockhash and swap transaction
                async with aiohttp.ClientSession() as session:
                    # Get blockhash
                    async with session.post(
                        self.rpc_url,
                        headers=self.headers,
                        json={
                            "jsonrpc": "2.0",
                            "id": "get-blockhash",
                            "method": "getLatestBlockhash",
                            "params": [{"commitment": "finalized"}]
                        }
                    ) as response:
                        response.raise_for_status()
                        result = await response.json()
                        blockhash = result.get("result", {}).get("value", {}).get("blockhash")
                        if not blockhash:
                            raise ValueError("Failed to get blockhash")

                    # Initialize retry variables
                    retry_count = 0
                    max_retries = 3
                    retry_delay = 1
                    
                    # Get swap transaction
                    async with session.post(
                        f"{self.base_url}/v6/swap",
                        headers=self.headers,
                        json={
                            "quoteResponse": quote_response,
                            "userPublicKey": wallet_pubkey,
                            "wrapUnwrapSOL": True,
                            "asLegacyTransaction": True,
                            "onlyDirectRoutes": True,
                            "skipPreflight": True,
                            "slippageBps": 250,
                            "swapMode": "ExactIn",
                            "computeUnitPriceMicroLamports": 1000,
                            "computeUnitLimit": 1400000,
                            "useTokenLedger": False,
                            "destinationTokenAccount": None,
                            "dynamicComputeUnitLimit": False,
                            "useSharedAccounts": True,
                            "maxAccounts": 54,
                            "platformFeeBps": 0,
                            "minContextSlot": None,
                            "strictValidation": True,
                            "prioritizationFeeLamports": 10000,
                            "useVersionedTransaction": False
                        }
                    ) as response:
                        response.raise_for_status()
                        result = await response.json()
                        tx_data = result.get("swapTransaction")
                        if not tx_data:
                            raise ValueError("No swap transaction returned")
                    
                signed_tx = tx_data
                cprint("✅ Using pre-signed transaction from Jupiter", "green")
                cprint("🔄 Sending transaction to RPC...", "cyan")
                
                while retry_count < max_retries:
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.post(
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
                                            "skipPreflight": True,
                                            "preflightCommitment": "confirmed"
                                        }
                                    ]
                                },
                                timeout=60
                            ) as response:
                                response.raise_for_status()
                                result = await response.json()
                                
                                if "error" in result:
                                    cprint(f"❌ RPC error: {json.dumps(result['error'], indent=2)}", "red")
                                    return None
                                
                                signature = result.get("result")
                                if signature and await self.monitor_transaction(signature):
                                    cprint(f"✅ Transaction confirmed: {signature}", "green")
                                    cprint(f"🔍 View on Solscan: https://solscan.io/tx/{signature}", "cyan")
                                    return signature
                                return None
                    except aiohttp.ClientError as e:
                        retry_count += 1
                        if retry_count < max_retries:
                            cprint(f"⚠️ RPC request failed (attempt {retry_count}): {str(e)}", "yellow")
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2
                        else:
                            raise Exception(f"Failed to send transaction after {max_retries} retries: {str(e)}")
                    except Exception as e:
                        raise Exception(f"Failed to send transaction: {str(e)}")
            except Exception as e:
                cprint(f"❌ Failed to sign transaction: {str(e)}", "red")
                return None
            
        except Exception as e:
            cprint(f"❌ Failed to execute swap: {str(e)}", "red")
            return None
            
    async def _create_ata_transaction(self, mint: str, owner: str, ata: str) -> Optional[str]:
        try:
            async with aiohttp.ClientSession() as session:
                # Get rent exemption
                async with session.post(
                    self.rpc_url,
                    headers=self.headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": "create-ata-tx",
                        "method": "getMinimumBalanceForRentExemption",
                        "params": [165]
                    }
                ) as response:
                    response.raise_for_status()
                    rent = (await response.json()).get("result", 0)
                
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
                async with session.post(
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
                ) as response:
                    response.raise_for_status()
                    return (await response.json()).get("result")
        except Exception as e:
            cprint(f"❌ Failed to create ATA transaction: {str(e)}", "red")
            return None

    async def create_token_account(self, mint: str, owner: str) -> Optional[str]:
        try:
            wallet_key = Keypair.from_base58_string(os.getenv("SOLANA_PRIVATE_KEY"))
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.rpc_url,
                    headers=self.headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": "create-ata",
                        "method": "getAssociatedTokenAddress",
                        "params": [mint, owner]
                    }
                ) as response:
                    response.raise_for_status()
                    ata = (await response.json()).get("result")
                    if not ata:
                        return None
                    
            create_tx = await self._create_ata_transaction(mint, owner, ata)
            if not create_tx:
                return None
                
            tx = Transaction.from_bytes(bytes.fromhex(create_tx))
            tx.sign([wallet_key])
            await self._log_transaction("Create ATA", {
                "mint": mint,
                "owner": owner,
                "ata": ata,
                "transaction": base64.b64encode(bytes(tx)).decode('utf-8')
            })
            return await self._send_and_confirm_transaction(tx)
        except Exception as e:
            cprint(f"❌ Failed to create token account: {str(e)}", "red")
            return None

    async def _send_and_confirm_transaction(self, tx_data: str) -> Optional[str]:
        try:
            # Load private key
            wallet_key = Keypair.from_base58_string(os.getenv("SOLANA_PRIVATE_KEY"))
            
            # Decode base64 transaction
            tx_bytes = base64.b64decode(tx_data)
            tx = Transaction.from_bytes(tx_bytes)
            
            async with aiohttp.ClientSession() as session:
                # Get recent blockhash
                async with session.post(
                    self.rpc_url,
                    headers=self.headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": "get-blockhash",
                        "method": "getLatestBlockhash",
                        "params": [{"commitment": "finalized"}]
                    }
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    blockhash = result.get("result", {}).get("value", {}).get("blockhash")
                    if not blockhash:
                        raise ValueError("Failed to get blockhash")
                    
                # Sign transaction
                tx.sign([wallet_key], Hash.from_string(blockhash))
                signed_tx = base64.b64encode(bytes(tx)).decode('utf-8')
                
                # Send transaction
                async with session.post(
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
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    if "error" in result:
                        cprint(f"❌ RPC error: {json.dumps(result['error'], indent=2)}", "red")
                        return None
                    
                    signature = result.get("result")
                    if signature and await self.monitor_transaction(signature):
                        return signature
                    return None
        except Exception as e:
            cprint(f"❌ Failed to send transaction: {str(e)}", "red")
            return None

    async def _log_transaction(self, action: str, details: dict):
        try:
            log_file = f"logs/transactions_{datetime.now().strftime('%Y%m%d')}.log"
            with open(log_file, "a") as f:
                f.write(f"{datetime.now().isoformat()} - {action}\n")
                f.write(json.dumps(details, indent=2) + "\n\n")
        except Exception as e:
            cprint(f"❌ Failed to log transaction: {str(e)}", "red")

    async def monitor_transaction(self, signature: str, max_retries: int = 10) -> bool:
        try:
            retry_count = 0
            delay = 1.0
            
            async with aiohttp.ClientSession() as session:
                while retry_count < max_retries:
                    await self._rate_limit()
                    async with session.post(
                        self.rpc_url,
                        headers=self.headers,
                        json={
                            "jsonrpc": "2.0",
                            "id": "get-tx-status",
                            "method": "getSignatureStatuses",
                            "params": [[signature], {"searchTransactionHistory": True}]
                        }
                    ) as response:
                        response.raise_for_status()
                        data = await response.json()
                        
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
                            await asyncio.sleep(delay)
                            delay *= 1.5
                        
            cprint(f"❌ Transaction {signature[:8]}... timed out after {max_retries} retries", "red")
            return False
            
        except Exception as e:
            cprint(f"❌ Transaction monitoring failed: {str(e)}", "red")
            return False
