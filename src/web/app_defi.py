"""
Solana DeFi Agent Web Application with WebSocket Support
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import redis.asyncio as redis
from src.data.chainstack_client import ChainStackClient
from src.services.logging_service import logging_service

# Bilingual error messages
ERROR_MESSAGES = {
    'server_error': {
        'en': 'Internal server error',
        'zh': '服务器内部错误'
    },
    'websocket_error': {
        'en': 'WebSocket connection error',
        'zh': 'WebSocket连接错误'
    },
    'redis_error': {
        'en': 'Redis connection error',
        'zh': 'Redis连接错误'
    }
}

app = FastAPI()
chainstack_client = ChainStackClient()

# Setup Redis for real-time updates
redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))

# Setup templates
templates = Jinja2Templates(directory="src/web/templates")
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/", response_class=HTMLResponse)
async def index(request):
    """Serve the main DeFi agent interface"""
    return templates.TemplateResponse(
        "defi_agent.html",
        {"request": request}
    )

@app.websocket("/ws/price_updates")
async def price_updates(websocket: WebSocket):
    """Handle real-time price updates via WebSocket"""
    await websocket.accept()
    
    try:
        while True:
            # Get token address from client
            token_address = await websocket.receive_text()
            
            try:
                # Get token data from Chainstack
                price_data = await chainstack_client.get_token_data(token_address)
                
                # Cache price data in Redis
                await redis_client.setex(
                    f"price:{token_address}",
                    300,  # 5 minutes TTL
                    json.dumps(price_data)
                )
                
                # Send price update to client
                await websocket.send_json({
                    "type": "price_update",
                    "data": price_data
                })
                
                # Log successful update
                await logging_service.log_user_action(
                    'price_update',
                    {
                        'token_address': token_address,
                        'price': price_data.get('price'),
                        'timestamp': price_data.get('timestamp')
                    },
                    'system'
                )
                
            except Exception as e:
                error_msg = ERROR_MESSAGES['server_error']
                await logging_service.log_error(
                    f"{error_msg['zh']} | {error_msg['en']}",
                    {
                        'error': str(e),
                        'token_address': token_address
                    },
                    'system'
                )
                
                # Send error to client
                await websocket.send_json({
                    "type": "error",
                    "message": f"{error_msg['zh']} | {error_msg['en']}"
                })
                
    except WebSocketDisconnect:
        await logging_service.log_user_action(
            'websocket_disconnect',
            {'message': 'WebSocket disconnected normally'},
            'system'
        )
        
    except Exception as e:
        error_msg = ERROR_MESSAGES['websocket_error']
        await logging_service.log_error(
            f"{error_msg['zh']} | {error_msg['en']}",
            {'error': str(e)},
            'system'
        )

@app.on_event("startup")
async def startup_event():
    """Initialize Redis connection on startup"""
    try:
        await redis_client.ping()
    except Exception as e:
        error_msg = ERROR_MESSAGES['redis_error']
        await logging_service.log_error(
            f"{error_msg['zh']} | {error_msg['en']}",
            {'error': str(e)},
            'system'
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)
