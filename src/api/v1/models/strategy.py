from pydantic import BaseModel
from typing import Dict, Any, Optional

class Strategy(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    active: bool = True
    risk_level: Optional[int] = 1
    max_position_size: Optional[float] = 0.2
    stop_loss_percentage: Optional[float] = -0.05
    take_profit_percentage: Optional[float] = 0.1

def apply_strategy_parameters(trade_request, strategy):
    if "slippage_bps" in strategy.parameters:
        trade_request.slippage_bps = strategy.parameters["slippage_bps"]
    if "max_retries" in strategy.parameters:
        trade_request.max_retries = strategy.parameters["max_retries"]
    if "use_shared_accounts" in strategy.parameters:
        trade_request.use_shared_accounts = strategy.parameters["use_shared_accounts"]
    if "force_simpler_route" in strategy.parameters:
        trade_request.force_simpler_route = strategy.parameters["force_simpler_route"]
    return trade_request
