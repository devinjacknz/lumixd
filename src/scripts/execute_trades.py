from src.nice_funcs import market_buy
from src.config import MIN_TRADE_SIZE_SOL
from src.data.jupiter_client import JupiterClient
from solders.keypair import Keypair
import time
import os
from termcolor import cprint

def execute_ai16z_trades():
    """Execute two small trades for AI16z token"""
    ai16z_address = 'HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC'
    trade_size = MIN_TRADE_SIZE_SOL  # 0.001 SOL
    
    for i in range(2):
        cprint(f'\n🔄 Executing trade {i+1} of 2 for {trade_size} SOL...', 'cyan')
        try:
            # Create token account if needed
            jupiter = JupiterClient()
            wallet_key = Keypair.from_base58_string(os.getenv("SOLANA_PRIVATE_KEY"))
            jupiter.create_token_account(ai16z_address, str(wallet_key.pubkey()))
            
            success = market_buy(ai16z_address, trade_size)
            if success:
                cprint(f'✅ Trade {i+1} completed successfully', 'green')
            else:
                cprint(f'❌ Trade {i+1} failed', 'red')
        except Exception as e:
            cprint(f'❌ Trade {i+1} failed: {str(e)}', 'red')
        time.sleep(2)  # Wait between trades

if __name__ == '__main__':
    execute_ai16z_trades()
