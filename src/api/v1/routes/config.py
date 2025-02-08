from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from pydantic import BaseModel
from src.config.settings import TRADING_CONFIG

router = APIRouter()

class ConfigUpdate(BaseModel):
    trade_parameters: Dict[str, Any]
    risk_parameters: Dict[str, Any]
    monitoring: Dict[str, Any]

@router.get("")
async def get_config():
    return TRADING_CONFIG

@router.put("/update")
async def update_config(config: ConfigUpdate):
    try:
        TRADING_CONFIG["trade_parameters"].update(config.trade_parameters)
        TRADING_CONFIG["risk_parameters"].update(config.risk_parameters)
        TRADING_CONFIG["monitoring"].update(config.monitoring)
        return {"message": "Configuration updated", "config": TRADING_CONFIG}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
