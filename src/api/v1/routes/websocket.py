"""
WebSocket Route for Real-time Trading and Market Data
"""
import json
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.data.chainstack_client import ChainStackClient
from src.modules.nlp_processor import NLPProcessor
from src.data.jupiter_client import JupiterClient

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
                        result = await manager.jupiter_client.execute_swap(
                            input_token=params["token_symbol"],
                            amount=params["amount"],
                            slippage=params.get("slippage", 1.0)
                        )
                        await websocket.send_json({
                            "type": "trade_executed",
                            "status": "success" if result else "failed",
                            "transaction_hash": result.get("signature") if result else None
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
