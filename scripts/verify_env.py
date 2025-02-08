"""
Verify environment variables are set correctly
"""
import os
from dotenv import load_dotenv
from termcolor import cprint

def verify_environment():
    """Verify all required environment variables are set"""
    load_dotenv()
    
    required_vars = {
        'HELIUS_API_KEY': 'Helius API key for RPC access',
        'SOLANA_PRIVATE_KEY': 'Solana wallet private key',
        'DEEPSEEK_API_KEY': 'DeepSeek API key for NLP processing',
        'CHAINSTACK_API_KEY': 'Chainstack API key for WebSocket',
        'DEEPSEEK_API_URL': 'DeepSeek API endpoint',
        'CHAINSTACK_WS_ENDPOINT': 'Chainstack WebSocket endpoint',
        'RPC_ENDPOINT': 'RPC endpoint for Solana',
        'MONGODB_URI': 'MongoDB connection URI',
        'MONGODB_DB': 'MongoDB database name',
        'SCHEDULER_TIMEZONE': 'Scheduler timezone (should be UTC)'
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"{var} ({description})")
    
    if missing_vars:
        cprint("❌ Missing required environment variables:", "red")
        for var in missing_vars:
            cprint(f"  - {var}", "red")
        return False
    
    # Verify specific values
    scheduler_tz = os.getenv('SCHEDULER_TIMEZONE')
    if scheduler_tz != 'UTC':
        cprint("❌ SCHEDULER_TIMEZONE must be set to UTC", "red")
        return False
    
    cprint("✅ All required environment variables are set", "green")
    return True

if __name__ == '__main__':
    verify_environment()
