from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import os
import time
from pydantic import BaseModel
from src.utils.env import get_env_var
from src.data.jupiter_client import JupiterClient
from src.monitoring.performance_monitor import PerformanceMonitor
from src.api.v1.models.strategy import Strategy, apply_strategy_parameters
from src.api.v1.routes.strategies import strategies_db

router = APIRouter()
jupiter_client = JupiterClient()
performance_monitor = PerformanceMonitor()

class TradeRequest(BaseModel):
    input_token: str
    output_token: str
    amount_sol: float
    slippage_bps: int = 250
    strategy_id: str | None = None
    max_retries: int = 3
    use_shared_accounts: bool = True
    force_simpler_route: bool = True

class TradeResponse(BaseModel):
    transaction_signature: str
    input_amount: float
    output_amount: float
    price_impact: float

@router.post("/execute", response_model=TradeResponse)
async def execute_trade(trade: TradeRequest):
    try:
        if trade.strategy_id and trade.strategy_id in strategies_db:
            strategy = strategies_db[trade.strategy_id]
            if not strategy.active:
                raise HTTPException(status_code=400, detail="Strategy is not active")
            trade = apply_strategy_parameters(trade, strategy)
            
        amount_lamports = int(trade.amount_sol * 1e9)
        retries = 0
        last_error = None
        
        while retries < trade.max_retries:
            try:
                quote = jupiter_client.get_quote(
                    trade.input_token,
                    trade.output_token,
                    str(amount_lamports),
                    use_shared_accounts=trade.use_shared_accounts,
                    force_simpler_route=trade.force_simpler_route
                )
                if not quote:
                    raise HTTPException(status_code=400, detail="Failed to get quote")
                    
                signature = jupiter_client.execute_swap(
                    quote,
                    get_env_var("WALLET_ADDRESS"),
                    use_shared_accounts=trade.use_shared_accounts
                )
                if not signature:
                    raise HTTPException(status_code=400, detail="Failed to execute trade")
                    
                performance_monitor.log_trade_metrics({
                    "success": True,
                    "token": trade.output_token,
                    "amount": trade.amount_sol,
                    "execution_time": time.time(),
                    "slippage": float(quote.get("priceImpactPct", 0))
                })
                    
                return TradeResponse(
                    transaction_signature=signature,
                    input_amount=float(quote["inAmount"]) / 1e9,
                    output_amount=float(quote["outAmount"]),
                    price_impact=float(quote.get("priceImpactPct", 0))
                )
            except Exception as e:
                last_error = str(e)
                retries += 1
                if retries < trade.max_retries:
                    time.sleep(2 ** retries)  # Exponential backoff
                    
        raise HTTPException(status_code=500, detail=f"Failed after {trade.max_retries} retries: {last_error}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_trade_history():
    return performance_monitor.get_summary()

@router.get("/status")
async def get_trade_status():
    return {
        "active": True,
        "metrics": performance_monitor.metrics
    }
