from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
from datetime import datetime
from src.api.v1.models.trading_instance import (
    TradingInstance,
    TradingInstanceCreate,
    TradingInstanceUpdate
)
from src.api.v1.models.strategy import Strategy
from src.api.v1.routes.trades import TradeRequest
from src.api.v1.routes.strategies import strategies_db
from src.monitoring.performance_monitor import PerformanceMonitor
from src.services.instance_manager import InstanceManager

instance_manager = InstanceManager()

router = APIRouter()
instances_db: Dict[str, TradingInstance] = {}
performance_monitor = PerformanceMonitor()

@router.post("/create")
async def create_instance(instance: TradingInstanceCreate):
    if instance.strategy_id and instance.strategy_id not in strategies_db:
        raise HTTPException(status_code=404, detail="Strategy not found")
        
    instance_id = f"instance_{len(instances_db) + 1}"
    params = instance.parameters or {}
    params.update({
        "slippage_bps": params.get("slippage_bps", 250),
        "max_retries": params.get("max_retries", 3),
        "use_shared_accounts": params.get("use_shared_accounts", True),
        "force_simpler_route": params.get("force_simpler_route", True)
    })
    
    new_instance = TradingInstance(
        id=instance_id,
        name=instance.name,
        description=instance.description,
        strategy_id=instance.strategy_id,
        tokens=instance.tokens,
        amount_sol=instance.amount_sol,
        parameters=params)
    )
    
    if not instance_manager.create_instance(new_instance):
        raise HTTPException(status_code=500, detail="Failed to create trading instance")
        
    instances_db[instance_id] = new_instance
    return {
        "id": instance_id,
        "instance": new_instance,
        "message": "Trading instance created successfully"
    }

@router.get("/list", response_model=List[TradingInstance])
async def list_instances():
    instances = list(instances_db.values())
    for instance in instances:
        metrics = instance_manager.get_instance_metrics(instance.id)
        if metrics:
            instance.metrics = metrics
    return instances

@router.get("/{instance_id}")
async def get_instance(instance_id: str):
    if instance_id not in instances_db:
        raise HTTPException(status_code=404, detail="Trading instance not found")
    return instances_db[instance_id]

@router.put("/{instance_id}/update")
async def update_instance(instance_id: str, update: TradingInstanceUpdate):
    if instance_id not in instances_db:
        raise HTTPException(status_code=404, detail="Trading instance not found")
        
    instance = instances_db[instance_id]
    update_data = update.dict(exclude_unset=True)
    
    if "strategy_id" in update_data:
        if update_data["strategy_id"] not in strategies_db:
            raise HTTPException(status_code=404, detail="Strategy not found")
            
    if not instance_manager.update_instance(instance_id, instance):
        raise HTTPException(status_code=500, detail="Failed to update trading instance")
    
    for field, value in update_data.items():
        setattr(instance, field, value)
        
    instances_db[instance_id] = instance
    return {
        "message": "Instance updated successfully",
        "instance": instance,
        "metrics": instance_manager.get_instance_metrics(instance_id)
    }

@router.post("/{instance_id}/toggle")
async def toggle_instance(instance_id: str):
    if instance_id not in instances_db:
        raise HTTPException(status_code=404, detail="Trading instance not found")
        
    instance = instances_db[instance_id]
    agent = instance_manager.get_agent(instance_id)
    if not agent:
        raise HTTPException(status_code=500, detail="Trading agent not found")
        
    instance.active = agent.toggle_active()
    instances_db[instance_id] = instance
    
    return {
        "message": f"Instance {'activated' if instance.active else 'deactivated'}",
        "instance": instance
    }

@router.post("/{instance_id}/trade")
async def execute_instance_trade(instance_id: str, trade: TradeRequest):
    if instance_id not in instances_db:
        raise HTTPException(status_code=404, detail="Instance not found")
        
    instance = instances_db[instance_id]
    if not instance.active:
        raise HTTPException(status_code=400, detail="Instance not active")
        
    agent = instance_manager.get_agent(instance_id)
    if not agent:
        raise HTTPException(status_code=500, detail="Trading agent not found")
        
    try:
        result = await agent.execute_trade(
            token=trade.token,
            direction=trade.direction,
            amount=trade.amount_sol,
            instance_config=instance.parameters
        )
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{instance_id}/metrics")
async def get_instance_metrics(instance_id: str):
    if instance_id not in instances_db:
        raise HTTPException(status_code=404, detail="Instance not found")
        
    metrics = instance_manager.get_instance_metrics(instance_id)
    if not metrics:
        raise HTTPException(status_code=500, detail="Failed to get instance metrics")
        
    return metrics

@router.get("/{instance_id}/performance")
async def get_instance_performance(instance_id: str):
    if instance_id not in instances_db:
        raise HTTPException(status_code=404, detail="Trading instance not found")
        
    instance = instances_db[instance_id]
    metrics = instance_manager.get_instance_metrics(instance_id)
    if not metrics:
        raise HTTPException(status_code=500, detail="Failed to get instance metrics")
        
    return {
        "instance_id": instance_id,
        "instance": instance,
        "metrics": metrics,
        "performance": performance_monitor.get_instance_metrics(instance_id)
    }
