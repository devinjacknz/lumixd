import asyncio
import pytest
from decimal import Decimal
from unittest.mock import patch, AsyncMock, MagicMock
from src.data.raydium_client import RaydiumClient

# Mock responses
MOCK_RESPONSES = {
    'pool_info': {
        "success": True,
        "data": {
            "pool_id_1": {
                "id": "pool_id_1",
                "baseMint": "base_token_address",
                "quoteMint": "quote_token_address",
                "lpMint": "lp_token_address",
                "baseDecimals": 9,
                "quoteDecimals": 6,
                "lpDecimals": 9,
                "version": 3,
                "programId": "program_address",
                "authority": "authority_address",
                "baseVault": "base_vault_address",
                "quoteVault": "quote_vault_address",
                "lpVault": "lp_vault_address"
            }
        }
    },
    'token_price': {
        "success": True,
        "data": {
            "price": "1.234567",
            "mint": "token_mint_address"
        }
    }
}

async def test_get_pool_info():
    """Test pool information retrieval"""
    async with RaydiumClient() as client:
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(
                return_value=MOCK_RESPONSES['pool_info']
            )
            mock_get.return_value.__aenter__.return_value.raise_for_status = AsyncMock()
            
            result = await client.get_pool_info(["pool_id_1"])
            assert result == MOCK_RESPONSES['pool_info']["data"]
            
async def test_get_token_price():
    """Test token price retrieval"""
    async with RaydiumClient() as client:
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(
                return_value=MOCK_RESPONSES['token_price']
            )
            mock_get.return_value.__aenter__.return_value.raise_for_status = AsyncMock()
            
            result = await client.get_token_price("token_mint_address")
            assert result == Decimal("1.234567")
            
async def test_error_handling():
    """Test error handling for failed requests"""
    error_response = {
        "success": False,
        "msg": "API error message"
    }
    
    async with RaydiumClient(retry_attempts=1) as client:
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(
                return_value=error_response
            )
            mock_get.return_value.__aenter__.return_value.raise_for_status = AsyncMock()
            
            with pytest.raises(Exception) as exc_info:
                await client.get_pool_info(["pool_id_1"])
            assert "API error message" in str(exc_info.value)
            
async def test_retry_mechanism():
    """Test retry mechanism for failed requests"""
    success_response = MOCK_RESPONSES['pool_info']
    error_response = {
        "success": False,
        "msg": "Temporary error"
    }
    
    responses = [error_response, error_response, success_response]
    response_index = 0
    
    async def mock_json():
        nonlocal response_index
        response = responses[response_index]
        response_index = min(response_index + 1, len(responses) - 1)
        return response
    
    async with RaydiumClient(retry_attempts=3, retry_delay=0.1) as client:
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value.json = mock_json
            mock_get.return_value.__aenter__.return_value.raise_for_status = AsyncMock()
            
            result = await client.get_pool_info(["pool_id_1"])
            assert result == success_response["data"]
            assert response_index == 2  # Should have retried twice before succeeding

if __name__ == "__main__":
    pytest.main(["-v", __file__])
