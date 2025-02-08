from typing import Dict, Any
from pathlib import Path

# Trading Settings / 交易设置
TRADING_CONFIG: Dict[str, Any] = {
    "tokens": {
        "AI16Z": "HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC",
        "SWARM": "GHoewwgqzpyr4honfYZXDjWVqEQf4UVnNkbzqpqzwxPr",
        "SOL": "So11111111111111111111111111111111111111112"
    },
    "trade_parameters": {
        "amount_sol": 0.001,  # 0.001 SOL per trade
        "interval_minutes": 15,  # 15-minute trading interval
        "verification_hours": 2,  # 2-hour verification duration
        "slippage_bps": 250,  # 2.5% slippage for optimal execution
        "max_retries": 3,  # Maximum retry attempts
        "retry_delay_seconds": 5  # Delay between retries
    },
    "risk_parameters": {
        "max_loss_percentage": 2.0,  # Maximum loss per trade
        "min_liquidity_score": 0.5,  # Minimum liquidity requirement
        "max_contract_risk": 0.7,  # Maximum contract risk score
        "position_size_limit": 0.20,  # Maximum position size (20%)
        "cash_buffer": 0.30  # Minimum cash buffer (30%)
    },
    "rpc_endpoints": {
        "primary": None,  # Set via RPC_ENDPOINT environment variable
        "fallback": "https://api.mainnet-beta.solana.com"
    },
    "chainstack": {
        "use_enhanced_rpc": True,
        "websocket_enabled": True,
        "cache_duration": 300,
        "retry_attempts": 3,
        "timeout": 30,
        "batch_size": 100
    },
    "monitoring": {
        "min_sol_balance": 0.05,  # Minimum SOL balance
        "alert_on_failure": True,  # Alert on trade failures
        "max_consecutive_failures": 3,  # Maximum consecutive failures
        "health_check_interval": 15  # Health check interval (minutes)
    }
}

# Environment Variables / 环境变量
REQUIRED_ENV_VARS = [
    "SOLANA_PRIVATE_KEY",
    "WALLET_ADDRESS",
    "RPC_ENDPOINT"
]
