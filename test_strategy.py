import asyncio
import json
from trading_strategy import TradingStrategy

async def test_strategy_generation():
    strategy = TradingStrategy()
    
    print("\n测试交易策略生成 Testing Strategy Generation:")
    print("==========================================")
    
    try:
        orders = await strategy.generate_orders()
        
        print("\n1. 全仓买入订单 Full Position Buy Order:")
        print(json.dumps(orders[0], indent=2, ensure_ascii=False))
        
        print("\n2. 定时卖出订单 Timed Sell Order:")
        print(json.dumps(orders[1], indent=2, ensure_ascii=False))
        
        print("\n3. 条件单 Conditional Order:")
        print(json.dumps(orders[2], indent=2, ensure_ascii=False))
        
        execution_plan = await strategy.execute_strategy()
        print("\n执行计划 Execution Plan:")
        for step in execution_plan:
            print(f"\n时间 Time: {step['execution_time']}")
            print(f"类型 Type: {step['order']['type']}")
            print(f"动作 Action: {step['order']['action']}")
            if 'position_size' in step['order']:
                print(f"仓位大小 Position Size: {step['order']['position_size']}")
            if 'amount' in step['order']:
                print(f"数量 Amount: {step['order']['amount']}")
            
        return True
        
    except Exception as e:
        print(f"\n❌ 错误 Error: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_strategy_generation())
        print("\n✅ 策略生成测试完成 Strategy Generation Test Complete")
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断 Test Interrupted")
