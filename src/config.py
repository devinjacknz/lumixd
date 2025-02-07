"""
Lumix Trading System Configuration
"""

from src.config.settings import TRADING_CONFIG

# Token Addresses
USDC_ADDRESS = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC token address
SOL_ADDRESS = TRADING_CONFIG["tokens"]["SOL"]
AI16Z_ADDRESS = TRADING_CONFIG["tokens"]["AI16Z"]
SWARM_ADDRESS = TRADING_CONFIG["tokens"]["SWARM"]

# Trading Exclusions
EXCLUDED_TOKENS = [USDC_ADDRESS, SOL_ADDRESS]

# Token List for Trading
MONITORED_TOKENS = [
    AI16Z_ADDRESS,
    SWARM_ADDRESS
]

# Trading Parameters
TRADING_INTERVAL = TRADING_CONFIG["trade_parameters"]["interval_minutes"]
MIN_TRADE_SIZE_SOL = TRADING_CONFIG["trade_parameters"]["amount_sol"]
MAX_ORDER_SIZE_SOL = MIN_TRADE_SIZE_SOL * 10
SLIPPAGE = TRADING_CONFIG["trade_parameters"]["slippage_bps"]
PRIORITY_FEE = 100000
MAX_RETRIES = TRADING_CONFIG["trade_parameters"]["max_retries"]
USE_SOL_FOR_TRADING = True

# Risk Management Settings
MIN_SOL_BALANCE = TRADING_CONFIG["monitoring"]["min_sol_balance"]
MIN_USDC_BALANCE = 1.0
CREATE_ATA_IF_MISSING = True
CASH_PERCENTAGE = TRADING_CONFIG["risk_parameters"]["cash_buffer"] * 100
MAX_POSITION_PERCENTAGE = TRADING_CONFIG["risk_parameters"]["position_size_limit"] * 100
MAX_LOSS_PERCENTAGE = TRADING_CONFIG["risk_parameters"]["max_loss_percentage"]

# Trading Monitoring
VERIFICATION_HOURS = TRADING_CONFIG["trade_parameters"]["verification_hours"]
HEALTH_CHECK_INTERVAL = TRADING_CONFIG["monitoring"]["health_check_interval"]

# Market Data Configuration
TIMEFRAME = '15m'
LOOKBACK_DAYS = 3
MIN_VOLUME_24H = 1000
MIN_LIQUIDITY = 5000

# AI Model Settings
AI_MODEL = "deepseek-r1:1.5b"
AI_MAX_TOKENS = 1024
AI_TEMPERATURE = 0.7

# RPC Configuration
RPC_ENDPOINTS = {
    "primary": os.getenv("RPC_ENDPOINT"),
    "fallback": TRADING_CONFIG["rpc_endpoints"]["fallback"]
}
