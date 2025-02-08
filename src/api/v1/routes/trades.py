from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional, Dict
import os
import time
from pydantic import BaseModel
from src.utils.env import get_env_var
from src.data.jupiter_client import JupiterClient
from src.monitoring.performance_monitor import PerformanceMonitor
from src.api.v1.models.strategy import Strategy, apply_strategy_parameters
from src.api.v1.routes.strategies import strategies_db
from src.services.logging_service import logging_service

# Bilingual error messages
ERROR_MESSAGES: Dict[str, Dict[str, str]] = {
    'strategy_inactive': {
        'en': 'Strategy is not active',
        'zh': '策略未激活'
    },
    'quote_failed': {
        'en': 'Failed to get quote',
        'zh': '获取报价失败'
    },
    'trade_failed': {
        'en': 'Failed to execute trade',
        'zh': '执行交易失败'
    },
    'insufficient_balance': {
        'en': 'Insufficient balance for trade',
        'zh': '余额不足以执行交易'
    },
    'invalid_token': {
        'en': 'Invalid token address or symbol',
        'zh': '无效的代币地址或符号'
    },
    'max_retries_exceeded': {
        'en': 'Failed after maximum retries',
        'zh': '超过最大重试次数'
    }
}

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
async def execute_trade(trade: TradeRequest, request: Request):
    try:
        # Log trade attempt
        await logging_service.log_trade_attempt(
            str(trade.dict()),
            request.headers.get('X-User-ID', 'anonymous')
        )
        
        if trade.strategy_id and trade.strategy_id in strategies_db:
            strategy = strategies_db[trade.strategy_id]
            if not strategy.active:
                error_msg = ERROR_MESSAGES['strategy_inactive']
                await logging_service.log_error(
                    f"{error_msg['zh']} | {error_msg['en']}",
                    {'strategy_id': trade.strategy_id},
                    request.headers.get('X-User-ID', 'anonymous')
                )
                raise HTTPException(status_code=400, detail=f"{error_msg['zh']} | {error_msg['en']}")
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
                    error_msg = ERROR_MESSAGES['quote_failed']
                    raise HTTPException(status_code=400, detail=f"{error_msg['zh']} | {error_msg['en']}")
                    
                signature = jupiter_client.execute_swap(
                    quote,
                    get_env_var("WALLET_ADDRESS"),
                    use_shared_accounts=trade.use_shared_accounts
                )
                if not signature:
                    error_msg = ERROR_MESSAGES['trade_failed']
                    await logging_service.log_error(
                        f"{error_msg['zh']} | {error_msg['en']}",
                        {'trade': trade.dict()},
                        request.headers.get('X-User-ID', 'anonymous')
                    )
                    raise HTTPException(status_code=400, detail=f"{error_msg['zh']} | {error_msg['en']}")
                    
                # Log trade success
                await logging_service.log_trade_result({
                    "status": "success",
                    "token": trade.output_token,
                    "amount": trade.amount_sol,
                    "execution_time": time.time(),
                    "slippage": float(quote.get("priceImpactPct", 0)),
                    "transaction_signature": signature,
                    "message": "交易成功 | Trade successful"
                })
                
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
                
                # Log trade error
                await logging_service.log_error(
                    str(e),
                    {
                        'trade': trade.dict(),
                        'retry_count': retries,
                        'error_type': type(e).__name__
                    },
                    request.headers.get('X-User-ID', 'anonymous')
                )
                
                if retries < trade.max_retries:
                    time.sleep(2 ** retries)  # Exponential backoff
                    
        # Log final failure
        error_msg = ERROR_MESSAGES['max_retries_exceeded']
        await logging_service.log_error(
            f"{error_msg['zh']} | {error_msg['en']}",
            {
                'trade': trade.dict(),
                'final_error': last_error,
                'total_retries': trade.max_retries
            },
            request.headers.get('X-User-ID', 'anonymous')
        )
        raise HTTPException(status_code=500, detail=f"{error_msg['zh']} | {error_msg['en']}: {last_error}")
    except Exception as e:
        # Log unexpected error
        error_msg = f"错误 | Error: {str(e)}"
        await logging_service.log_error(
            error_msg,
            {
                'trade': trade.dict(),
                'error_type': type(e).__name__
            },
            request.headers.get('X-User-ID', 'anonymous')
        )
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/history")
async def get_trade_history():
    return performance_monitor.get_summary()

@router.get("/status")
async def get_trade_status():
    return {
        "active": True,
        "metrics": performance_monitor.metrics
    }
