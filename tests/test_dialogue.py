import asyncio
import os
import json
from unittest.mock import patch, AsyncMock
from dotenv import load_dotenv
from src.agents.trading_agent import TradingAgent
from src.models.base_model import ModelResponse

# Load environment variables
load_dotenv()

# Set up test environment
os.environ["WALLET_ADDRESS"] = "HN7cABqLq46Es1jh92dQQisAq662SmxELLLsHHe4YWrH"
os.environ["RPC_ENDPOINT"] = "https://api.mainnet-beta.solana.com"
os.environ["SOLANA_PRIVATE_KEY"] = "${walletkey}"  # Use test wallet key from environment

# Mock responses
MOCK_RESPONSES = {
    'balance': {
        "jsonrpc": "2.0",
        "result": {
            "context": {"slot": 1234},
            "value": 5000000000  # 5 SOL
        },
        "id": "get-balance"
    },
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

async def test_dialogue_trading():
    """Test bilingual dialogue trading functionality"""
    # Create agent with mocked dependencies
    # Create mock objects
    mock_response = AsyncMock()
    mock_response.json.return_value = MOCK_RESPONSES['balance']
    mock_response.status = 200
    
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_response
    
    mock_post = AsyncMock()
    mock_post.return_value = mock_session
    
    mock_quote = AsyncMock()
    mock_quote.return_value = MOCK_RESPONSES['quote']
    
    mock_swap = AsyncMock()
    mock_swap.return_value = "tx_signature_123"
    
    # Apply patches
    # Set up mock responses
    mock_response = AsyncMock()
    mock_response.json.return_value = MOCK_RESPONSES['balance']
    mock_response.status = 200
    
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_response
    
    mock_post = AsyncMock()
    mock_post.return_value = mock_session
    
    mock_quote = AsyncMock()
    mock_quote.return_value = MOCK_RESPONSES['quote']
    
    mock_swap = AsyncMock()
    mock_swap.return_value = "tx_signature_123"
    
    mock_generate = AsyncMock()
    mock_generate.return_value = ModelResponse(
        content=json.dumps({
            'direction': 'buy',
            'token': 'SOL',
            'amount': 500,
            'slippage_bps': 200
        }),
        raw_response={'response': 'mocked response'}
    )
    
    # Apply patches using regular context managers
    with patch('aiohttp.ClientSession.post', mock_post), \
         patch('src.data.jupiter_client.JupiterClient.get_quote', mock_quote), \
         patch('src.data.jupiter_client.JupiterClient.execute_swap', mock_swap), \
         patch('src.models.ollama_model.OllamaModel.generate_response', mock_generate):
        
        agent = TradingAgent()
    
    async def test_trade_command(command: str, is_chinese: bool = False, mock_post=None, mock_quote=None, mock_swap=None):
        """Helper function to test trade commands"""
        print(f"\n🔍 Testing {'Chinese' if is_chinese else 'English'} trading command...")
        print(f"Command: {command}")
        
        try:
            # Set up mocks if provided
            if all([mock_post, mock_quote, mock_swap]):
                mock_response = AsyncMock()
                mock_response.json.return_value = MOCK_RESPONSES['balance']
                mock_response.status = 200
                mock_post.return_value.__aenter__.return_value = mock_response
                mock_quote.return_value = MOCK_RESPONSES['quote']
                mock_swap.return_value = "tx_signature_123"
            
            response = await agent.execute_dialogue_trade(command)
            print(f"Response: {response}")
            
            # Verify response structure
            assert isinstance(response, dict), "Response should be a dictionary"
            assert "status" in response, "Response should have status field"
            assert "message" in response, "Response should have message field"
            assert "message_cn" in response, "Response should have message_cn field"
            
            # For valid trade commands, verify success
            if "负" not in command and "-" not in command:
                assert response["status"] == "success", f"Valid trade command should succeed: {response['message']}"
                if is_chinese:
                    assert "交易执行成功" in response["message_cn"], "Should have Chinese success message"
                else:
                    assert "Trade executed successfully" in response["message"], "Should have English success message"
                print("✅ Trade command executed successfully")
            else:
                assert response["status"] == "error", "Invalid trade command should fail"
                if is_chinese:
                    assert "金额无效" in response["message_cn"], "Should have Chinese error message"
                else:
                    assert "Invalid amount" in response["message"], "Should have English error message"
                print("✅ Invalid trade command rejected correctly")
            
            return response
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            raise
    
    # Test valid Chinese trading command
    cn_response = await test_trade_command(
        "买入500个SOL代币，滑点不超过2%",
        is_chinese=True,
        mock_post=mock_post,
        mock_quote=mock_quote,
        mock_swap=mock_swap
    )
    assert cn_response["status"] == "success", "Valid Chinese trade should succeed"
    assert "交易执行成功" in cn_response["message_cn"], "Should have Chinese success message"
    
    # Test valid English trading command
    en_response = await test_trade_command(
        "Buy 500 SOL tokens with max 2% slippage",
        mock_post=mock_post,
        mock_quote=mock_quote,
        mock_swap=mock_swap
    )
    assert en_response["status"] == "success", "Valid English trade should succeed"
    assert "Trade executed successfully" in en_response["message"], "Should have English success message"
    
    # Test error handling in Chinese
    cn_error = await test_trade_command(
        "买入负100个SOL代币",  # Invalid amount
        is_chinese=True,
        mock_post=mock_post,
        mock_quote=mock_quote,
        mock_swap=mock_swap
    )
    assert cn_error["status"] == "error", "Expected error for invalid Chinese input"
    assert "金额无效" in cn_error["message_cn"], "Should have Chinese error message"
    
    # Test error handling in English
    en_error = await test_trade_command(
        "Buy -100 SOL tokens",  # Invalid amount
        mock_post=mock_post,
        mock_quote=mock_quote,
        mock_swap=mock_swap
    )
    assert en_error["status"] == "error", "Expected error for invalid English input"
    assert "Invalid amount" in en_error["message"], "Should have English error message"
    
    print("\n✅ All dialogue trading tests completed successfully!")
    
    print("\n✅ All dialogue trading tests completed!")

if __name__ == "__main__":
    asyncio.run(test_dialogue_trading())
