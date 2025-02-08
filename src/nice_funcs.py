from typing import Optional
import os
import time
from termcolor import cprint
from solders.keypair import Keypair
from src.data.jupiter_client import JupiterClient

def fetch_wallet_holdings_og(wallet_address: str):
    """Fetch wallet holdings"""
    try:
        import pandas as pd
        return pd.DataFrame(columns=['Mint Address', 'Amount', 'USD Value'])
    except Exception as e:
        cprint(f"❌ Failed to fetch wallet holdings: {str(e)}", "red")
        return pd.DataFrame(columns=['Mint Address', 'Amount', 'USD Value'])

def market_buy(token_address: str, amount: str) -> bool:
    """Execute a market buy order"""
    try:
        wallet_pubkey = os.getenv("WALLET_ADDRESS")
        if not wallet_pubkey:
            cprint("❌ WALLET_ADDRESS environment variable not set", "red")
            return False

        jupiter = JupiterClient()
        quote = jupiter.get_quote(
            input_mint="So11111111111111111111111111111111111111112",
            output_mint=token_address,
            amount=amount
        )
        
        if not quote:
            cprint("❌ Failed to get quote", "red")
            return False
            
        tx = jupiter.execute_swap(quote, wallet_pubkey)
        if not tx:
            cprint("❌ Market buy failed", "red")
            return False
            
        return True
    except Exception as e:
        cprint(f"❌ Market buy failed: {str(e)}", "red")
        return False

def market_sell(token_address: str, amount: str) -> bool:
    """Execute a market sell order"""
    try:
        wallet_pubkey = os.getenv("WALLET_ADDRESS")
        if not wallet_pubkey:
            cprint("❌ WALLET_ADDRESS environment variable not set", "red")
            return False

        jupiter = JupiterClient()
        quote = jupiter.get_quote(
            input_mint=token_address,
            output_mint="So11111111111111111111111111111111111111112",
            amount=amount
        )
        
        if not quote:
            cprint("❌ Failed to get quote", "red")
            return False
            
        tx = jupiter.execute_swap(quote, wallet_pubkey)
        if not tx:
            cprint("❌ Market sell failed", "red")
            return False
            
        return True
    except Exception as e:
        cprint(f"❌ Market sell failed: {str(e)}", "red")
        return False

def calculate_atr(high_prices: list, low_prices: list, close_prices: list, period: int = 14) -> float:
    if len(high_prices) < 2 or len(low_prices) < 2 or len(close_prices) < 2:
        return 0.0
        
    tr_values = []
    for i in range(1, len(close_prices)):
        tr1 = high_prices[i] - low_prices[i]
        tr2 = abs(high_prices[i] - close_prices[i-1])
        tr3 = abs(low_prices[i] - close_prices[i-1])
        tr_values.append(max(tr1, tr2, tr3))
        
    return sum(tr_values[-period:]) / min(period, len(tr_values)) if tr_values else 0.0
