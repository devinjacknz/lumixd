"""
Tests for Market Analysis Service
"""

import pytest
import pandas as pd
from unittest.mock import AsyncMock, MagicMock, patch
from src.agents.market_analysis import MarketAnalysisService
from src.data.chainstack_client import ChainStackClient
from src.models.deepseek_model import DeepSeekModel
from src.models.base_model import ModelResponse

@pytest.fixture
def mock_chainstack_client():
    client = AsyncMock(spec=ChainStackClient)
    
    # Mock token data response
    df = pd.DataFrame({
        'Close': [1.0, 1.1, 1.2, 1.3, 1.4],
        'High': [1.1, 1.2, 1.3, 1.4, 1.5],
        'Low': [0.9, 1.0, 1.1, 1.2, 1.3],
        'Volume': [1000, 1100, 1200, 1300, 1400]
    })
    client.get_token_data.return_value = df
    
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
def mock_deepseek_model():
    model = AsyncMock(spec=DeepSeekModel)
    model.generate_response.return_value = ModelResponse(
        content="Bullish trend with strong momentum. High confidence in continued upward movement.",
        raw_response={"choices": [{"message": {"content": "Analysis"}}]}
    )
    return model

@pytest.fixture
def market_analysis_service(mock_chainstack_client, mock_deepseek_model):
    service = MarketAnalysisService()
    service.chain_client = mock_chainstack_client
    service.model = mock_deepseek_model
    return service

@pytest.mark.asyncio
async def test_analyze_price_trend(market_analysis_service):
    """Test price trend analysis"""
    result = await market_analysis_service.analyze_price_trend("test_token")
    assert "current_price" in result
    assert "price_change_24h" in result
    assert "ma20" in result
    assert "ma40" in result
    assert "rsi" in result
    assert "trend" in result
    assert "indicators" in result
    assert isinstance(result["indicators"], dict)

@pytest.mark.asyncio
async def test_analyze_liquidity(market_analysis_service):
    """Test liquidity analysis"""
    result = await market_analysis_service.analyze_liquidity("test_token")
    assert "liquidity_metrics" in result
    assert "risk_assessment" in result
    assert "total_supply" in result["liquidity_metrics"]
    assert "holder_count" in result["liquidity_metrics"]
    assert "top_holders_share" in result["liquidity_metrics"]
    assert "daily_volume" in result["liquidity_metrics"]
    assert "tx_count_24h" in result["liquidity_metrics"]

@pytest.mark.asyncio
async def test_analyze_trend_with_ai(market_analysis_service):
    """Test AI trend analysis"""
    df = pd.DataFrame({
        'Close': [1.0, 1.1, 1.2],
        'High': [1.1, 1.2, 1.3],
        'Low': [0.9, 1.0, 1.1],
        'Volume': [1000, 1100, 1200],
        'MA20': [1.0, 1.1, 1.2],
        'MA40': [0.9, 1.0, 1.1],
        'RSI': [45, 55, 65]
    })
    result = await market_analysis_service._analyze_trend_with_ai(df)
    assert "ai_analysis" in result
    assert "confidence" in result
    assert result["confidence"] in ["high", "medium", "low"]

def test_assess_concentration_risk(market_analysis_service):
    """Test concentration risk assessment"""
    assert market_analysis_service._assess_concentration_risk(0.8) == "HIGH"
    assert market_analysis_service._assess_concentration_risk(0.6) == "MEDIUM"
    assert market_analysis_service._assess_concentration_risk(0.4) == "LOW"

def test_assess_volume_adequacy(market_analysis_service):
    """Test volume adequacy assessment"""
    assert market_analysis_service._assess_volume_adequacy(100) == "LOW"
    assert market_analysis_service._assess_volume_adequacy(5000) == "MEDIUM"
    assert market_analysis_service._assess_volume_adequacy(10000) == "HIGH"

def test_assess_holder_distribution(market_analysis_service):
    """Test holder distribution assessment"""
    holders = [{"amount": "100"}] * 50
    assert market_analysis_service._assess_holder_distribution(holders) == "HIGH"
    holders = [{"amount": "100"}] * 500
    assert market_analysis_service._assess_holder_distribution(holders) == "MEDIUM"
    holders = [{"amount": "100"}] * 2000
    assert market_analysis_service._assess_holder_distribution(holders) == "LOW"

@pytest.mark.asyncio
async def test_error_handling(market_analysis_service):
    """Test error handling"""
    market_analysis_service.chain_client.get_token_data.side_effect = Exception("Test error")
    result = await market_analysis_service.analyze_price_trend("test_token")
    assert "error" in result
    
    market_analysis_service.chain_client.get_token_holders.side_effect = Exception("Test error")
    result = await market_analysis_service.analyze_liquidity("test_token")
    assert "error" in result
