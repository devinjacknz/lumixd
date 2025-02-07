from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.v1.routes import trades, strategies, config, monitor, instances
from src.api.v1.middleware.rate_limit import RateLimitMiddleware
from src.services.instance_manager import InstanceManager
from src.services.balance_manager import BalanceManager

app = FastAPI(
    title="Lumix Trading API",
    description="Multi-agent trading system with multiple trading instances and custom strategies",
    version="1.0.0"
)

# Initialize services
instance_manager = InstanceManager()
balance_manager = BalanceManager()

def get_instance_manager():
    return instance_manager

def get_balance_manager():
    return balance_manager

# Add dependencies to routes
app.dependency_overrides[instances.get_instance_manager] = get_instance_manager
app.dependency_overrides[instances.get_balance_manager] = get_balance_manager

app.add_middleware(RateLimitMiddleware, max_requests=5, window_seconds=1)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trades.router, prefix="/api/v1/trades", tags=["trades"])
app.include_router(strategies.router, prefix="/api/v1/strategies", tags=["strategies"])
app.include_router(config.router, prefix="/api/v1/config", tags=["config"])
app.include_router(monitor.router, prefix="/api/v1/monitor", tags=["monitor"])
app.include_router(instances.router, prefix="/api/v1/instances", tags=["instances"])

@app.get("/")
async def root():
    return {"status": "ok", "message": "Lumix Trading API is running"}
