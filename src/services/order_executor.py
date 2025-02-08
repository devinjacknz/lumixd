"""
Order Execution Handler for Trading System
"""
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from termcolor import cprint
from src.data.jupiter_client import JupiterClient
from src.data.price_tracker import PriceTracker
from src.services.order_manager import OrderManager

class OrderExecutor:
    def __init__(self):
        """Initialize order executor with required components"""
        self.jupiter_client = JupiterClient()
        self.price_tracker = PriceTracker()
        self.order_manager = OrderManager()
        
    async def execute_order(self, order_id: str) -> bool:
        """Execute order based on type"""
        order = await self.order_manager.get_order(order_id)
        if not order or order['status'] != 'pending':
            return False
            
        try:
            if order['type'] == 'immediate':
                return await self.execute_immediate_order(order)
            elif order['type'] == 'timed':
                return await self.execute_timed_order(order)
            elif order['type'] == 'conditional':
                return await self.execute_conditional_order(order)
            return False
        except Exception as e:
            cprint(f"❌ Order execution failed: {str(e)}", "red")
            return False
            
    async def execute_immediate_order(self, order: Dict[str, Any]) -> bool:
        """Execute immediate full position buy order"""
        try:
            # Get quote for full position
            quote = self.jupiter_client.get_quote(
                input_mint=self.jupiter_client.sol_token,
                output_mint=order['token'],
                amount=str(int(float(os.getenv("MAX_TRADE_SIZE_SOL", "10.0")) * 1e9))
            )
            
            if not quote:
                return False
                
            # Execute swap
            signature = self.jupiter_client.execute_swap(
                quote_response=quote,
                wallet_pubkey=os.getenv("WALLET_ADDRESS", ""),
                use_shared_accounts=True
            )
            
            if signature:
                await self.order_manager.update_order_status(
                    order['id'],
                    'executed',
                    {'signature': signature}
                )
                return True
            return False
        except Exception as e:
            cprint(f"❌ Immediate order execution failed: {str(e)}", "red")
            return False
            
    async def execute_timed_order(self, order: Dict[str, Any]) -> bool:
        """Execute timed half position sell order"""
        try:
            # Get current position size
            position_size = await self.order_manager.get_position_size(
                order['instance_id'],
                order['token']
            )
            
            if position_size <= 0:
                return False
                
            # Calculate sell amount (half position)
            sell_amount = position_size * order['position_size']  # 0.5 for half position
            
            # Get quote for sell
            quote = self.jupiter_client.get_quote(
                input_mint=order['token'],
                output_mint=self.jupiter_client.sol_token,
                amount=str(int(sell_amount * 1e9))
            )
            
            if not quote:
                return False
                
            # Execute swap
            signature = self.jupiter_client.execute_swap(
                quote_response=quote,
                wallet_pubkey=os.getenv("WALLET_ADDRESS", ""),
                use_shared_accounts=True
            )
            
            if signature:
                await self.order_manager.update_order_status(
                    order['id'],
                    'executed',
                    {'signature': signature}
                )
                return True
            return False
        except Exception as e:
            cprint(f"❌ Timed order execution failed: {str(e)}", "red")
            return False
            
    async def execute_conditional_order(self, order: Dict[str, Any]) -> bool:
        """Execute conditional order based on price movement"""
        try:
            # Check price condition
            current_price = await self.price_tracker.get_price_change(
                order['token'],
                order['entry_price']
            )
            
            condition_met = False
            if order['condition']['type'] == 'above_entry' and current_price > 0:
                condition_met = True
            elif order['condition']['type'] == 'below_entry' and current_price < 0:
                condition_met = True
                
            if not condition_met:
                await self.order_manager.update_order_status(
                    order['id'],
                    'cancelled',
                    {'reason': 'condition_not_met'}
                )
                return False
                
            # Execute trade based on direction
            if order['direction'] == 'sell':
                position_size = await self.order_manager.get_position_size(
                    order['instance_id'],
                    order['token']
                )
                if position_size <= 0:
                    return False
                    
                sell_amount = position_size * order['position_size']
            else:  # buy
                buy_amount = float(order.get('amount', 10.0))  # Default to 10u if not specified
                
            # Get quote
            quote = self.jupiter_client.get_quote(
                input_mint=order['token'] if order['direction'] == 'sell' else self.jupiter_client.sol_token,
                output_mint=self.jupiter_client.sol_token if order['direction'] == 'sell' else order['token'],
                amount=str(int((sell_amount if order['direction'] == 'sell' else buy_amount) * 1e9))
            )
            
            if not quote:
                return False
                
            # Execute swap
            signature = self.jupiter_client.execute_swap(
                quote_response=quote,
                wallet_pubkey=os.getenv("WALLET_ADDRESS", ""),
                use_shared_accounts=True
            )
            
            if signature:
                await self.order_manager.update_order_status(
                    order['id'],
                    'executed',
                    {'signature': signature}
                )
                return True
            return False
        except Exception as e:
            cprint(f"❌ Conditional order execution failed: {str(e)}", "red")
            return False
