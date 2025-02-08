"""
Derive Solana wallet address from private key
"""
from solders.keypair import Keypair
from solders.pubkey import Pubkey
import os
from dotenv import load_dotenv

def derive_wallet_address():
    """Derive wallet address from private key in environment"""
    load_dotenv()
    
    # Get private key from environment
    private_key = os.getenv('SOLANA_PRIVATE_KEY')
    if not private_key:
        print('SOLANA_PRIVATE_KEY not found in environment')
        return None
        
    try:
        # Convert to bytes and create keypair
        keypair = Keypair.from_bytes(bytes.fromhex(private_key))
        return str(keypair.pubkey())
    except Exception as e:
        print(f'Error deriving wallet address: {e}')
        return None

if __name__ == '__main__':
    wallet_address = derive_wallet_address()
    if wallet_address:
        print(f'Derived wallet address: {wallet_address}')
