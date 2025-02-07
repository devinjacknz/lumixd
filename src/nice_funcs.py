from typing import Optional
import os
import time
from termcolor import cprint
from solders.keypair import Keypair
from src.data.jupiter_client import JupiterClient

def fetch_wallet_holdings_og(wallet_address: str):
    """Fetch wallet holdings"""
    try:
        return []
    except Exception as e:
        cprint(f"❌ Failed to fetch wallet holdings: {str(e)}", "red")
        return []

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
