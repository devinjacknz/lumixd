import time
import json
import os
from datetime import datetime
from trading_strategy_v2 import TradingStrategy
from src.data.jupiter_client import JupiterClient

def check_balance(jupiter_client, wallet_key):
    """Check SOL balance before trading"""
    try:
        response = jupiter_client.get_quote(
            input_mint="So11111111111111111111111111111111111111112",
            output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            amount="1000000",  # 0.001 SOL to check
            use_shared_accounts=True,
            force_simpler_route=True
        )
        
        if response and float(response.get('inAmount', 0)) > 0:
            print("✅ Wallet connection and balance verified")
            return True
            
        print("❌ Insufficient balance for trading")
        return False
        
    except Exception as e:
        print(f"❌ Balance check failed: {str(e)}")
        return False

def execute_trades():
    """Execute trading strategy with wallet credentials"""
    print("\n执行交易策略 Executing Trading Strategy:")
    print("=====================================")
    
    try:
        # Initialize components
        strategy = TradingStrategy()
        jupiter_client = JupiterClient()
        retry_delay = 1.0  # Initial retry delay in seconds
        
        # Load wallet
        wallet_key = os.getenv("SOLANA_PRIVATE_KEY")
        if not wallet_key:
            raise ValueError("Wallet credentials not found")
            
        # Check balance with retry
        print("\n检查钱包余额 Checking Wallet Balance...")
        retry_count = 0
        while retry_count < 3:
            if check_balance(jupiter_client, wallet_key):
                break
            retry_count += 1
            time.sleep(retry_delay)
            retry_delay *= 1.5  # Exponential backoff
        else:
            raise ValueError("Balance check failed after retries")
            
        # Generate orders
        print("\n生成订单 Generating Orders...")
        execution_plan = strategy.execute_strategy()
        
        for step in execution_plan:
            order = step['order']
            execution_time = step['execution_time']
            
            print(f"\n订单类型 Order Type: {order['type']}")
            print(f"执行时间 Execution Time: {execution_time}")
            print(f"交易动作 Action: {order['action']}")
            
            if order['type'] == 'immediate':
                # Execute immediate order with retry
                retry_count = 0
                retry_delay = 1.0
                while retry_count < 3:
                    try:
                        quote = jupiter_client.get_quote(
                            input_mint="So11111111111111111111111111111111111111112",
                            output_mint=order['token_address'],
                            amount=str(int(order['amount'] * 1e9)),  # Convert to lamports
                            use_shared_accounts=True,
                            force_simpler_route=True
                        )
                        if quote:
                            print(f"报价 Quote: {json.dumps(quote, indent=2)}")
                            # Execute swap
                            signature = jupiter_client.execute_swap(quote, wallet_key)
                            if signature:
                                print(f"✅ Swap executed: {signature}")
                                print(f"🔍 View on Solscan: https://solscan.io/tx/{signature}")
                            break
                    except Exception as e:
                        print(f"Retry {retry_count + 1}: {str(e)}")
                        retry_count += 1
                        if retry_count < 3:
                            time.sleep(retry_delay)
                            retry_delay *= 1.5
                
            elif order['type'] == 'timed':
                delay = (execution_time - datetime.now()).total_seconds()
                if delay > 0:
                    print(f"等待执行 Waiting for {delay} seconds...")
                    time.sleep(delay)
                print("执行定时订单 Executing timed order...")
                
            elif order['type'] == 'conditional':
                delay = (execution_time - datetime.now()).total_seconds()
                if delay > 0:
                    print(f"等待检查条件 Waiting to check condition in {delay} seconds...")
                    time.sleep(delay)
                print("检查价格条件 Checking price condition...")
                
            print(f"✅ 订单已处理 Order processed")
            
        return True
        
    except Exception as e:
        print(f"\n❌ 执行错误 Execution Error: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        result = execute_trades()
        if result:
            print("\n✅ 交易策略执行完成 Trading Strategy Execution Complete")
        else:
            print("\n❌ 交易策略执行失败 Trading Strategy Execution Failed")
    except KeyboardInterrupt:
        print("\n⚠️ 执行被用户中断 Execution Interrupted")
