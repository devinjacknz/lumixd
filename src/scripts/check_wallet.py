from src.nice_funcs import fetch_wallet_holdings_og
import os
from termcolor import cprint

def check_wallet_status():
    """Check wallet holdings and token balances"""
    try:
        print('\nChecking wallet holdings...')
        holdings = fetch_wallet_holdings_og(os.getenv('WALLET_ADDRESS'))
        print(holdings)
        
        if holdings.empty:
            cprint("❌ No token holdings found", "red")
        else:
            cprint(f"✅ Found {len(holdings)} token holdings", "green")
            print("\nToken Balances:")
            for _, row in holdings.iterrows():
                print(f"{row['Mint Address']}: {row['Amount']} (${row['USD Value']:.2f})")
                
    except Exception as e:
        cprint(f"❌ Error checking wallet: {str(e)}", "red")

if __name__ == "__main__":
    check_wallet_status()
