from fastapi import APIRouter
from src.monitoring.system_monitor import SystemMonitor
from src.monitoring.performance_monitor import PerformanceMonitor

router = APIRouter()
performance_monitor = PerformanceMonitor()
system_monitor = SystemMonitor(performance_monitor)

@router.get("/health")
async def get_health():
    return system_monitor.check_system_health()

@router.get("/performance")
async def get_performance():
    return performance_monitor.get_summary()
