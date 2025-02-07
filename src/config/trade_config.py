from decimal import Decimal

# Trading parameters
USDC_SIZE = Decimal('10.0')  # Default trade size in USDC
SLIPPAGE = 250  # Default slippage (2.5%)
STOP_LOSS_PERCENTAGE = Decimal('-0.05')  # Default stop loss (-5%)
MAX_LOSS_PERCENTAGE = Decimal('-0.10')  # Maximum loss (-10%)
MAX_RETRIES = 3  # Maximum retry attempts
TRADE_INTERVAL = 900  # 15 minutes in seconds
MIN_SOL_BALANCE = Decimal('0.05')  # Minimum SOL balance
MIN_USDC_BALANCE = Decimal('10.0')  # Minimum USDC balance
MIN_TRADE_SIZE_SOL = Decimal('0.001')  # Minimum trade size
MAX_ORDER_SIZE_SOL = Decimal('10.0')  # Maximum order size
CREATE_ATA_IF_MISSING = True  # Create Associated Token Account if missing

# Token addresses
USDC_ADDRESS = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
SOL_ADDRESS = "So11111111111111111111111111111111111111112"
AI16Z_ADDRESS = "HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC"
SWARM_ADDRESS = "SWMGqHJzXPxrG2oJvK2RVtP4rsi5j6xpqEzNvY7Hae8"

# System parameters
MAX_CONCURRENT_TRADES = 5
MAX_POSITION_SIZE = Decimal('0.2')  # 20% of total balance
CASH_BUFFER = Decimal('0.3')  # 30% cash buffer
USE_SOL_FOR_TRADING = True  # Use SOL instead of USDC for trading
