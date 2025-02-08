from pydantic import BaseModel

class InstanceTradeRequest(BaseModel):
    token: str
    amount_sol: float
