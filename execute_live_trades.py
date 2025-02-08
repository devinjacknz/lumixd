import asyncio
import os
from src.data.jupiter_client import JupiterClient
from trading_strategy_v2 import TradingStrategy

async def execute_trade():
    client = JupiterClient()
    strategy = TradingStrategy()
    
    print("\n执行交易 Executing Trades:")
    print("=========================")
    
    # Check balance
    try:
        quote = await client.get_quote(
            input_mint='So11111111111111111111111111111111111111112',
            output_mint='6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump',
            amount='1000000000'  # 1 SOL
        )
        
        if quote:
            print('✅ Balance check passed')
            orders = strategy.generate_orders()
            if orders:
                print(f'\n生成订单 Generated {len(orders)} orders')
                for order in orders:
                    print(f'\n执行订单 Executing order: {order}')
                    if order['type'] == 'immediate':
                        result = await client.execute_swap(
                            quote,
                            os.getenv('WALLET_KEY'),
                            slippage_bps=250
                        )
                        print(f'交易结果 Swap result: {result}')
                        if result:
                            print(f'🔍 View on Solscan: https://solscan.io/tx/{result}')
        else:
            print('❌ Insufficient balance')
            
    except Exception as e:
        print(f'❌ Error executing trade: {str(e)}')

if __name__ == "__main__":
    asyncio.run(execute_trade())
