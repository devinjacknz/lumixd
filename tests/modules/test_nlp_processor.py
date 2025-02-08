"""
Tests for NLP Processor Module
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.modules.nlp_processor import NLPProcessor
from src.models.deepseek_model import DeepSeekModel
from src.models.base_model import ModelResponse

@pytest.fixture
def mock_deepseek_model():
    model = MagicMock(spec=DeepSeekModel)
    
    # Mock successful parsing response
    model.generate_response.side_effect = [
        ModelResponse(
            content="""
            {
                "action": "buy",
                "token_symbol": "SOL",
                "amount": "1.5",
                "slippage": "2.0",
                "urgency": "high"
            }
            """,
            raw_response={"choices": [{"message": {"content": "Analysis"}}]}
        ),
        ModelResponse(  # Second call for parameter structuring
            content="""
            {
                "action": "buy",
                "token_symbol": "SOL",
                "amount": 1.5,
                "slippage": 2.0,
                "urgency": "high"
            }
            """,
            raw_response={"choices": [{"message": {"content": "Analysis"}}]}
        )
    ]
    return model

@pytest.fixture
def nlp_processor(mock_deepseek_model):
    processor = NLPProcessor()
    processor.model = mock_deepseek_model
    return processor

@pytest.mark.asyncio
async def test_process_instruction_success(nlp_processor):
    """Test successful instruction processing"""
    result = await nlp_processor.process_instruction("Buy 1.5 SOL with 2% slippage")
    assert "parsed_params" in result
    assert "confidence" in result
    assert result["parsed_params"]["action"] == "buy"
    assert result["parsed_params"]["token_symbol"] == "SOL"
    assert result["parsed_params"]["amount"] == 1.5

@pytest.mark.asyncio
async def test_process_instruction_failure(nlp_processor):
    """Test instruction processing failure"""
    nlp_processor.model.generate_response.side_effect = Exception("Test error")
    result = await nlp_processor.process_instruction("Invalid instruction")
    assert "error" in result
    assert "original_text" in result

@pytest.mark.asyncio
async def test_validate_parameters_success(nlp_processor):
    """Test parameter validation success"""
    params = {
        "action": "buy",
        "token_symbol": "SOL",
        "amount": "1.5",
        "slippage": "2.0"
    }
    validated = await nlp_processor.validate_parameters(params)
    assert validated["action"] == "buy"
    assert "token_address" in validated
    assert validated["amount"] == 1.5
    assert validated["slippage"] == 2.0

@pytest.mark.asyncio
async def test_validate_parameters_failure(nlp_processor):
    """Test parameter validation failure"""
    params = {
        "action": "invalid",
        "token_symbol": "UNKNOWN",
        "amount": "-1"
    }
    with pytest.raises(ValueError):
        await nlp_processor.validate_parameters(params)

def test_extract_parameters_success(nlp_processor):
    """Test parameter extraction success"""
    model_response = """
    {
        "action": "buy",
        "token_symbol": "SOL",
        "amount": 1.5
    }
    """
    params = nlp_processor._extract_parameters(model_response)
    assert params["action"] == "buy"
    assert params["token_symbol"] == "SOL"
    assert params["amount"] == 1.5

def test_extract_parameters_failure(nlp_processor):
    """Test parameter extraction failure"""
    model_response = "Invalid response"
    params = nlp_processor._extract_parameters(model_response)
    assert params == {}

def test_calculate_confidence(nlp_processor):
    """Test confidence calculation"""
    high_conf = nlp_processor._calculate_confidence("I am confident this is a buy order")
    assert high_conf > 0.7
    
    med_conf = nlp_processor._calculate_confidence("This is probably a buy order")
    assert 0.4 <= med_conf <= 0.7
    
    low_conf = nlp_processor._calculate_confidence("This might be a buy order")
    assert low_conf < 0.4

def test_error_handling(nlp_processor):
    """Test error handling in confidence calculation"""
    conf = nlp_processor._calculate_confidence(None)
    assert conf == 0.5  # Default medium confidence
