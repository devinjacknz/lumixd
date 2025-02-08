from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime

class InstanceMetrics(BaseModel):
    total_trades: int = 0
    successful_trades: int = 0
    total_volume: float = 0.0
    profit_loss: float = 0.0
    last_trade_time: Optional[datetime] = None
    last_trade_status: Optional[str] = None
    wallet_balance: Optional[float] = None
    active_trades: int = 0

class TradingInstance(BaseModel):
    id: str
    name: str
    description: str
    strategy_id: str
    tokens: List[str]
    amount_sol: float
    active: bool = True
    created_at: datetime = datetime.now()
    last_trade_time: Optional[datetime] = None
    parameters: Dict[str, Any] = {
        "slippage_bps": 250,
        "max_retries": 3,
        "use_shared_accounts": True,
        "force_simpler_route": True
    }
    performance: Dict[str, Any] = {
        "total_trades": 0,
        "successful_trades": 0,
        "total_volume": 0.0,
        "profit_loss": 0.0
    }
    metrics: Optional[InstanceMetrics] = None

class TradingInstanceCreate(BaseModel):
    name: str
    description: str
    strategy_id: str
    tokens: List[str]
    amount_sol: float
    parameters: Optional[Dict[str, Any]] = None

class TradingInstanceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    strategy_id: Optional[str] = None
    tokens: Optional[List[str]] = None
    amount_sol: Optional[float] = None
    active: Optional[bool] = None
    parameters: Optional[Dict[str, Any]] = None
