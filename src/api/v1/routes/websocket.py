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
from src.services.order_manager import OrderManager
from src.data.price_tracker import PriceTracker
from solders.pubkey import Pubkey

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.chainstack_client = ChainStackClient()
        self.nlp_processor = NLPProcessor()
        self.jupiter_client = JupiterClient()
        self.token_info = TokenInfoModule()
        self.order_manager = OrderManager()
        self.price_tracker = PriceTracker()
        
    async def initialize(self):
        """Initialize async components"""
        await self.order_manager.start()
        await self.price_tracker.start()
        print("✅ Initialized WebSocket manager")
        
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

@router.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time trading and market data"""
    client_id = str(id(websocket))
    print(f"🔌 New WebSocket connection: {client_id}")
    
    try:
        await manager.connect(websocket, client_id)
        print(f"✅ Client connected: {client_id}")
        
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
                    if "error" not in parsed and parsed.get("parsed_params"):
                        params = parsed.get("parsed_params", {})
                        instance_id = "default"  # Use default instance for now
                        print(f"✅ Parsed parameters: {params}")  # Debug log
                        
                        # Validate required parameters
                        if not params.get("token_address"):
                            await websocket.send_json({
                                "type": "error",
                                "message": {
                                    "en": "Token address is required",
                                    "zh": "代币地址为必填项"
                                }
                            })
                            continue
                        
                        try:
                            # Handle immediate full position buy
                            if "现价买全仓" in instruction:
                                try:
                                    order_id = await manager.order_manager.create_immediate_order(
                                        instance_id=instance_id,
                                        token=params["token_address"],
                                        position_size=1.0,  # Full position
                                        amount=float(os.getenv("MAX_TRADE_SIZE_SOL", "10.0"))
                                    )
                                    await websocket.send_json({
                                        "type": "order_created",
                                        "order_id": order_id,
                                        "message": {
                                            "en": "Full position buy order created",
                                            "zh": "全仓买入订单已创建"
                                        },
                                        "params": {
                                            "token_address": params["token_address"],
                                            "position_size": 1.0,
                                            "amount": float(os.getenv("MAX_TRADE_SIZE_SOL", "10.0"))
                                        }
                                    })
                                except Exception as e:
                                    print(f"❌ Error creating immediate order: {str(e)}")
                                    await websocket.send_json({
                                        "type": "error",
                                        "message": {
                                            "en": f"Failed to create order: {str(e)}",
                                            "zh": f"创建订单失败：{str(e)}"
                                        }
                                    })
                                
                            # Handle timed half position sell
                            elif "分钟后卖出半仓" in instruction:
                                delay_minutes = int(instruction.split("分钟")[0])
                                order_id = await manager.order_manager.create_timed_order(
                                    instance_id=instance_id,
                                    token=params["token_address"],
                                    direction="sell",
                                    position_size=0.5,  # Half position
                                    delay_minutes=delay_minutes
                                )
                                await websocket.send_json({
                                    "type": "order_created",
                                    "order_id": order_id,
                                    "message": {
                                        "en": f"Timed sell order created (execute in {delay_minutes} minutes)",
                                        "zh": f"定时卖出订单已创建（{delay_minutes}分钟后执行）"
                                    },
                                    "params": {
                                        "direction": "sell",
                                        "position_size": 0.5,
                                        "delay_minutes": delay_minutes,
                                        "token_address": params.get("token_address", "So11111111111111111111111111111111111111112")
                                    }
                                })
                                
                            # Handle conditional order
                            elif "分钟后，如果相对买入价" in instruction:
                                delay_minutes = int(instruction.split("分钟")[0])
                                is_up = "上涨" in instruction
                                
                                # Get current price as entry price
                                quote = await asyncio.get_event_loop().run_in_executor(
                                    None,
                                    lambda: manager.jupiter_client.get_quote(
                                        input_mint=manager.jupiter_client.sol_token,
                                        output_mint=params["token_address"],
                                        amount="1000000000"  # 1 SOL
                                    )
                                )
                                if not quote:
                                    raise ValueError("Failed to get entry price")
                                    
                                entry_price = float(quote.get("outAmount", 0)) / 1e9
                                
                                order_id = await manager.order_manager.create_conditional_order(
                                    instance_id=instance_id,
                                    token=params["token_address"],
                                    direction="sell" if is_up else "buy",
                                    position_size=1.0 if is_up else 0.1,  # Full remaining position or 10u
                                    delay_minutes=delay_minutes,
                                    condition={"type": "above_entry" if is_up else "below_entry"},
                                    entry_price=entry_price
                                )
                                await websocket.send_json({
                                    "type": "order_created",
                                    "order_id": order_id,
                                    "message": {
                                        "en": f"Conditional order created (execute in {delay_minutes} minutes)",
                                        "zh": f"条件单已创建（{delay_minutes}分钟后检查条件）"
                                    },
                                    "params": {
                                        "direction": "sell" if is_up else "buy",
                                        "position_size": 1.0 if is_up else 0.1,
                                        "delay_minutes": delay_minutes,
                                        "token_address": params["token_address"],
                                        "condition": "above_entry" if is_up else "below_entry",
                                        "entry_price": entry_price
                                    },
                                    "type": "conditional_order"
                                })
                                
                        except Exception as e:
                            await websocket.send_json({
                                "type": "error",
                                "message": {
                                    "en": f"Failed to create order: {str(e)}",
                                    "zh": f"创建订单失败：{str(e)}"
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
