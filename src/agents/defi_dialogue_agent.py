"""
Solana DeFi Dialogue Agent
Handles user interactions, token analysis, and trading strategy generation
"""

import os
import json
from typing import Dict, Any, Optional
from src.models.deepseek_model import DeepSeekModel
from src.data.jupiter_client_v2 import JupiterClientV2
from src.services.logging_service import logging_service

class DefiDialogueAgent:
    """Manages dialogue flow for Solana DeFi trading"""
    
    def __init__(self):
        self.model = DeepSeekModel(model_name="deepseek-r1:1.5b")
        self.jupiter_client = JupiterClientV2()
        self.context = {}
        
    async def process_user_input(self, user_input: str, user_id: str) -> Dict[str, Any]:
        """Process user input and generate appropriate response"""
        try:
            # Log user input
            await logging_service.log_user_action(
                'user_input',
                {'input': user_input},
                user_id
            )
            
            # Generate NLP response
            response = self.model.generate_response(
                system_prompt="""你是一个专业的Solana生态DeFi交易助手。
                1. 帮助用户分析代币信息
                2. 制定交易策略
                3. 执行确认的交易
                请保持专业和谨慎的态度。""",
                user_content=user_input
            )
            
            # Parse response
            parsed = json.loads(response.content)
            
            # Update context based on response type
            if parsed.get('type') == 'token_info':
                self.context['token'] = parsed.get('token_data', {})
            elif parsed.get('type') == 'strategy':
                self.context['strategy'] = parsed.get('strategy_data', {})
            
            return {
                'status': 'success',
                'response': parsed,
                'requires_confirmation': parsed.get('type') == 'strategy',
                'context': self.context
            }
            
        except Exception as e:
            await logging_service.log_error(str(e), {'input': user_input}, user_id)
            return {
                'status': 'error',
                'message': f'处理错误 | Processing error: {str(e)}'
            }
    
    async def execute_trade(self, wallet_key: str, user_id: str) -> Dict[str, Any]:
        """Execute trade based on confirmed strategy"""
        try:
            if not self.context.get('strategy'):
                return {
                    'status': 'error',
                    'message': '没有确认的交易策略 | No confirmed trading strategy'
                }
            
            strategy = self.context['strategy']
            
            # Get quote
            quote = await self.jupiter_client.get_quote(
                input_mint=strategy['input_token'],
                output_mint=strategy['output_token'],
                amount=strategy['amount']
            )
            
            if not quote:
                return {
                    'status': 'error',
                    'message': '无法获取报价 | Failed to get quote'
                }
            
            # Execute swap
            result = await self.jupiter_client.execute_swap(quote, wallet_key)
            if result:
                response_data = {
                    'status': 'success',
                    'transaction': result,
                    'solscan_url': f"https://solscan.io/tx/{result}"
                }
                await logging_service.log_trade_result(response_data, user_id)
                return response_data
            
            return {
                'status': 'error',
                'message': '交易执行失败 | Trade execution failed'
            }
            
        except Exception as e:
            await logging_service.log_error(str(e), {'context': self.context}, user_id)
            return {
                'status': 'error',
                'message': f'交易错误 | Trading error: {str(e)}'
            }
    
    def clear_context(self):
        """Clear the current dialogue context"""
        self.context = {}
