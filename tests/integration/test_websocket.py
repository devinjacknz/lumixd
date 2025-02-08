"""
Integration Tests for WebSocket and Trading Flow
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from src.api.v1.main import app
from src.data.chainstack_client import ChainStackClient
from src.data.jupiter_client import JupiterClient

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.mark.integration
@pytest.mark.websocket
async def test_websocket_connection():
    """Test WebSocket connection and message handling"""
    async with TestClient(app).websocket_connect("/ws") as websocket:
        data = {"type": "subscribe", "channel": "trades"}
        await websocket.send_json(data)
        response = await websocket.receive_json()
        assert response["type"] == "subscribed"
        assert response["channel"] == "trades"

@pytest.mark.integration
@pytest.mark.websocket
async def test_market_data_stream():
    """Test market data streaming through WebSocket"""
    async with TestClient(app).websocket_connect("/ws") as websocket:
        # Subscribe to market data
        await websocket.send_json({
            "type": "subscribe",
            "channel": "market",
            "symbol": "SOL/USD"
        })
        
        # Verify subscription response
        response = await websocket.receive_json()
        assert response["type"] == "subscribed"
        assert response["channel"] == "market"
        
        # Verify market data updates
        data = await websocket.receive_json()
        assert "price" in data
        assert "volume" in data
        assert "timestamp" in data

@pytest.mark.integration
@pytest.mark.trading
async def test_trading_flow():
    """Test complete trading flow from instruction to execution"""
    async with TestClient(app).websocket_connect("/ws") as websocket:
        # Send trading instruction
        instruction = {
            "type": "trade",
            "instruction": "Buy 1 SOL with 2% slippage"
        }
        await websocket.send_json(instruction)
        
        # Verify instruction parsing
        response = await websocket.receive_json()
        assert response["type"] == "instruction_parsed"
        assert "params" in response
        assert response["params"]["action"] == "buy"
        assert response["params"]["token_symbol"] == "SOL"
        
        # Verify trade execution
        execution = await websocket.receive_json()
        assert execution["type"] == "trade_executed"
        assert execution["status"] == "success"
        assert "transaction_hash" in execution

@pytest.mark.performance
async def test_websocket_stability():
    """Test WebSocket connection stability under load"""
    connections = []
    try:
        # Create multiple connections
        for _ in range(10):
            client = TestClient(app)
            ws = await client.websocket_connect("/ws")
            connections.append(ws)
            
        # Send messages on all connections
        for ws in connections:
            await ws.send_json({"type": "ping"})
            
        # Verify responses
        for ws in connections:
            response = await ws.receive_json()
            assert response["type"] == "pong"
            
    finally:
        # Clean up connections
        for ws in connections:
            await ws.close()

@pytest.mark.performance
async def test_response_times():
    """Test response times under load"""
    async with TestClient(app).websocket_connect("/ws") as websocket:
        start_time = asyncio.get_event_loop().time()
        
        # Send multiple rapid requests
        for _ in range(50):
            await websocket.send_json({"type": "ping"})
            response = await websocket.receive_json()
            assert response["type"] == "pong"
            
        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time
        
        # Average response time should be under 100ms
        avg_response_time = total_time / 50
        assert avg_response_time < 0.1  # 100ms

@pytest.mark.performance
async def test_memory_usage():
    """Test memory usage during extended operation"""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    start_memory = process.memory_info().rss
    
    async with TestClient(app).websocket_connect("/ws") as websocket:
        # Generate sustained load
        for _ in range(1000):
            await websocket.send_json({"type": "ping"})
            await websocket.receive_json()
            
        end_memory = process.memory_info().rss
        memory_increase = end_memory - start_memory
        
        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024  # 50MB in bytes
