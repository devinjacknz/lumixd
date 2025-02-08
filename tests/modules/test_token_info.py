"""
Tests for Token Info Module
"""

import pytest
import pandas as pd
from unittest.mock import AsyncMock, MagicMock
from src.modules.token_info import TokenInfoModule
from src.data.chainstack_client import ChainStackClient

@pytest.fixture
def mock_chainstack_client():
    client = AsyncMock(spec=ChainStackClient)
    
    # Mock token metadata response
    client.get_token_metadata.return_value = {
        "name": "Test Token",
        "symbol": "TEST",
        "decimals": 9
    }
    
    # Mock token data response
    df = pd.DataFrame({
        'Close': [1.0, 1.1, 1.2],
        'Volume': [1000, 1100, 1200]
    })
    client.get_token_data.return_value = df
    
    # Mock token supply response
    client.get_token_supply.return_value = {
        "amount": "1000000000",
        "decimals": 9,
        "uiAmount": 1000.0
    }
    
    # Mock token holders response
    client.get_token_holders.return_value = [
        {"address": "holder1", "amount": "500000000"},
        {"address": "holder2", "amount": "300000000"},
        {"address": "holder3", "amount": "200000000"}
    ]
    
    # Mock signatures response
    client.get_signatures_for_address.return_value = [
        {"signature": "sig1", "slot": 1000},
        {"signature": "sig2", "slot": 999}
    ]
    
    return client

@pytest.fixture
def token_info_module(mock_chainstack_client):
    module = TokenInfoModule()
    module.client = mock_chainstack_client
    return module

@pytest.mark.asyncio
async def test_get_token_info_by_symbol(token_info_module):
    """Test getting token info by symbol"""
    info = await token_info_module.get_token_info("SOL")
    assert info["metadata"]["symbol"] == "TEST"
    assert "market" in info
    assert "address" in info

@pytest.mark.asyncio
async def test_get_token_info_by_address(token_info_module):
    """Test getting token info by address"""
    info = await token_info_module.get_token_info("So11111111111111111111111111111111111111112")
    assert info["metadata"]["symbol"] == "TEST"
    assert "market" in info
    assert "address" in info

@pytest.mark.asyncio
async def test_get_market_data(token_info_module):
    """Test getting market data"""
    data = await token_info_module.get_market_data("So11111111111111111111111111111111111111112")
    assert "price" in data
    assert "volume_24h" in data
    assert "liquidity_score" in data
    assert "supply" in data
    assert "holders" in data

@pytest.mark.asyncio
async def test_get_token_history(token_info_module):
    """Test getting token history"""
    history = await token_info_module.get_token_history("So11111111111111111111111111111111111111112")
    assert "price_history" in history
    assert "transactions" in history
    assert len(history["transactions"]) == 2

@pytest.mark.asyncio
async def test_analyze_position(token_info_module):
    """Test position analysis"""
    analysis = await token_info_module.analyze_position("So11111111111111111111111111111111111111112", 100.0)
    assert "position_value" in analysis
    assert "position_size" in analysis
    assert "volume_ratio" in analysis
    assert "liquidity_score" in analysis
    assert "risk_level" in analysis

@pytest.mark.asyncio
async def test_error_handling(token_info_module):
    """Test error handling"""
    token_info_module.client.get_token_metadata.side_effect = Exception("Test error")
    info = await token_info_module.get_token_info("INVALID")
    assert info == {}

def test_calculate_liquidity_score(token_info_module):
    """Test liquidity score calculation"""
    holders = [
        {"amount": "500"},
        {"amount": "300"},
        {"amount": "200"}
    ]
    score = token_info_module._calculate_liquidity_score(holders)
    assert 0 <= score <= 1

def test_calculate_risk_level(token_info_module):
    """Test risk level calculation"""
    risk = token_info_module._calculate_risk_level(1000, 10000, 0.8)
    assert risk in ["LOW", "MEDIUM", "HIGH"]
