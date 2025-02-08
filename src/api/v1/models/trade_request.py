from pydantic import BaseModel, Field
from typing import Optional

class TradeRequest(BaseModel):
    input_token: str = Field(..., description="Input token address")
    output_token: str = Field(..., description="Output token address")
    amount_sol: float = Field(..., description="Amount in SOL")
    slippage_bps: int = Field(default=250, description="Slippage in basis points")
    use_shared_accounts: bool = Field(default=True, description="Use shared accounts")
    force_simpler_route: bool = Field(default=True, description="Force simpler route")
    dynamic_compute_unit_limit: bool = Field(default=True, description="Use dynamic compute unit limit")
    priority_level: Optional[str] = Field(default=None, description="Priority level for transaction")
