from dotenv import load_dotenv
import os

load_dotenv()

print('HELIUS_API_KEY:', os.getenv('HELIUS_API_KEY'))
print('RPC_ENDPOINT:', os.getenv('RPC_ENDPOINT'))
print('DEEPSEEK_KEY:', os.getenv('DEEPSEEK_KEY'))
print('SOLANA_PRIVATE_KEY: [HIDDEN]' if os.getenv('SOLANA_PRIVATE_KEY') else 'SOLANA_PRIVATE_KEY: Not set')
