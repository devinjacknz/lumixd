import asyncio
import os
from dotenv import load_dotenv
from src.agents.trading_agent import TradingAgent

# Load environment variables
load_dotenv()

# Set up test environment
os.environ["WALLET_ADDRESS"] = "HN7cABqLq46Es1jh92dQQisAq662SmxELLLsHHe4YWrH"
os.environ["RPC_ENDPOINT"] = "https://solana-mainnet.core.chainstack.com/60d783949ddfbc48b7f1232aa308d7b8"
os.environ["SOLANA_PRIVATE_KEY"] = "${walletkey}"  # Use test wallet key from environment

async def test_dialogue_trading():
    """Test bilingual dialogue trading functionality"""
    agent = TradingAgent()
    
    async def test_trade_command(command: str, is_chinese: bool = False):
        """Helper function to test trade commands"""
        print(f"\n🔍 Testing {'Chinese' if is_chinese else 'English'} trading command...")
        print(f"Command: {command}")
        
        try:
            response = await agent.execute_dialogue_trade(command)
            print(f"Response: {response}")
            
            # Verify response structure
            assert isinstance(response, dict), "Response should be a dictionary"
            assert "status" in response, "Response should have status field"
            assert "message" in response, "Response should have message field"
            assert "message_cn" in response, "Response should have message_cn field"
            
            # Check if trade parameters were parsed correctly
            if response["status"] == "success":
                print("✅ Trade command parsed successfully")
            else:
                print(f"⚠️ Trade command failed: {response['message_cn'] if is_chinese else response['message']}")
                
            return response
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            raise
    
    # Test valid Chinese trading command
    cn_response = await test_trade_command(
        "买入500个SOL代币，滑点不超过2%",
        is_chinese=True
    )
    
    # Test valid English trading command
    en_response = await test_trade_command(
        "Buy 500 SOL tokens with max 2% slippage"
    )
    
    # Test error handling in Chinese
    cn_error = await test_trade_command(
        "买入负100个SOL代币",  # Invalid amount
        is_chinese=True
    )
    assert cn_error["status"] == "error", "Expected error for invalid Chinese input"
    
    # Test error handling in English
    en_error = await test_trade_command(
        "Buy -100 SOL tokens",  # Invalid amount
    )
    assert en_error["status"] == "error", "Expected error for invalid English input"
    
    print("\n✅ All dialogue trading tests completed!")

if __name__ == "__main__":
    asyncio.run(test_dialogue_trading())
