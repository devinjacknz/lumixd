"""
WebSocket Route for Real-time Trading and Market Data
"""
import os
import json
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.data.chainstack_client import ChainStackClient
from src.modules.nlp_processor import NLPProcessor
from src.data.jupiter_client import JupiterClient
from solders.pubkey import Pubkey

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.chainstack_client = ChainStackClient()
        self.nlp_processor = NLPProcessor()
        self.jupiter_client = JupiterClient()
        
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            
    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections.values():
            try:
                await connection.send_json(message)
            except Exception:
                continue

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, client_id: str = None):
    if not client_id:
        client_id = str(id(websocket))
    
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            try:
                data = await websocket.receive_json()
                message_type = data.get("type", "")
                
                if message_type == "subscribe":
                    channel = data.get("channel")
                    await websocket.send_json({
                        "type": "subscribed",
                        "channel": channel
                    })
                    
                    if channel == "market":
                        symbol = data.get("symbol")
                        market_data = await manager.chainstack_client.get_token_data(symbol)
                        await websocket.send_json({
                            "type": "market_data",
                            "symbol": symbol,
                            "data": market_data
                        })
                        
                elif message_type == "trade":
                    instruction = data.get("instruction", "")
                    # Parse trading instruction
                    parsed = await manager.nlp_processor.process_instruction(instruction)
                    await websocket.send_json({
                        "type": "instruction_parsed",
                        "params": parsed.get("parsed_params", {})
                    })
                    
                    # Execute trade if parsing successful
                    if "error" not in parsed:
                        params = parsed["parsed_params"]
                        # Get quote first
                        quote = await manager.jupiter_client.get_quote(
                            input_mint=params["token_address"],
                            output_mint=manager.jupiter_client.sol_token,
                            amount=str(int(params["amount"] * 1e9))  # Convert to lamports
                        )
                        
                        if quote:
                            # Execute swap with quote
                            private_key = os.getenv("SOLANA_PRIVATE_KEY")
                            if not private_key:
                                await websocket.send_json({
                                    "type": "error",
                                    "message": "Wallet private key not configured"
                                })
                                continue
                                
                            try:
                                # Create wallet pubkey from private key
                                wallet_pubkey = str(Pubkey.from_bytes(bytes.fromhex(private_key)))
                                result = await manager.jupiter_client.execute_swap(
                                    quote_response=quote,
                                    wallet_pubkey=wallet_pubkey
                                )
                                await websocket.send_json({
                                    "type": "trade_executed",
                                    "status": "success" if result else "failed",
                                    "transaction_hash": result if result else None
                                })
                            except Exception as e:
                                await websocket.send_json({
                                    "type": "error",
                                    "message": f"Failed to execute trade: {str(e)}"
                                })
                        
                elif message_type == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
        manager.disconnect(client_id)
