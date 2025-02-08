import asyncio
import os
import json
import time
import pytest
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
        "slippageBps": 250,
        "platformFee": None,
        "priceImpactPct": 0.1
    },
    'swap': {
        "swapTransaction": "base64_encoded_transaction",
        "lastValidBlockHeight": 123456789,
        "result": "test_signature_123"  # Jupiter v6 API returns signature in result field
    }
}

@pytest.mark.asyncio
async def test_jupiter_v6_trading():
    """Test Jupiter v6 API trading functionality"""
    # Create client with mocked dependencies
    client = JupiterClient()
    
    # Set up mock responses for get_quote
    class MockResponse:
        def __init__(self, responses):
            self.responses = responses
            self._call_count = 0
            
        async def __aenter__(self):
            if self._call_count < len(self.responses):
                response = self.responses[self._call_count]
                self._call_count += 1
                return response
            return self.responses[-1]
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None
            
    class MockClientSession:
        def __init__(self):
            # Create mock responses
            self.error_response = AsyncMock()
            self.error_response.status = 429
            self.error_response.json = AsyncMock(return_value={"error": "Too many requests"})
            self.error_response.raise_for_status = AsyncMock()
            
            self.success_response = AsyncMock()
            self.success_response.status = 200
            self.success_response.json = AsyncMock(return_value=MOCK_RESPONSES['quote'])
            self.success_response.raise_for_status = AsyncMock()
            
            self.swap_error = AsyncMock()
            self.swap_error.status = 429
            self.swap_error.json = AsyncMock(return_value={"error": "Too many requests"})
            self.swap_error.raise_for_status = AsyncMock()
            
            # First response is for getting swap transaction
            self.swap_success = AsyncMock()
            self.swap_success.status = 200
            self.swap_success.json = AsyncMock(return_value={
                "swapTransaction": "base64_encoded_transaction"
            })
            self.swap_success.raise_for_status = AsyncMock()
            
            # Second response is for sending transaction to RPC
            self.rpc_success = AsyncMock()
            self.rpc_success.status = 200
            self.rpc_success.json = AsyncMock(return_value={
                "jsonrpc": "2.0",
                "id": "send-tx",
                "result": "test_signature_123"
            })
            self.rpc_success.raise_for_status = AsyncMock()
            
            # Third response is for monitoring transaction
            self.monitor_success = AsyncMock()
            self.monitor_success.status = 200
            self.monitor_success.json = AsyncMock(return_value={
                "jsonrpc": "2.0",
                "id": "get-tx-status",
                "result": {
                    "value": [{
                        "confirmationStatus": "finalized",
                        "err": None
                    }]
                }
            })
            self.monitor_success.raise_for_status = AsyncMock()
            
            # Create blockhash response
            self.blockhash_success = AsyncMock()
            self.blockhash_success.status = 200
            self.blockhash_success.json = AsyncMock(return_value={
                "jsonrpc": "2.0",
                "id": "get-blockhash",
                "result": {
                    "value": {
                        "blockhash": "test_blockhash_123",
                        "lastValidBlockHeight": 123456789
                    }
                }
            })
            self.blockhash_success.raise_for_status = AsyncMock()

            # Set up response sequences
            self.get_responses = [self.error_response, self.error_response, self.success_response]
            self.post_responses = [
                self.swap_error,        # First attempt fails
                self.swap_success,      # Get swap transaction
                self.blockhash_success, # Get blockhash
                self.rpc_success,       # Send transaction to RPC
                self.monitor_success    # Monitor transaction status
            ]
            self.get_index = 0
            self.post_index = 0
            
        async def __aenter__(self):
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None
            
        def get(self, *args, **kwargs):
            outer_self = self
            class ContextManager:
                async def __aenter__(self):
                    response = outer_self.get_responses[min(outer_self.get_index, len(outer_self.get_responses) - 1)]
                    outer_self.get_index += 1
                    return response
                    
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    return None
            return ContextManager()
            
        def post(self, *args, **kwargs):
            outer_self = self
            class ContextManager:
                async def __aenter__(self):
                    response = outer_self.post_responses[min(outer_self.post_index, len(outer_self.post_responses) - 1)]
                    outer_self.post_index += 1
                    return response
                    
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    return None
            return ContextManager()
            
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
    wallet_address = "HN7cABqLq46Es1jh92dQQisAq662SmxELLLsHHe4YWrH"
    
    # Reset mock session for swap test
    mock_session.post_index = 0
    
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
        def __init__(self):
            super().__init__()
            error_response = AsyncMock()
            error_response.status = 500
            error_response.json = AsyncMock(return_value={"error": "Internal server error"})
            error_response.raise_for_status = AsyncMock(side_effect=Exception("Internal server error"))
            self.get_responses = [error_response]
            
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
