import asyncio
import os
import json
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
    
    # Test get_quote
    with patch('aiohttp.ClientSession.post', return_value=mock_session):
        quote = await client.get_quote(
            input_mint="So11111111111111111111111111111111111111112",  # SOL
            output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            amount="1000000000"  # 1 SOL
        )
        assert quote is not None, "Quote should not be None"
        assert quote['inAmount'] == "1000000000", "Input amount should match"
        assert quote['slippageBps'] == 250, "Slippage should match"
        print("✅ get_quote test passed")
    
    # Test execute_swap
    mock_response.json = AsyncMock(return_value=MOCK_RESPONSES['swap'])
    wallet_address = os.getenv("WALLET_ADDRESS")
    if not wallet_address:
        raise ValueError("WALLET_ADDRESS environment variable is not set")
        
    with patch('aiohttp.ClientSession.post', return_value=mock_session):
        signature = await client.execute_swap(
            quote_response=MOCK_RESPONSES['quote'],
            wallet_pubkey=wallet_address
        )
        assert signature is not None, "Signature should not be None"
        print("✅ execute_swap test passed")
    
    print("\n✅ All Jupiter v6 API tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_jupiter_v6_trading())
