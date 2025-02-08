import asyncio
import os
import json
import time
from unittest.mock import patch, AsyncMock, MagicMock
from dotenv import load_dotenv
from src.data.jupiter_client import JupiterClient

# Load environment variables
load_dotenv()

# Mock responses
MOCK_RESPONSES = {
    'quote': {
        "inputMint": "So11111111111111111111111111111111111111112",
        "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "inAmount": "1000000000",
        "outAmount": "20000000",
        "otherAmountThreshold": "19800000",
        "swapMode": "ExactIn",
        "slippageBps": 200,
        "platformFee": None,
        "priceImpactPct": 0.1
    },
    'swap': {
        "swapTransaction": "base64_encoded_transaction",
        "lastValidBlockHeight": 123456789
    }
}

async def test_jupiter_v6_trading():
    """Test Jupiter v6 API trading functionality"""
    # Create client with mocked dependencies
    client = JupiterClient()
    
    # Set up mock responses for get_quote
    # Set up mock responses
    error_response = AsyncMock()
    error_response.status = 429
    error_response.json = AsyncMock(return_value={"error": "Too many requests"})
    error_response.raise_for_status = AsyncMock()
    
    success_response = AsyncMock()
    success_response.status = 200
    success_response.json = AsyncMock(return_value=MOCK_RESPONSES['quote'])
    success_response.raise_for_status = AsyncMock()
    
    # Create mock session class
    class MockClientSession:
        async def __aenter__(self):
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None
            
        async def get(self, *args, **kwargs):
            class MockResponse:
                async def __aenter__(self):
                    if not hasattr(self, '_call_count'):
                        self._call_count = 0
                    self._call_count += 1
                    if self._call_count <= 2:
                        return error_response
                    return success_response
                    
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    return None
                    
            return MockResponse()
            
        async def post(self, *args, **kwargs):
            class MockResponse:
                async def __aenter__(self):
                    if not hasattr(self, '_call_count'):
                        self._call_count = 0
                    self._call_count += 1
                    if self._call_count == 1:
                        return swap_error_response
                    return swap_success_response
                    
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    return None
                    
            return MockResponse()
            
    # Patch ClientSession with our mock
    mock_session = MockClientSession()
    
    # Test get_quote with retry mechanism
    with patch('aiohttp.ClientSession', return_value=mock_session), \
         patch('asyncio.sleep', new=AsyncMock()) as mock_sleep:  # Mock sleep to avoid actual delays
        quote = await client.get_quote(
            input_mint="So11111111111111111111111111111111111111112",  # SOL
            output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            amount="1000000000"  # 1 SOL
        )
        
        # Verify retry mechanism
        assert quote is not None, "Quote should not be None"
        assert quote['inAmount'] == "1000000000", "Input amount should match"
        assert quote['slippageBps'] == 250, "Slippage should match"
        assert mock_sleep.call_count == 2, "Should have retried twice with backoff"
        assert mock_sleep.call_args_list[0][0][0] == 1.0, "First retry should wait 1s"
        assert mock_sleep.call_args_list[1][0][0] == 2.0, "Second retry should wait 2s"
        print("✅ get_quote test passed with retry mechanism")
    
    # Test execute_swap with retry mechanism
    swap_error_response = AsyncMock()
    swap_error_response.status = 429
    swap_error_response.json = AsyncMock(return_value={"error": "Too many requests"})
    swap_error_response.raise_for_status = AsyncMock()
    
    swap_success_response = AsyncMock()
    swap_success_response.status = 200
    swap_success_response.json = AsyncMock(return_value=MOCK_RESPONSES['swap'])
    swap_success_response.raise_for_status = AsyncMock()
    
    # Set up post method with proper context manager
    mock_post_response = AsyncMock()
    mock_post_response.__aenter__ = AsyncMock(side_effect=[swap_error_response, swap_success_response])
    mock_post_response.__aexit__ = AsyncMock(return_value=None)
    mock_session.post = AsyncMock(return_value=mock_post_response)
    wallet_address = "HN7cABqLq46Es1jh92dQQisAq662SmxELLLsHHe4YWrH"
    
    with patch('aiohttp.ClientSession', return_value=mock_session), \
         patch('asyncio.sleep', new=AsyncMock()) as mock_sleep:  # Mock sleep to avoid actual delays
        signature = await client.execute_swap(
            quote_response=MOCK_RESPONSES['quote'],
            wallet_pubkey=wallet_address
        )
        
        # Verify retry mechanism
        assert signature is not None, "Signature should not be None"
        assert mock_sleep.call_count == 1, "Should have retried once with backoff"
        assert mock_sleep.call_args_list[0][0][0] == 1.0, "First retry should wait 1s"
        print("✅ execute_swap test passed with retry mechanism")
    
    # Test error handling
    class MockErrorClientSession(MockClientSession):
        async def get(self, *args, **kwargs):
            class MockResponse:
                async def __aenter__(self):
                    error_response = AsyncMock()
                    error_response.status = 500
                    error_response.json = AsyncMock(return_value={"error": "Internal server error"})
                    error_response.raise_for_status = AsyncMock(side_effect=Exception("Internal server error"))
                    return error_response
                    
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    return None
                    
            return MockResponse()
            
    # Update session for error test
    mock_session = MockErrorClientSession()
    
    with patch('aiohttp.ClientSession', return_value=mock_session):
        try:
            await client.get_quote(
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                amount="1000000000"
            )
            assert False, "Should raise error on server error"
        except Exception as e:
            assert "Internal server error" in str(e), "Should include error message"
            print("✅ error handling test passed")
    
    print("\n✅ All Jupiter v6 API tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_jupiter_v6_trading())
