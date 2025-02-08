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
    
    # Set up mock responses
    mock_response = MagicMock()
    mock_response.json = AsyncMock(return_value=MOCK_RESPONSES['quote'])
    mock_response.status = 200
    
    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    # Test retry mechanism
    error_response = MagicMock()
    error_response.status = 429  # Too Many Requests
    error_session = MagicMock()
    error_session.__aenter__ = AsyncMock(return_value=error_response)
    error_session.__aexit__ = AsyncMock(return_value=None)
    
    retry_mock = MagicMock()
    retry_mock.side_effect = [error_session, error_session, mock_session]  # Fail twice, succeed on third try
    
    # Test get_quote with retry mechanism
    with patch('aiohttp.ClientSession.post', side_effect=[error_session, error_session, mock_session]):
        start_time = time.time()
        quote = await client.get_quote(
            input_mint="So11111111111111111111111111111111111111112",  # SOL
            output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            amount="1000000000"  # 1 SOL
        )
        end_time = time.time()
        retry_duration = end_time - start_time
        
        # Verify retry mechanism
        assert quote is not None, "Quote should not be None"
        assert quote['inAmount'] == "1000000000", "Input amount should match"
        assert quote['slippageBps'] == 250, "Slippage should match"
        assert retry_duration >= 2.0, "Should have exponential backoff delay"
        print("✅ get_quote test passed with retry mechanism")
    
    # Test execute_swap with retry mechanism
    mock_response.json = AsyncMock(return_value=MOCK_RESPONSES['swap'])
    wallet_address = "HN7cABqLq46Es1jh92dQQisAq662SmxELLLsHHe4YWrH"
        
    with patch('aiohttp.ClientSession.post', side_effect=[error_session, mock_session]):
        start_time = time.time()
        signature = await client.execute_swap(
            quote_response=MOCK_RESPONSES['quote'],
            wallet_pubkey=wallet_address
        )
        end_time = time.time()
        retry_duration = end_time - start_time
        
        # Verify retry mechanism
        assert signature is not None, "Signature should not be None"
        assert retry_duration >= 1.0, "Should have exponential backoff delay"
        print("✅ execute_swap test passed with retry mechanism")
    
    # Test error handling
    error_response = MagicMock()
    error_response.status = 500
    error_response.json = AsyncMock(return_value={"error": "Internal server error"})
    error_session = MagicMock()
    error_session.__aenter__ = AsyncMock(return_value=error_response)
    error_session.__aexit__ = AsyncMock(return_value=None)
    
    with patch('aiohttp.ClientSession.post', return_value=error_session):
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
