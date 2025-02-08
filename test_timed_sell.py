import asyncio
import websockets
import json
import sys

async def execute_timed_sell():
    uri = 'ws://localhost:8000/api/v1/ws'
    try:
        async with websockets.connect(uri) as websocket:
            instruction = '10分钟后卖出半仓，无论什么价格'
            print(f"\n用户: \"{instruction}\"")
            
            await websocket.send(json.dumps({
                'type': 'trade',
                'instruction': instruction
            }))
            
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                
                if data.get('type') == 'instruction_parsed':
                    print("\n✅ 指令解析成功")
                    print("解析参数:", json.dumps(data.get('params', {}), indent=2, ensure_ascii=False))
                    continue
                    
                if data.get('type') == 'order_created':
                    print("\n✅ 定时卖出订单已创建")
                    print(f"订单ID: {data.get('order_id')}")
                    print("参数:")
                    for key, value in data.get('params', {}).items():
                        print(f"  - {key}: {value}")
                    return True
                    
                if data.get('type') == 'error':
                    print(f"\n❌ 错误: {data.get('message', {}).get('zh', '未知错误')}")
                    return False
                    
    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket连接错误: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ 执行错误: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(execute_timed_sell())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        sys.exit(0)
