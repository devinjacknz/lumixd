import asyncio
import aiohttp
import json
import time
from datetime import datetime
from src.monitoring.network_monitor import network_monitor
from src.services.trade_verifier import trade_verifier
from src.services.logging_service import logging_service

async def monitor_system():
    print("🔄 Starting system monitoring...")
    start_time = time.time()
    monitoring_duration = 7200  # 2 hours
    check_interval = 60  # 1 minute
    
    while time.time() - start_time < monitoring_duration:
        try:
            # Check network health
            health = await network_monitor.check_network_health()
            print(f"\n⚡ Network Health Check ({datetime.now().strftime('%H:%M:%S')}):")
            print(f"RPC Status: {'✅' if health['rpc'] else '❌'}")
            print(f"Jupiter Status: {'✅' if health['jupiter'] else '❌'}")
            
            # Get recent trades from logs
            recent_trades = await logging_service.get_recent_actions(10)
            print("\n🔍 Recent Trade Activity:")
            for trade in recent_trades:
                if trade.get('action_type') == 'trade_result':
                    # Verify transaction on Solscan
                    tx_sig = trade.get('data', {}).get('transaction_signature')
                    if tx_sig:
                        verification = await trade_verifier.verify_transaction(tx_sig)
                        print(f"Transaction {tx_sig[:8]}... : {'✅' if verification['verified'] else '❌'}")
            
            # Check WebSocket connections
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.ws_connect('ws://localhost:8082/ws/price_updates') as ws:
                        await ws.send_text("So11111111111111111111111111111111111111112")
                        response = await ws.receive_json()
                        print("\n📡 WebSocket Status: ✅")
                        print(f"Price Update Received: {response.get('data', {}).get('price')}")
                except Exception as e:
                    print(f"\n📡 WebSocket Status: ❌ ({str(e)})")
            
            await asyncio.sleep(check_interval)
            
        except Exception as e:
            print(f"❌ Monitoring error: {str(e)}")
            await asyncio.sleep(check_interval)
            
    print("\n✅ System monitoring completed")

if __name__ == "__main__":
    asyncio.run(monitor_system())
