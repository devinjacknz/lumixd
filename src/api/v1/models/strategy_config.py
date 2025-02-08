from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class StrategyConfig(BaseModel):
    name: str = Field(..., description="Strategy name")
    description: str = Field(..., description="Strategy description")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Strategy parameters including max_position_size, stop_loss, take_profit"
    )
    active: bool = Field(default=True, description="Whether the strategy is active")
    
class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None
