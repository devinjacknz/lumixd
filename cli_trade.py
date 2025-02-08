import os
import sys
import json
import asyncio
from datetime import datetime, timezone
from src.data.jupiter_client_v2 import jupiter_client_v2
from src.services.logging_service import logging_service
from src.models.deepseek_model import DeepSeekModel

class TradeDialogCLI:
    def __init__(self):
        self.deepseek = DeepSeekModel()
        self.wallet_key = os.getenv('WALLET_KEY')
        
    async def display_welcome(self):
        print("\n=== Solana DeFi Trading Agent ===")
        print("欢迎使用 Solana DeFi 交易代理 | Welcome to Solana DeFi Trading Agent")
        print("请输入您的交易指令 | Please enter your trading instruction")
        print("示例 | Example: 买入500个AI16z代币，滑点不超过2%")
        print("输入 'q' 退出 | Enter 'q' to quit\n")
        
    async def get_user_input(self):
        try:
            instruction = input(">>> ")
            if instruction.lower() in ['q', 'quit', 'exit']:
                print("再见! | Goodbye!")
                sys.exit(0)
            return instruction
        except KeyboardInterrupt:
            print("\n再见! | Goodbye!")
            sys.exit(0)
            
    async def analyze_instruction(self, instruction: str):
        """Analyze trading instruction using DeepSeek"""
        try:
            # Log user input
            await logging_service.log_user_action(
                'user_input',
                {'instruction': instruction},
                'system'
            )
            
            # Analyze trade
            analysis = await self.deepseek.analyze_trade(instruction)
            
            # Log the analysis
            await logging_service.log_user_action(
                'trade_analysis',
                {
                    'instruction': instruction,
                    'analysis': analysis
                },
                'system'
            )
            
            return analysis
            
        except Exception as e:
            error_msg = f"\n❌ 分析错误 | Analysis error: {str(e)}"
            print(error_msg)
            
            await logging_service.log_error(
                str(e),
                {
                    'instruction': instruction,
                    'error': str(e)
                },
                'system'
            )
            
            return {
                'error': str(e),
                'instruction': instruction
            }
        
    async def display_analysis(self, analysis: dict):
        """Display trade analysis in both languages"""
        if 'error' in analysis:
            print(f"\n❌ 分析错误 | Analysis error: {analysis['error']}")
            return False
            
        print("\n=== 交易分析 | Trade Analysis ===")
        print(f"交易类型 | Trade Type: {analysis.get('trade_type', 'Unknown')}")
        print(f"代币 | Token: {analysis.get('token', 'Unknown')}")
        print(f"数量 | Amount: {analysis.get('amount', 'Unknown')}")
        print(f"滑点设置 | Slippage: {analysis.get('slippage', '2.5')}%")
        
        if analysis.get('market_analysis'):
            print("\n市场分析 | Market Analysis:")
            market = analysis['market_analysis']
            print(f"价格趋势 | Price Trend: {market.get('price_trend', 'Unknown')}")
            print(f"流动性 | Liquidity: {market.get('liquidity', 'Unknown')}")
            print(f"波动性 | Volatility: {market.get('volatility', 'Unknown')}")
            
        print("\n交易详情 | Trade Details:")
        print(f"输入代币地址 | Input Token: {analysis.get('input_mint', 'Unknown')}")
        print(f"输出代币地址 | Output Token: {analysis.get('output_mint', 'Unknown')}")
        
        print("\n确认执行? (y/n) | Confirm execution? (y/n)")
        return True
        
    async def execute_trade(self, analysis: dict):
        """Execute trade after confirmation"""
        try:
            if 'error' in analysis:
                print(f"\n❌ 分析错误 | Analysis error: {analysis['error']}")
                return
                
            # Get quote
            quote = await jupiter_client_v2.get_quote(
                analysis['input_mint'],
                analysis['output_mint'],
                analysis['amount']
            )
            
            if not quote:
                print("\n❌ 获取报价失败 | Failed to get quote")
                return
                
            # Execute swap
            signature = await jupiter_client_v2.execute_swap(quote, self.wallet_key)
            
            if signature:
                print(f"\n✅ 交易成功 | Trade successful")
                print(f"交易签名 | Transaction signature: {signature}")
                print(f"查看交易 | View transaction: https://solscan.io/tx/{signature}")
                
                await logging_service.log_user_action(
                    'trade_execution',
                    {
                        'analysis': analysis,
                        'signature': signature,
                        'status': 'success',
                        'quote': quote
                    }
                )
            else:
                print("\n❌ 交易失败 | Trade failed")
                await logging_service.log_error(
                    "Trade execution failed",
                    {
                        'analysis': analysis,
                        'status': 'failed',
                        'quote': quote
                    }
                )
                
        except Exception as e:
            print(f"\n❌ 错误 | Error: {str(e)}")
            await logging_service.log_error(
                str(e),
                {
                    'analysis': analysis,
                    'status': 'error'
                }
            )
            
    async def run(self):
        """Main CLI loop"""
        await self.display_welcome()
        
        while True:
            instruction = await self.get_user_input()
            
            # Analyze instruction
            analysis = await self.analyze_instruction(instruction)
            
            # Display analysis and get confirmation
            await self.display_analysis(analysis)
            
            # Get confirmation
            confirm = input(">>> ").lower()
            if confirm in ['y', 'yes', '是']:
                await self.execute_trade(analysis)
            else:
                print("\n❌ 交易已取消 | Trade cancelled")
                
async def main():
    cli = TradeDialogCLI()
    await cli.run()
    
if __name__ == "__main__":
    asyncio.run(main())
