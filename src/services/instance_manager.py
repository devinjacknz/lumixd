from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal
from termcolor import cprint
from src.api.v1.models.trading_instance import TradingInstance, InstanceMetrics
from src.api.v1.models.trade_request import TradeRequest
from src.agents.trading_agent import TradingAgent
from src.monitoring.performance_monitor import PerformanceMonitor
from src.monitoring.system_monitor import SystemMonitor

class InstanceManager:
    def __init__(self):
        self.instances: Dict[str, TradingInstance] = {}
        self.agents: Dict[str, TradingAgent] = {}
        self.next_id = 1
        self.performance_monitor = PerformanceMonitor()
        self.system_monitor = SystemMonitor(self.performance_monitor)
        
    def create_instance(self, config: Dict[str, Any]) -> Optional[str]:
        try:
            instance_id = f"instance_{self.next_id}"
            self.next_id += 1
            
            # Convert Decimal values to float
            amount_sol = float(config['amount_sol']) if isinstance(config['amount_sol'], (Decimal, str)) else config['amount_sol']
            
            # Create instance with proper configuration
            instance = TradingInstance(
                id=instance_id,
                name=str(config['name']),
                description=str(config.get('description', '')),
                strategy_id=str(config.get('strategy_id', 'default')),
                tokens=list(config['tokens']),
                amount_sol=amount_sol,
                parameters=dict(config.get('parameters', {})),
                active=True,
                metrics=InstanceMetrics()
            )
            
            self.agents[instance_id] = TradingAgent(instance_id, config)
            self.agents[instance_id].update_config(config.get('parameters', {}))
            self.instances[instance_id] = instance
            
            cprint(f"✅ Created instance {instance.name} ({instance_id})", "green")
            return instance_id
        except Exception as e:
            cprint(f"❌ Failed to create instance: {str(e)}", "red")
            return None
            
    def get_instance(self, instance_id: str) -> Optional[TradingInstance]:
        return self.instances.get(instance_id)
        
    def list_instances(self) -> List[str]:
        return list(self.instances.keys())
        
    def get_instance_metrics(self, instance_id: str) -> Dict[str, Any]:
        instance = self.instances.get(instance_id)
        agent = self.agents.get(instance_id)
        if not instance or not agent:
            return {}
        return {
            'instance': instance.metrics.dict() if instance.metrics else {},
            'agent': agent.get_instance_metrics(),
            'health': self.system_monitor.check_system_health(),
            'performance': self.performance_monitor.get_summary()
        }
        
    def update_instance_metrics(self, instance_id: str, metrics: Dict[str, Any]) -> bool:
        instance = self.instances.get(instance_id)
        agent = self.agents.get(instance_id)
        if not instance or not agent:
            return False
            
        if instance.metrics:
            instance.metrics.update(metrics)
            
        agent_metrics = agent.get_instance_metrics()
        agent_metrics.update(metrics)
        
        return True
        
    async def execute_instance_trade(self, instance_id: str, token: str, amount_sol: float) -> Optional[str]:
        try:
            instance = self.instances.get(instance_id)
            agent = self.agents.get(instance_id)
            if not instance or not agent:
                cprint(f"❌ Instance {instance_id} not found", "red")
                return None
                
            if not instance.active:
                cprint(f"❌ Instance {instance_id} is not active", "red")
                return None
                
            trade_request = {
                'input_token': "So11111111111111111111111111111111111111112",
                'output_token': token,
                'amount_sol': amount_sol,
                'slippage_bps': instance.parameters.get('slippage_bps', 250),
                'use_shared_accounts': instance.parameters.get('use_shared_accounts', True),
                'force_simpler_route': instance.parameters.get('force_simpler_route', True)
            }
            
            signature = agent.execute_trade(trade_request)
            if signature:
                cprint(f"✅ Trade executed: {signature}", "green")
                cprint(f"🔍 View on Solscan: https://solscan.io/tx/{signature}", "cyan")
                
                await self.update_instance_metrics(instance_id, {
                    'last_trade_time': datetime.now().isoformat(),
                    'last_trade_signature': signature,
                    'last_trade_status': 'success'
                })
                
            return signature
        except Exception as e:
            cprint(f"❌ Error executing trade: {str(e)}", "red")
            return None

            
    def get_instance(self, instance_id: str) -> Optional[TradingInstance]:
        return self.instances.get(instance_id)
        
    def get_agent(self, instance_id: str) -> Optional[TradingAgent]:
        return self.agents.get(instance_id)
        
    def list_instances(self) -> List[TradingInstance]:
        return list(self.instances.values())
        
    def update_instance(self, instance_id: str, instance: TradingInstance) -> bool:
        try:
            if instance_id not in self.instances:
                return False
            self.instances[instance_id] = instance
            self.agents[instance_id].update_config(instance.parameters)
            if instance.strategy_id:
                self.agents[instance_id].apply_strategy(
                    instance.strategy_id,
                    instance.parameters.get('strategy_params', {})
                )
            return True
        except Exception as e:
            cprint(f"❌ Error updating instance: {str(e)}", "red")
            return False
            
    def delete_instance(self, instance_id: str) -> bool:
        try:
            if instance_id not in self.instances:
                return False
            agent = self.agents[instance_id]
            agent.active = False
            del self.instances[instance_id]
            del self.agents[instance_id]
            return True
        except Exception as e:
            cprint(f"❌ Error deleting instance: {str(e)}", "red")
            return False
            
    def get_instance_metrics(self, instance_id: str) -> Optional[Dict]:
        try:
            if instance_id not in self.agents:
                return None
            agent = self.agents[instance_id]
            instance = self.instances[instance_id]
            metrics = agent.get_instance_metrics()
            metrics.update({
                'health': self.system_monitor.check_system_health(),
                'performance': self.performance_monitor.get_summary()
            })
            return metrics
        except Exception as e:
            cprint(f"❌ Error getting metrics: {str(e)}", "red")
            return None
            
    def start_instance(self, instance_id: str) -> bool:
        try:
            if instance_id not in self.instances:
                return False
            agent = self.agents[instance_id]
            instance = self.instances[instance_id]
            agent.active = True
            agent.run(instance.parameters)
            return True
        except Exception as e:
            cprint(f"❌ Error starting instance: {str(e)}", "red")
            return False
            
    def stop_instance(self, instance_id: str) -> bool:
        try:
            if instance_id not in self.instances:
                return False
            agent = self.agents[instance_id]
            agent.active = False
            return True
        except Exception as e:
            cprint(f"❌ Error stopping instance: {str(e)}", "red")
            return False
