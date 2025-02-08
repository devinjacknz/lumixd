"""
System Monitoring Routes
"""
from fastapi import APIRouter, HTTPException
from typing import Dict
import psutil
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from src.data.chainstack_client import ChainStackClient
from src.data.jupiter_client import JupiterClient

router = APIRouter()
chainstack_client = ChainStackClient()
jupiter_client = JupiterClient()
executor = ThreadPoolExecutor(max_workers=4)

@router.post("/status")
async def get_system_status() -> Dict:
    """Get system status including market data and trading info"""
    try:
        # System metrics
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        # Check Chainstack connection
        chainstack_status = "ok"
        try:
            await chainstack_client.get_token_price("So11111111111111111111111111111111111111112")
        except Exception as e:
            chainstack_status = f"error: {str(e)}"
            
        # Check Jupiter connection
        jupiter_status = "ok"
        try:
            quote = await asyncio.get_event_loop().run_in_executor(
                executor,
                jupiter_client.get_quote,
                "So11111111111111111111111111111111111111112",  # input_mint
                "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # output_mint (USDC)
                "1000000000"  # amount (1 SOL)
            )
            if not quote:
                jupiter_status = "error: failed to get quote"
        except Exception as e:
            jupiter_status = f"error: {str(e)}"
            
        return {
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available": memory.available // (1024 * 1024)  # MB
            },
            "services": {
                "chainstack": chainstack_status,
                "jupiter": jupiter_status
            },
            "trading": {
                "active": True,
                "last_update": datetime.now().isoformat(),
                "success_rate": 100,
                "volume_24h": 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check() -> Dict:
    """Basic health check endpoint"""
    return {"status": "ok"}
