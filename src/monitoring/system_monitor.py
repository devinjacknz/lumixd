import psutil
import time
from datetime import datetime
from typing import Dict, Any
from src.data.chainstack_client import ChainStackClient
from src.monitoring.performance_monitor import PerformanceMonitor

class SystemMonitor:
    def __init__(self, performance_monitor: PerformanceMonitor):
        self.client = ChainStackClient()
        self.performance_monitor = performance_monitor
        self.last_check = datetime.now()
        
    def check_system_health(self) -> Dict[str, Any]:
        try:
            start_time = time.time()
            wallet_balance = self.client.get_wallet_balance()
            rpc_latency = int((time.time() - start_time) * 1000)
            
            metrics = {
                'wallet_balance': wallet_balance,
                'cpu_usage': psutil.cpu_percent(),
                'memory_usage': psutil.virtual_memory().percent,
                'rpc_latency': rpc_latency
            }
            
            self.performance_monitor.log_system_health(metrics)
            return metrics
        except Exception as e:
            self.performance_monitor.logger.error(f"System health check failed: {str(e)}")
            return {}
            
    def monitor_trading_interval(self, token: str, last_trade_time: datetime):
        current_time = datetime.now()
        interval_seconds = int((current_time - last_trade_time).total_seconds())
        self.performance_monitor.log_trading_interval(token, interval_seconds)
        self.last_check = current_time
