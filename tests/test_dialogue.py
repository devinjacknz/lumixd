import asyncio
import os
import json
from unittest.mock import patch, AsyncMock
from dotenv import load_dotenv
from src.agents.trading_agent import TradingAgent

# Load environment variables
load_dotenv()

# Set up test environment
os.environ["WALLET_ADDRESS"] = "HN7cABqLq46Es1jh92dQQisAq662SmxELLLsHHe4YWrH"
os.environ["RPC_ENDPOINT"] = "https://api.mainnet-beta.solana.com"
os.environ["SOLANA_PRIVATE_KEY"] = "${walletkey}"  # Use test wallet key from environment

# Mock RPC responses
MOCK_BALANCE_RESPONSE = {
    "jsonrpc": "2.0",
    "result": {
        "context": {"slot": 1234},
        "value": 5000000000  # 5 SOL
    },
    "id": "get-balance"
}

async def test_dialogue_trading():
    """Test bilingual dialogue trading functionality"""
    # Create agent with mocked dependencies
    with patch('aiohttp.ClientSession.post', new_callable=AsyncMock) as mock_post:
        # Mock RPC responses
        mock_post.return_value.__aenter__.return_value.json.return_value = MOCK_BALANCE_RESPONSE
        mock_post.return_value.__aenter__.return_value.status = 200
        
        agent = TradingAgent()
    
    async def test_trade_command(command: str, is_chinese: bool = False, mock_post=None):
        """Helper function to test trade commands"""
        print(f"\n🔍 Testing {'Chinese' if is_chinese else 'English'} trading command...")
        print(f"Command: {command}")
        
        try:
            if mock_post:
                # Mock RPC response for balance check
                mock_post.return_value.__aenter__.return_value.json.return_value = MOCK_BALANCE_RESPONSE
                mock_post.return_value.__aenter__.return_value.status = 200
            
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
                print("✅ Trade command executed successfully")
            else:
                assert response["status"] == "error", "Invalid trade command should fail"
                assert "Invalid amount" in response["message"], "Should reject negative amounts"
                print("✅ Invalid trade command rejected correctly")
            
            return response
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            raise
    
    # Test valid Chinese trading command
    cn_response = await test_trade_command(
        "买入500个SOL代币，滑点不超过2%",
        is_chinese=True,
        mock_post=mock_post
    )
    assert cn_response["status"] == "success", "Valid Chinese trade should succeed"
    
    # Test valid English trading command
    en_response = await test_trade_command(
        "Buy 500 SOL tokens with max 2% slippage",
        mock_post=mock_post
    )
    assert en_response["status"] == "success", "Valid English trade should succeed"
    
    # Test error handling in Chinese
    cn_error = await test_trade_command(
        "买入负100个SOL代币",  # Invalid amount
        is_chinese=True,
        mock_post=mock_post
    )
    assert cn_error["status"] == "error", "Expected error for invalid Chinese input"
    assert "金额无效" in cn_error["message_cn"], "Should have Chinese error message"
    
    # Test error handling in English
    en_error = await test_trade_command(
        "Buy -100 SOL tokens",  # Invalid amount
        mock_post=mock_post
    )
    assert en_error["status"] == "error", "Expected error for invalid English input"
    assert "Invalid amount" in en_error["message"], "Should have English error message"
    
    print("\n✅ All dialogue trading tests completed!")

if __name__ == "__main__":
    asyncio.run(test_dialogue_trading())
