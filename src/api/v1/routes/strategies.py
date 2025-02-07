from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

router = APIRouter()

class Strategy(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    active: bool = True

class StrategyCreate(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]

strategies_db: Dict[str, Strategy] = {}

@router.post("/create")
async def create_strategy(strategy: StrategyCreate):
    strategy_id = f"strategy_{len(strategies_db) + 1}"
    strategies_db[strategy_id] = Strategy(
        name=strategy.name,
        description=strategy.description,
        parameters=strategy.parameters
    )
    return {"id": strategy_id, "strategy": strategies_db[strategy_id]}

@router.get("/list")
async def list_strategies():
    return list(strategies_db.values())

@router.put("/{strategy_id}/update")
async def update_strategy(strategy_id: str, strategy: Strategy):
    if strategy_id not in strategies_db:
        raise HTTPException(status_code=404, detail="Strategy not found")
    strategies_db[strategy_id] = strategy
    return {"message": "Strategy updated", "strategy": strategy}

@router.post("/{strategy_id}/execute")
async def execute_strategy(strategy_id: str):
    if strategy_id not in strategies_db:
        raise HTTPException(status_code=404, detail="Strategy not found")
    strategy = strategies_db[strategy_id]
    if not strategy.active:
        raise HTTPException(status_code=400, detail="Strategy is not active")
    return {"message": f"Executing strategy: {strategy.name}"}
