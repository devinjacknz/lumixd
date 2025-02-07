import logging
import os
from datetime import datetime
from typing import Dict, Any
from termcolor import cprint
from pathlib import Path

class PerformanceMonitor:
    def __init__(self):
        self.logger = self._setup_logger()
        self.metrics = {
            'trades_executed': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_volume': 0.0,
            'avg_execution_time': 0.0,
            'avg_slippage': 0.0
        }
        
    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger("performance")
        log_dir = Path("logs/performance")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(
            log_dir / f"metrics_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)
        return logger
        
    def log_trade_metrics(self, metrics: Dict[str, Any]):
        self.metrics['trades_executed'] += 1
        if metrics.get('success', False):
            self.metrics['successful_trades'] += 1
        else:
            self.metrics['failed_trades'] += 1
            
        self.metrics['total_volume'] += float(metrics.get('amount', 0))
        
        n = self.metrics['trades_executed']
        self.metrics['avg_execution_time'] = (
            (self.metrics['avg_execution_time'] * (n-1) + metrics.get('execution_time', 0)) / n
        )
        self.metrics['avg_slippage'] = (
            (self.metrics['avg_slippage'] * (n-1) + metrics.get('slippage', 0)) / n
        )
        
        self.logger.info(
            f"Trade Metrics: "
            f"token={metrics.get('token')}, "
            f"direction={metrics.get('direction')}, "
            f"amount={metrics.get('amount')} SOL, "
            f"execution_time={metrics.get('execution_time')}ms, "
            f"slippage={metrics.get('slippage')}%, "
            f"gas={metrics.get('gas_cost')} SOL"
        )
        
    def log_system_health(self, metrics: Dict[str, Any]):
        self.logger.info(
            f"System Health: "
            f"wallet_balance={metrics.get('wallet_balance')} SOL, "
            f"cpu_usage={metrics.get('cpu_usage')}%, "
            f"memory_usage={metrics.get('memory_usage')}%, "
            f"rpc_latency={metrics.get('rpc_latency')}ms"
        )
        
    def log_trading_interval(self, token: str, interval_seconds: int):
        self.logger.info(
            f"Trading Interval: "
            f"token={token}, "
            f"interval={interval_seconds}s"
        )
        
    def get_summary(self) -> Dict[str, Any]:
        success_rate = (
            self.metrics['successful_trades'] / self.metrics['trades_executed']
            if self.metrics['trades_executed'] > 0 else 0
        )
        
        return {
            'trades_executed': self.metrics['trades_executed'],
            'success_rate': f"{success_rate:.2%}",
            'total_volume': f"{self.metrics['total_volume']:.3f} SOL",
            'avg_execution_time': f"{self.metrics['avg_execution_time']:.0f}ms",
            'avg_slippage': f"{self.metrics['avg_slippage']:.2f}%"
        }
        
    def print_summary(self):
        summary = self.get_summary()
        cprint("\n📊 Performance Summary", "cyan")
        cprint(f"📈 Trades Executed: {summary['trades_executed']}", "cyan")
        cprint(f"✅ Success Rate: {summary['success_rate']}", "green")
        cprint(f"💰 Total Volume: {summary['total_volume']}", "yellow")
        cprint(f"⚡ Avg Execution Time: {summary['avg_execution_time']}", "magenta")
        cprint(f"📉 Avg Slippage: {summary['avg_slippage']}", "blue")
