import os
import json
import base64
import asyncio
import aiohttp
from typing import Optional, Dict
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction
from solana.system_program import TransferParams, transfer
from solana.keypair import Keypair
from solana.publickey import PublicKey
from src.services.logging_service import logging_service

# Constants
SLIPPAGE_BPS = 250  # 2.5%
SOL_DECIMALS = 9
LAMPORTS_PER_SOL = 1_000_000_000  # 10^9
POSITION_SIZE = 5 * LAMPORTS_PER_SOL  # 5 SOL

# Token addresses
SOL_MINT = "So11111111111111111111111111111111111111112"
VINE_MINT = "6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump"
POOL_ADDRESS = "58fzJMbX5PatnfJPqWWsqkVFPRKptkbb5r2vCw4Qq3z9"

async def get_pool_info(client: AsyncClient) -> Optional[Dict]:
    """Get pool information"""
    try:
        print("\n🔍 获取池信息中... | Getting pool info...")
        response = await client.get_account_info(PublicKey(POOL_ADDRESS))
        if response["result"]["value"]:
            print("\n✅ 获取池信息成功 | Pool info received")
            return response["result"]["value"]
        return None
    except Exception as e:
        print(f"\n❌ 错误 | Error: {str(e)}")
        return None

async def get_quote(client: AsyncClient) -> Optional[Dict]:
    """Get quote for swap"""
    try:
        print("\n🔍 获取报价中... | Getting quote...")
        print(f"输入代币 | Input token: SOL ({SOL_MINT})")
        print(f"输出代币 | Output token: VINE ({VINE_MINT})")
        print(f"数量 | Amount: 5 SOL")
        print(f"滑点 | Slippage: {SLIPPAGE_BPS/100}%")
        
        # Get pool info first
        pool_info = await get_pool_info(client)
        if not pool_info:
            return None
            
        # Calculate expected output amount
        # This is a simplified calculation - in production you'd want to use the actual AMM formula
        response = await client.get_token_accounts_by_owner(
            PublicKey(POOL_ADDRESS),
            {"programId": PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")}
        )
        
        if response["result"]["value"]:
            print("\n✅ 获取报价成功 | Quote received")
            return {
                "pool": POOL_ADDRESS,
                "inputAmount": str(POSITION_SIZE),
                "minimumOutputAmount": str(int(POSITION_SIZE * 0.975))  # Account for slippage
            }
        return None
    except Exception as e:
        print(f"\n❌ 错误 | Error: {str(e)}")
        return None

async def execute_swap(client: AsyncClient, wallet_key: str, quote: Dict) -> Optional[str]:
    """Execute swap transaction"""
    try:
        if not quote:
            print("\n❌ 无报价信息 | No quote provided")
            return None
            
        print("\n🔄 执行交易中... | Executing swap...")
        
        # Create keypair from private key
        private_key = base64.b64decode(wallet_key)
        keypair = Keypair.from_secret_key(private_key)
        
        # Create transfer instruction
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=keypair.public_key,
                to_pubkey=PublicKey(POOL_ADDRESS),
                lamports=int(quote["inputAmount"])
            )
        )
        
        # Create transaction
        transaction = Transaction()
        transaction.add(transfer_ix)
        
        # Send transaction
        result = await client.send_transaction(
            transaction,
            keypair,
            opts={"skip_preflight": True}
        )
        
        if "result" in result:
            signature = result["result"]
            print(f"\n✅ 交易成功 | Trade successful")
            print(f"交易签名 | Transaction signature: {signature}")
            print(f"查看交易 | View transaction: https://solscan.io/tx/{signature}")
            return signature
            
        print(f"\n❌ 交易失败 | Trade failed: {json.dumps(result)}")
        return None
        
    except Exception as e:
        print(f"\n❌ 错误 | Error: {str(e)}")
        return None

async def execute_buy() -> None:
    """Execute buy trade for VINE token"""
    try:
        # Initialize Solana client
        client = AsyncClient("https://api.mainnet-beta.solana.com")
        
        # Get quote
        quote = await get_quote(client)
        if not quote:
            return
            
        # Get wallet key from environment
        wallet_key = os.getenv('WALLET_KEY')
        if not wallet_key:
            print("\n❌ 钱包密钥未设置 | Wallet key not set")
            return
            
        # Execute swap
        signature = await execute_swap(client, wallet_key, quote)
        
        if signature:
            await logging_service.log_user_action(
                'buy_executed',
                {
                    'token': 'VINE',
                    'amount': '5 SOL worth',
                    'signature': signature,
                    'status': 'success',
                    'quote': quote
                },
                'system'
            )
        else:
            await logging_service.log_error(
                "Trade execution failed",
                {
                    'input_mint': SOL_MINT,
                    'output_mint': VINE_MINT,
                    'amount': str(POSITION_SIZE),
                    'status': 'failed'
                },
                'system'
            )
            
        # Close client
        await client.close()
            
    except Exception as e:
        print(f"\n❌ 错误 | Error: {str(e)}")
        await logging_service.log_error(str(e), locals(), 'system')

async def main() -> None:
    """Main entry point"""
    try:
        await execute_buy()
    except KeyboardInterrupt:
        print("\n👋 退出程序 | Exiting program")
    except Exception as e:
        print(f"\n❌ 错误 | Error: {str(e)}")
        await logging_service.log_error(str(e), locals(), 'system')

if __name__ == "__main__":
    asyncio.run(main())
