import asyncio
from src.agents.trading_agent import TradingAgent

async def test_trading():
    agent = TradingAgent(instance_id='test', model_type='deepseek-r1', model_name='deepseek-r1:1.5b')
    
    # Test token info queries
    try:
        # USDC token address
        usdc_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        price = await agent.get_token_price(usdc_address)
        print(f'USDC price in SOL: {price}')
    except Exception as e:
        print(f'Error getting price: {str(e)}')
    
    # Test trading execution with minimal amount
    try:
        trade_request = {
            'token': usdc_address,  # Buy USDC with SOL
            'amount': 0.001,  # Small amount for testing
            'slippage_bps': 250,
            'direction': 'buy'
        }
        signature = await agent.execute_trade(trade_request)
    except Exception as e:
        print(f'Error executing trade: {str(e)}')
    print(f'Trade signature: {signature}')

if __name__ == '__main__':
    asyncio.run(test_trading())
