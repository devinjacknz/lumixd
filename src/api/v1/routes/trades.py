from fastapi import APIRouter, HTTPException
from typing import List, Optional
import os
from pydantic import BaseModel
from src.data.jupiter_client import JupiterClient
from src.monitoring.performance_monitor import PerformanceMonitor

router = APIRouter()
jupiter_client = JupiterClient()
performance_monitor = PerformanceMonitor()

class TradeRequest(BaseModel):
    input_token: str
    output_token: str
    amount_sol: float
    slippage_bps: Optional[int] = 250

class TradeResponse(BaseModel):
    transaction_signature: str
    input_amount: float
    output_amount: float
    price_impact: float

@router.post("/execute", response_model=TradeResponse)
async def execute_trade(trade: TradeRequest):
    try:
        amount_lamports = int(trade.amount_sol * 1e9)
        quote = jupiter_client.get_quote(
            trade.input_token,
            trade.output_token,
            str(amount_lamports),
            use_shared_accounts=True,
            force_simpler_route=True
        )
        if not quote:
            raise HTTPException(status_code=400, detail="Failed to get quote")
            
        signature = jupiter_client.execute_swap(
            quote,
            os.getenv("WALLET_ADDRESS"),
            use_shared_accounts=True
        )
        if not signature:
            raise HTTPException(status_code=400, detail="Failed to execute trade")
            
        return TradeResponse(
            transaction_signature=signature,
            input_amount=float(quote["inAmount"]) / 1e9,
            output_amount=float(quote["outAmount"]),
            price_impact=float(quote.get("priceImpactPct", 0))
        )
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
