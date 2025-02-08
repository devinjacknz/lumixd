"""
Price Tracker for Real-time Token Price Updates
"""
import os
import json
import asyncio
from typing import Dict, Optional
from termcolor import cprint
import websockets
from src.data.jupiter_client import JupiterClient

class WebSocketClient:
    def __init__(self):
        self.ws_endpoint = os.getenv("CHAINSTACK_WS_ENDPOINT")
        self.subscriptions = set()
        self.ws = None
        self.reconnect_delay = int(os.getenv("WEBSOCKET_RECONNECT_DELAY", "5000"))
        
    async def connect(self) -> bool:
        """Connect to WebSocket endpoint"""
        if not self.ws_endpoint:
            cprint("❌ WebSocket endpoint not configured", "red")
            return False
            
        try:
            self.ws = await websockets.connect(
                self.ws_endpoint,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=20
            )
            cprint("✅ WebSocket connected", "green")
            return True
        except Exception as e:
            cprint(f"❌ WebSocket connection failed: {str(e)}", "red")
            await asyncio.sleep(self.reconnect_delay / 1000)  # Convert to seconds
            return False
            
    async def subscribe(self, token: str):
        """Subscribe to token price updates"""
        retry_count = 0
        max_retries = 3
        retry_delay = 1.0
        
        while retry_count < max_retries:
            try:
                if not self.ws:
                    if not await self.connect():
                        retry_count += 1
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                        
                message = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "accountSubscribe",
                    "params": [
                        token,
                        {"encoding": "jsonParsed", "commitment": "confirmed"}
                    ]
                }
                
                if self.ws:  # Double-check ws is still connected
                    await self.ws.send(json.dumps(message))
                    self.subscriptions.add(token)
                    return True
                    
            except Exception as e:
                cprint(f"❌ Subscription failed for {token} (attempt {retry_count + 1}): {str(e)}", "red")
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    # Try to reconnect
                    await self.connect()
                    
        return False
            
    async def receive(self):
        """Receive WebSocket messages"""
        while True:
            try:
                if not self.ws:
                    if not await self.connect():
                        await asyncio.sleep(self.reconnect_delay / 1000)
                        continue
                
                try:
                    message = await self.ws.recv()
                    yield json.loads(message)
                except websockets.exceptions.ConnectionClosed:
                    cprint("❌ WebSocket connection closed", "red")
                    self.ws = None
                    continue
            except Exception as e:
                cprint(f"❌ WebSocket receive error: {str(e)}", "red")
                if self.ws:
                    try:
                        await self.ws.close()
                    except:
                        pass
                self.ws = None
                await asyncio.sleep(1)
            
    async def close(self):
        """Close WebSocket connection"""
        if self.ws:
            await self.ws.close()
            self.ws = None

class PriceTracker:
    def __init__(self):
        """Initialize price tracker with WebSocket client"""
        self.prices: Dict[str, float] = {}
        self.ws_client = WebSocketClient()
        self.jupiter_client = JupiterClient()
        self._stop = False
        self._price_update_task = None
        
    async def start(self):
        """Start price tracking"""
        self._stop = False
        self._price_update_task = asyncio.create_task(self._update_prices())
        
    async def stop(self):
        """Stop price tracking"""
        self._stop = True
        if self._price_update_task:
            self._price_update_task.cancel()
            await self.ws_client.close()
            
    async def track_token(self, token: str):
        """Start tracking token price"""
        await self.ws_client.subscribe(token)
        # Get initial price
        initial_price = await self._get_token_price(token)
        if initial_price:
            self.prices[token] = initial_price
            
    async def get_price_change(self, token: str, entry_price: float) -> float:
        """Get price change percentage from entry"""
        current = self.prices.get(token, 0)
        if not current or not entry_price:
            return 0
        return (current - entry_price) / entry_price * 100
        
    async def _update_prices(self):
        """Update prices from WebSocket feed"""
        retry_count = 0
        max_retries = 3
        retry_delay = 1.0
        
        while not self._stop and retry_count < max_retries:
            try:
                async for message in self.ws_client.receive():
                    if self._stop:
                        break
                        
                    if "params" in message:
                        token = message["params"]["subscription"]
                        data = message["params"]["result"]
                        if "value" in data:
                            # Update price in cache with retry
                            for attempt in range(3):
                                price = await self._get_token_price(token)
                                if price:
                                    self.prices[token] = price
                                    # Reset retry count on successful update
                                    retry_count = 0
                                    break
                                await asyncio.sleep(0.5)
                                
            except Exception as e:
                retry_count += 1
                cprint(f"❌ Price update error (attempt {retry_count}): {str(e)}", "red")
                if retry_count < max_retries:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    # Attempt to reconnect
                    await self.ws_client.connect()
                else:
                    cprint("❌ Max retries reached, stopping price updates", "red")
                    break
            
    async def _get_token_price(self, token: str) -> Optional[float]:
        """Get token price from Jupiter"""
        try:
            quote = self.jupiter_client.get_quote(
                input_mint=token,
                output_mint=self.jupiter_client.sol_token,
                amount="1000000000"  # 1 unit in smallest denomination
            )
            if not quote:
                return None
            return float(quote.get('outAmount', 0)) / 1e9
        except Exception as e:
            cprint(f"❌ Error getting token price: {str(e)}", "red")
            return None
