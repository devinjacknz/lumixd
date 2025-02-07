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
        self.ws_url = self.base_url.replace("https://", "wss://")
        self.headers = {"Content-Type": "application/json"}
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 second between requests (Developer plan)
        
    def _rate_limit(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
        
    def _post_rpc(self, method: str, params: list) -> dict:
        self._rate_limit()
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={
                    "jsonrpc": "2.0",
                    "id": method,
                    "method": method,
                    "params": params
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            cprint(f"✨ Failed RPC call to {method}: {str(e)}", "red")
            return {}
            
    def get_token_price(self, token_address: str) -> float:
        response = self._post_rpc("getTokenLargestAccounts", [token_address])
        if "result" in response and "value" in response["result"]:
            largest_account = response["result"]["value"][0]
            return float(largest_account["amount"]) / 1e9
        return 0.0
            
    def get_wallet_balance(self, wallet_address: str) -> float:
        response = self._post_rpc("getBalance", [wallet_address])
        if "result" in response and "value" in response["result"]:
            return float(response["result"]["value"]) / 1e9
        return 0.0

    def get_token_data(self, token_address: str, days_back: int = 3, timeframe: str = '1H') -> pd.DataFrame:
        response = self._post_rpc("getTokenLargestAccounts", [token_address])
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
        
    def get_token_metadata(self, address: str) -> dict:
        response = self._post_rpc("getAccountInfo", [address, {"encoding": "jsonParsed"}])
        return response.get("result", {}).get("value", {})
        
    def get_token_holders(self, address: str) -> list:
        response = self._post_rpc("getTokenLargestAccounts", [address])
        return response.get("result", {}).get("value", [])
        
    def get_token_supply(self, address: str) -> dict:
        response = self._post_rpc("getTokenSupply", [address])
        return response.get("result", {}).get("value", {})
        
    def get_signatures_for_address(self, address: str, limit: int = 1) -> list:
        response = self._post_rpc("getSignaturesForAddress", [address, {"limit": limit}])
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
