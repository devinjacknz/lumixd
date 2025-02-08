from fastapi import WebSocket, APIRouter
from typing import List
import asyncio
from termcolor import cprint

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        cprint(f"✨ New WebSocket connection established. Total connections: {len(self.active_connections)}", "green")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        cprint(f"🔌 WebSocket connection closed. Remaining connections: {len(self.active_connections)}", "yellow")

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                cprint(f"❌ Failed to send message to connection: {str(e)}", "red")
                disconnected.append(connection)
        
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(data)
    except Exception as e:
        cprint(f"❌ WebSocket error: {str(e)}", "red")
        manager.disconnect(websocket)
