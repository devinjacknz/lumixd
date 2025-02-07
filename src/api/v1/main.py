from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.v1.routes import trades, strategies, config, monitor

app = FastAPI(
    title="Lumix Trading API",
    description="Multi-agent trading system with custom strategy support",
    version="1.0.0"
)

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

@app.get("/")
async def root():
    return {"status": "ok", "message": "Lumix Trading API is running"}
