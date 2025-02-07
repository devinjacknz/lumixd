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
        "amount_sol": 0.001,
        "interval_minutes": 15,
        "verification_hours": 2,
        "slippage_bps": 250,
        "max_retries": 3,
        "retry_delay_seconds": 5
    },
    "rpc_endpoints": {
        "primary": "https://solana-mainnet.core.chainstack.com/60d783949ddfbc48b7f1232aa308d7b8",
        "fallback": "https://api.mainnet-beta.solana.com"
    },
    "monitoring": {
        "min_sol_balance": 0.05,
        "alert_on_failure": True,
        "max_consecutive_failures": 3
    }
}

# Environment Variables / 环境变量
REQUIRED_ENV_VARS = [
    "SOLANA_PRIVATE_KEY",
    "WALLET_ADDRESS",
    "RPC_ENDPOINT"
]
