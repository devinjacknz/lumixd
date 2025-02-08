import asyncio
import websockets
import json

async def test_trading_scenarios():
    uri = "ws://localhost:8000/api/v1/ws"
    async with websockets.connect(uri) as websocket:
        print("\nTest 1: Full Position Buy Order")
        instruction = "6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump现价买全仓"
        print(f"\n用户: \"{instruction}\"")
        await websocket.send(json.dumps({
            "type": "trade_request",
            "data": {
                "instruction": instruction,
                "instance_id": "test"
            }
        }))
        
        # Wait for instruction received acknowledgment
        response = await asyncio.wait_for(websocket.recv(), timeout=10)
        data = json.loads(response)
        print("\n系统: 收到指令")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # Wait for order created response
        response = await asyncio.wait_for(websocket.recv(), timeout=10)
        data = json.loads(response)
        print("\n系统: 创建订单")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        if data.get('type') != 'order_created':
            raise Exception(f"Failed to create buy order: {data}")
            
        buy_order_id = data['data']['order_id']
        entry_price = data['data'].get('price', 0)
        
        print("\nTest 2: Timed Half Position Sell")
        instruction = "10分钟后卖出半仓，无论什么价格"
        print(f"\n用户: \"{instruction}\"")
        await websocket.send(json.dumps({
            "type": "trade_request",
            "data": {
                "instruction": instruction,
                "instance_id": "test"
            }
        }))
        
        # Wait for instruction received acknowledgment
        response = await asyncio.wait_for(websocket.recv(), timeout=10)
        data = json.loads(response)
        print("\n系统: 收到指令")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # Wait for order created response
        response = await asyncio.wait_for(websocket.recv(), timeout=10)
        data = json.loads(response)
        print("\n系统: 创建订单")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        if data.get('type') != 'order_created':
            raise Exception(f"Failed to create timed sell order: {data}")
            
        print("\nTest 3: Conditional Trading")
        instruction = "20分钟后，如果相对买入价上涨，则卖出剩下全仓；如果下跌，则买入10u"
        print(f"\n用户: \"{instruction}\"")
        await websocket.send(json.dumps({
            "type": "trade_request",
            "data": {
                "instruction": instruction,
                "instance_id": "test",
                "entry_price": entry_price
            }
        }))
        
        # Wait for instruction received acknowledgment
        response = await asyncio.wait_for(websocket.recv(), timeout=10)
        data = json.loads(response)
        print("\n系统: 收到指令")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # Wait for order created response
        response = await asyncio.wait_for(websocket.recv(), timeout=10)
        data = json.loads(response)
        print("\n系统: 创建订单")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        if data.get('type') != 'order_created':
            raise Exception(f"Failed to create conditional order: {data}")
            
        # Monitor order execution
        print("\n监控订单执行...")
        while True:
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            data = json.loads(response)
            if data.get('type') == 'order_update':
                print(f"\n📊 订单更新: {json.dumps(data['data'], indent=2, ensure_ascii=False)}")

print("Testing advanced trading scenarios...")
try:
    asyncio.run(test_trading_scenarios())
except Exception as e:
    print(f"Test failed with error: {str(e)}")
    raise
