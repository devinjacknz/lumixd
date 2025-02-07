from fastapi import APIRouter
from src.monitoring.system_monitor import SystemMonitor
from src.monitoring.performance_monitor import PerformanceMonitor

router = APIRouter()
performance_monitor = PerformanceMonitor()
system_monitor = SystemMonitor(performance_monitor)

@router.get("/health")
async def get_health():
    try:
        health_data = system_monitor.check_system_health()
        if not health_data:
            raise HTTPException(status_code=500, detail="Failed to get system health data")
        return health_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance")
async def get_performance():
    try:
        return performance_monitor.get_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
