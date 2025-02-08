from typing import Dict, Optional
import requests
import json
import os
import time
from datetime import datetime
import pandas as pd
from termcolor import cprint
import websockets
import asyncio
from dotenv import load_dotenv

class ChainStackClient:
    def __init__(self):
        load_dotenv()
        base_url = os.getenv("RPC_ENDPOINT")
        if not base_url:
            raise ValueError("RPC_ENDPOINT environment variable is required")
        self.base_url = str(base_url)
        self.ws_url = os.getenv("CHAINSTACK_WS_ENDPOINT", "").strip()
        if not self.ws_url:
            self.ws_url = self.base_url.replace("https://", "wss://")
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": os.getenv("CHAINSTACK_API_KEY", "")
        }
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 second between requests (Developer plan)
        
        # Load Chainstack configuration
        from src.config.settings import TRADING_CONFIG
        self.config = TRADING_CONFIG["chainstack"]
        self.retry_attempts = self.config["retry_attempts"]
        self.timeout = self.config["timeout"]
        self.batch_size = self.config["batch_size"]
        self.cache_duration = self.config["cache_duration"]
        
    def _rate_limit(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
        
    async def _post_rpc(self, method: str, params: list, retry_count: int = 0) -> dict:
        self._rate_limit()
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: requests.post(
                self.base_url,
                headers=self.headers,
                json={
                    "jsonrpc": "2.0",
                    "id": method,
                    "method": method,
                    "params": params
                },
                timeout=self.timeout
            ))
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if retry_count < self.retry_attempts:
                cprint(f"⚠️ RPC call failed, retrying {retry_count + 1}/{self.retry_attempts}...", "yellow")
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                return await self._post_rpc(method, params, retry_count + 1)
            cprint(f"❌ Failed RPC call to {method}: {str(e)}", "red")
            return {}
            
    async def _batch_rpc(self, requests: list) -> list:
        """Execute multiple RPC requests in a batch"""
        self._rate_limit()
        try:
            batch_requests = []
            for i in range(0, len(requests), self.batch_size):
                batch = requests[i:i + self.batch_size]
                batch_requests.append(
                    asyncio.create_task(
                        self._post_rpc(
                            method=batch[0]["method"],
                            params=batch[0]["params"]
                        )
                    )
                )
            
            responses = []
            for response in asyncio.as_completed(batch_requests):
                result = await response
                result.raise_for_status()
                responses.extend(result.json())
            return responses
        except Exception as e:
            cprint(f"❌ Batch RPC call failed: {str(e)}", "red")
            return []
            
    async def get_token_price(self, token_address: str) -> float:
        response = await self._post_rpc("getTokenLargestAccounts", [token_address])
        if "result" in response and "value" in response["result"]:
            largest_account = response["result"]["value"][0]
            return float(largest_account["amount"]) / 1e9
        return 0.0
            
    async def get_wallet_balance(self, wallet_address: str) -> float:
        try:
            if not wallet_address:
                cprint("❌ Invalid wallet address", "red")
                return 0.0
            response = await self._post_rpc("getBalance", [wallet_address])
            if "result" in response:
                balance = float(response["result"]["value"]) / 1e9
                cprint(f"✅ SOL Balance: {balance:.6f}", "green")
                return balance
            cprint("❌ Failed to get balance", "red")
            return 0.0
        except Exception as e:
            cprint(f"❌ Error getting wallet balance: {str(e)}", "red")
            return 0.0

    async def get_token_data(self, token_address: str, days_back: int = 3, timeframe: str = '1H') -> pd.DataFrame:
        response = await self._post_rpc("getTokenLargestAccounts", [token_address])
        if "result" not in response or "value" not in response["result"]:
            return pd.DataFrame()
            
        largest_account = response["result"]["value"][0]
        current_price = float(largest_account["amount"]) / 1e9
        volume = current_price * 0.1
        
        now = datetime.now()
        df = pd.DataFrame({
            'Datetime (UTC)': [now.strftime('%Y-%m-%d %H:%M:%S')],
            'Open': [current_price],
            'High': [current_price],
            'Low': [current_price],
            'Close': [current_price],
            'Volume': [volume]
        })
        
        if len(df) >= 20:
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['RSI'] = self._calculate_rsi(df['Close'])
        if len(df) >= 40:
            df['MA40'] = df['Close'].rolling(window=40).mean()
            df['Price_above_MA20'] = df['Close'] > df['MA20']
            df['Price_above_MA40'] = df['Close'] > df['MA40']
            df['MA20_above_MA40'] = df['MA20'] > df['MA40']
            
        return df
            
    def _calculate_rsi(self, prices: pd.Series, periods: int = 14) -> pd.Series:
        deltas = prices.diff()
        gain = (deltas.where(deltas.gt(0), 0)).rolling(window=periods).mean()
        loss = (-deltas.where(deltas.lt(0), 0)).rolling(window=periods).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
        
    async def get_token_metadata(self, address: str) -> dict:
        response = await self._post_rpc("getAccountInfo", [address, {"encoding": "jsonParsed"}])
        return response.get("result", {}).get("value", {})
        
    async def get_token_holders(self, address: str) -> list:
        response = await self._post_rpc("getTokenLargestAccounts", [address])
        return response.get("result", {}).get("value", [])
        
    async def get_token_supply(self, address: str) -> dict:
        response = await self._post_rpc("getTokenSupply", [address])
        return response.get("result", {}).get("value", {})
        
    async def get_signatures_for_address(self, address: str, limit: int = 1) -> list:
        response = await self._post_rpc("getSignaturesForAddress", [address, {"limit": limit}])
        return response.get("result", [])

    async def subscribe_token_updates(self, token_address: str, callback) -> None:
        while True:
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    subscribe_msg = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "accountSubscribe",
                        "params": [token_address]
                    }
                    await websocket.send(json.dumps(subscribe_msg))
                    
                    async def health_check():
                        while True:
                            try:
                                await websocket.ping()
                                await asyncio.sleep(60)
                            except Exception:
                                break
                                
                    health_task = asyncio.create_task(health_check())
                    
                    while True:
                        try:
                            msg = await websocket.recv()
                            data = json.loads(msg)
                            await callback(data)
                        except Exception as e:
                            cprint(f"❌ WebSocket error: {str(e)}", "red")
                            break
                            
                    health_task.cancel()
                    
            except Exception as e:
                cprint(f"❌ WebSocket connection error: {str(e)}", "red")
                await asyncio.sleep(5)
