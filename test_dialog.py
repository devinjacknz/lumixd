import asyncio
import websockets
import json
import sys

async def test_dialog():
    uri = "ws://localhost:8000/api/v1/ws"
    async with websockets.connect(uri) as websocket:
        print("\nPlaybook Trading Scenarios Test")
        
        # Test 1: Full Position Buy
        instruction = "6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump现价买全仓"
        print(f"\n用户: \"{instruction}\"")
        await websocket.send(json.dumps({
            "type": "trade",
            "instruction": instruction
        }))
        # First response is instruction parsed
        response = await asyncio.wait_for(websocket.recv(), timeout=10)
        data = json.loads(response)
        if data.get("type") == "instruction_parsed":
            print("✅ 指令解析成功")
            print("解析参数:", json.dumps(data.get("params", {}), indent=2, ensure_ascii=False))
            
            # Wait for order creation response
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            data = json.loads(response)
            
        print("\n系统:")
        if "order_id" in data:
            print(f"✅ Full position buy order created: {data['order_id']}")
            print(f"Message: {data['message']['zh']}")
            if "params" in data:
                print("参数:")
                for key, value in data["params"].items():
                    print(f"  - {key}: {value}")
        else:
            print("❌ Error:", data.get("message", {}).get("zh", "Unknown error"))
            
        await asyncio.sleep(2)  # Wait for order processing
        
        # Test 2: Timed Half Position Sell
        instruction = "10分钟后卖出半仓，无论什么价格"
        print(f"\n用户: \"{instruction}\"")
        await websocket.send(json.dumps({
            "type": "trade",
            "instruction": instruction
        }))
        
        # First response is instruction parsed
        response = await asyncio.wait_for(websocket.recv(), timeout=10)
        data = json.loads(response)
        if data.get("type") == "instruction_parsed":
            print("✅ 指令解析成功")
            print("解析参数:", json.dumps(data.get("params", {}), indent=2, ensure_ascii=False))
            
            # Wait for order creation response
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            data = json.loads(response)
            
        print("\n系统:")
        if "order_id" in data:
            print(f"✅ 定时卖出订单已创建")
            print(f"订单ID: {data['order_id']}")
            if "params" in data:
                print("参数:")
                for key, value in data["params"].items():
                    print(f"  - {key}: {value}")
        else:
            print("❌ Error:", data.get("message", {}).get("zh", "Unknown error"))
            
        await asyncio.sleep(2)  # Wait for order processing
        
        # Test 3: Conditional Order
        instruction = "20分钟后，如果相对买入价上涨，则卖出剩下全仓；如果下跌，则买入10u"
        print(f"\n用户: \"{instruction}\"")
        await websocket.send(json.dumps({
            "type": "trade",
            "instruction": instruction
        }))
        
        # First response is instruction parsed
        response = await asyncio.wait_for(websocket.recv(), timeout=10)
        data = json.loads(response)
        if data.get("type") == "instruction_parsed":
            print("✅ 指令解析成功")
            print("解析参数:", json.dumps(data.get("params", {}), indent=2, ensure_ascii=False))
            
            # Wait for order creation response
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            data = json.loads(response)
            
        print("\n系统:")
        if "order_id" in data:
            print(f"✅ 条件单已创建")
            print(f"订单ID: {data['order_id']}")
            if "params" in data:
                print("参数:")
                for key, value in data["params"].items():
                    print(f"  - {key}: {value}")
        else:
            print("❌ Error:", data.get("message", {}).get("zh", "Unknown error"))

print("Testing comprehensive dialog flow from playbook...")
try:
    asyncio.run(test_dialog())
except websockets.exceptions.WebSocketException:
    print("❌ Error: Could not connect to WebSocket server. Make sure the server is running.")
    sys.exit(1)
except asyncio.TimeoutError:
    print("❌ Error: Timeout waiting for server response")
    sys.exit(1)
except KeyboardInterrupt:
    print("\n⚠️ Test interrupted by user")
    sys.exit(0)
except Exception as e:
    print(f"❌ Test failed with error: {str(e)}")
    sys.exit(1)
