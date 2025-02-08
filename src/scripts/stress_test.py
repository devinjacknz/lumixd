import asyncio
import os
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from termcolor import cprint
from src.scripts.test_config import TEST_CONFIG
from src.monitoring.system_monitor import SystemMonitor
from src.monitoring.performance_monitor import PerformanceMonitor
from src.services.instance_manager import InstanceManager
from src.services.balance_manager import BalanceManager
from src.data.chainstack_client import ChainStackClient

async def run_stress_test():
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=TEST_CONFIG['duration_hours'])
    
    performance_monitor = PerformanceMonitor()
    system_monitor = SystemMonitor(performance_monitor)
    instance_manager = InstanceManager()
    balance_manager = BalanceManager()
    client = ChainStackClient()
    
    cprint("\n🚀 Starting stress test...", "cyan")
    cprint(f"⏱️ Duration: {TEST_CONFIG['duration_hours']} hours", "cyan")
    cprint(f"🤖 Instances: {len(TEST_CONFIG['instances'])}", "cyan")
    cprint(f"⌛ Trade interval: {TEST_CONFIG['trade_interval_seconds']}s", "cyan")
    
    # Initialize instances
    instance_ids = []
    for instance_config in TEST_CONFIG['instances']:
        try:
            # Convert Decimal values to float for JSON serialization
            config = {
                'name': instance_config['name'],
                'description': f"Trading instance for {instance_config['tokens'][0]}/{instance_config['tokens'][1]} pair",
                'strategy_id': 'default',
                'tokens': instance_config['tokens'],
                'amount_sol': float(instance_config['amount_sol']),
                'parameters': {
                    'allocation': float(instance_config['allocation']),
                    'slippage_bps': 250,
                    'max_position_size': 0.2,
                    'use_shared_accounts': True,
                    'force_simpler_route': True
                }
            }
            
            instance_id = instance_manager.create_instance(config)
            if not instance_id:
                cprint(f"❌ Failed to create instance: {config['name']}", "red")
                continue
                
            instance_ids.append(instance_id)
            cprint(f"✅ Created instance: {config['name']} ({instance_id})", "green")
        except Exception as e:
            cprint(f"❌ Error creating instance: {str(e)}", "red")
            continue
    
    last_trade_time = datetime.now() - timedelta(seconds=TEST_CONFIG['trade_interval_seconds'])
    
    while datetime.now() < end_time:
        try:
            # Check system health
            health = system_monitor.check_system_health()
            if health['status'] != 'healthy':
                cprint(f"❌ System health check failed: {health}", "red")
                await asyncio.sleep(60)
                continue
                
            # Check if it's time to trade
            if (datetime.now() - last_trade_time).total_seconds() >= TEST_CONFIG['trade_interval_seconds']:
                # Get wallet balance
                wallet_balance = client.get_wallet_balance(TEST_CONFIG['wallet_address'])
                if wallet_balance < TEST_CONFIG['performance_thresholds']['min_sol_balance']:
                    cprint(f"❌ Insufficient balance: {wallet_balance} SOL", "red")
                    break
                    
                # Execute trades for each instance
                for instance_id in instance_manager.list_instances():
                    instance = instance_manager.get_instance(instance_id)
                    if not instance or not instance.active:
                        continue
                        
                    # Monitor instance health
                    metrics = system_monitor.check_instance_health(instance_id)
                    if metrics['status'] != 'healthy':
                        cprint(f"❌ Instance {instance_id} health check failed", "red")
                        continue
                        
                    # Execute trade
                    signature = await instance_manager.execute_instance_trade(
                        instance_id,
                        instance.tokens[1],  # Trade SOL for token
                        instance.amount_sol
                    )
                    
                    if signature:
                        cprint(f"✅ Trade executed: {signature}", "green")
                        cprint(f"🔍 View on Solscan: https://solscan.io/tx/{signature}", "cyan")
                        
                        # Verify transaction
                        if await system_monitor.verify_transaction(signature):
                            cprint(f"✅ Transaction verified", "green")
                        else:
                            cprint(f"❌ Transaction verification failed", "red")
                    else:
                        cprint(f"❌ Trade failed for instance {instance_id}", "red")
                        
                last_trade_time = datetime.now()
                
            # Update metrics
            for instance_id in instance_manager.list_instances():
                metrics = instance_manager.get_instance_metrics(instance_id)
                performance_monitor.log_trade_metrics(metrics)
                
            # Print progress
            elapsed = datetime.now() - start_time
            remaining = end_time - datetime.now()
            cprint(f"\n⏱️ Progress: {elapsed.total_seconds()/3600:.1f}h / {TEST_CONFIG['duration_hours']}h", "cyan")
            cprint(f"⌛ Remaining: {remaining.total_seconds()/3600:.1f}h", "cyan")
            performance_monitor.print_summary()
            
            await asyncio.sleep(60)
            
        except Exception as e:
            cprint(f"❌ Error in stress test loop: {str(e)}", "red")
            await asyncio.sleep(60)
            
    cprint("\n🏁 Stress test completed!", "cyan")
    performance_monitor.print_summary()

if __name__ == "__main__":
    asyncio.run(run_stress_test())
