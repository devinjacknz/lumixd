import pytest
from fastapi.testclient import TestClient
from src.web.app_defi import app

client = TestClient(app)

def test_websocket_connection():
    with client.websocket_connect("/ws/price_updates") as websocket:
        # Test SOL token updates
        websocket.send_text("So11111111111111111111111111111111111111112")
        data = websocket.receive_json()
        assert data["type"] == "price_update"
        assert "price" in data["data"]
        assert "volume" in data["data"]
        assert "market_data" in data["data"]

def test_websocket_error_handling():
    with client.websocket_connect("/ws/price_updates") as websocket:
        # Test invalid token address
        websocket.send_text("invalid_address")
        data = websocket.receive_json()
        assert data["type"] == "error"
        assert "message" in data
