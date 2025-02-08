import asyncio
from src.models.deepseek_model import DeepSeekModel

def test_model():
    model = DeepSeekModel(model_name="deepseek-r1:1.5b")
    
    # Test Chinese trading instruction
    response = model.generate_response(
        system_prompt="你是一个专业的交易助手，帮助用户分析和执行交易。",
        user_content="分析SOL代币的市场状况，关注价格趋势和流动性"
    )
    print("\n中文测试 | Chinese Test:")
    print(response.content)
    
    # Test English trading instruction
    response = model.generate_response(
        system_prompt="You are a professional trading assistant helping users analyze and execute trades.",
        user_content="Analyze SOL token market conditions, focus on price trends and liquidity"
    )
    print("\nEnglish Test:")
    print(response.content)
    
    # Test trading command parsing
    response = model.generate_response(
        system_prompt="Parse trading instructions and return structured JSON.",
        user_content="买入500个SOL代币，滑点不超过2%"
    )
    print("\n交易指令测试 | Trading Command Test:")
    print(response.content)

if __name__ == "__main__":
    test_model()
