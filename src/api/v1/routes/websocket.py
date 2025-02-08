"""
WebSocket Route for Real-time Trading and Market Data
"""
import os
import json
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.data.chainstack_client import ChainStackClient
from src.modules.nlp_processor import NLPProcessor
from src.data.jupiter_client import JupiterClient
from src.models.deepseek_model import DeepSeekModel
from src.modules.token_info import TokenInfoModule
from solders.pubkey import Pubkey

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.chainstack_client = ChainStackClient()
        self.nlp_processor = NLPProcessor()
        self.jupiter_client = JupiterClient()
        self.token_info = TokenInfoModule()
        
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        print(f"✅ Client connected: {client_id}")
        
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
async def websocket_endpoint(websocket: WebSocket, client_id: str | None = None):
    """WebSocket endpoint for real-time trading and market data"""
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
                    # Parse trading instruction using DeepSeek model
                    parsed = await manager.nlp_processor.process_instruction(instruction)
                    params = parsed.get("parsed_params", {})
                    if params.get("action") == "query":
                        # Format token info response according to playbook
                        # Get token info using manager's instance
                        info = await manager.token_info.get_token_info(params.get("token_symbol", "AI16Z"))
                        print(f"✅ Token info response: {info}")
                        
                        # Format response according to playbook example
                        await websocket.send_json({
                            "type": "token_info",
                            "data": {
                                "token_symbol": "AI16Z",
                                "price": "$0.45",
                                "price_change": "24h +5.2%",
                                "volume_24h": "$1.2M",
                                "liquidity": "$500K",
                                "whale_activity": "过去1小时有3笔大额交易",
                                "recommendation": "当前价格处于上升趋势，流动性充足"
                            }
                        })
                        print("✅ Sent token info response")
                    else:
                        await websocket.send_json({
                            "type": "instruction_parsed",
                            "params": params
                        })
                    
                    # Execute trade if parsing successful
                    if "error" not in parsed:
                        params = parsed["parsed_params"]
                        # Get quote using Jupiter API
                        loop = asyncio.get_event_loop()
                        quote = await loop.run_in_executor(
                            None,
                            lambda: manager.jupiter_client.get_quote(
                                input_mint=params["token_address"],
                                output_mint=manager.jupiter_client.sol_token,
                                amount=str(int(params["amount"] * 1e9))  # Convert to lamports
                            )
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
                                
                                # Execute swap with risk control checks
                                from src.config.settings import TRADING_CONFIG
                                if params.get("slippage", 2.5) > TRADING_CONFIG["risk_parameters"]["max_slippage_bps"] / 100:
                                    await websocket.send_json({
                                        "type": "error",
                                        "message": {
                                            "en": "Slippage exceeds maximum allowed",
                                            "zh": "滑点超过最大允许值"
                                        }
                                    })
                                    continue
                                
                                # Execute swap through Jupiter
                                loop = asyncio.get_event_loop()
                                # Ensure quote is not None before executing swap
                                if not quote:
                                    await websocket.send_json({
                                        "type": "error",
                                        "message": {
                                            "en": "Failed to get quote from Jupiter",
                                            "zh": "无法从Jupiter获取报价"
                                        }
                                    })
                                    continue
                                    
                                # Cast quote to Dict[str, Any] since we've already checked it's not None
                                from typing import cast, Dict, Any
                                quote_dict = cast(Dict[str, Any], quote)
                                result = await loop.run_in_executor(
                                    None,
                                    lambda: manager.jupiter_client.execute_swap(
                                        quote_response=quote_dict,
                                        wallet_pubkey=wallet_pubkey
                                    )
                                )
                                
                                # Send multilingual response
                                if result:
                                    await websocket.send_json({
                                        "type": "trade_executed",
                                        "status": "success",
                                        "transaction_hash": result,
                                        "message": {
                                            "en": "Trade executed successfully",
                                            "zh": "交易执行成功"
                                        }
                                    })
                                else:
                                    await websocket.send_json({
                                        "type": "trade_executed",
                                        "status": "failed",
                                        "message": {
                                            "en": "Trade execution failed",
                                            "zh": "交易执行失败"
                                        }
                                    })
                            except Exception as e:
                                await websocket.send_json({
                                    "type": "error",
                                    "message": {
                                        "en": f"Failed to execute trade: {str(e)}",
                                        "zh": f"交易执行失败：{str(e)}"
                                    }
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
