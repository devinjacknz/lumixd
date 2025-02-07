from datetime import datetime, timedelta

# Market data configuration
LOOKBACK_DAYS = 7
TIMEFRAME = "1h"  # 1h, 4h, 1d
SAVE_MARKET_DATA = True

# Trading pairs
TRADING_PAIRS = [
    "SOL/USDC",
    "AI16z/SOL",
    "SWARM/SOL"
]

# Time windows
SENTIMENT_WINDOW = timedelta(hours=24)
PRICE_WINDOW = timedelta(hours=4)
VOLUME_WINDOW = timedelta(hours=12)

# Update intervals
DATA_UPDATE_INTERVAL = timedelta(minutes=15)
METRICS_UPDATE_INTERVAL = timedelta(minutes=5)
