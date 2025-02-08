from typing import Dict, Optional, List
from datetime import datetime
from src.agents.trading_agent import TradingAgent
from src.api.v1.models.trading_instance import TradingInstance
from src.monitoring.performance_monitor import PerformanceMonitor
from src.monitoring.system_monitor import SystemMonitor
from termcolor import cprint

class InstanceManager:
    def __init__(self):
        self.instances: Dict[str, TradingInstance] = {}
        self.agents: Dict[str, TradingAgent] = {}
        self.performance_monitor = PerformanceMonitor()
        self.system_monitor = SystemMonitor(self.performance_monitor)
        
    def create_instance(self, instance: TradingInstance) -> bool:
        try:
            self.instances[instance.id] = instance
            self.agents[instance.id] = TradingAgent(instance_id=instance.id)
            self.agents[instance.id].update_config(instance.parameters)
            if instance.strategy_id:
                self.agents[instance.id].apply_strategy(
                    instance.strategy_id,
                    instance.parameters.get('strategy_params', {})
                )
            return True
        except Exception as e:
            cprint(f"❌ Error creating instance: {str(e)}", "red")
            return False
            
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
