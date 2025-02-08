"""
Order Monitor for Trading System
Handles monitoring and execution of pending orders
"""
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from termcolor import cprint
from src.services.order_manager import OrderManager
from src.services.order_executor import OrderExecutor
from src.data.price_tracker import PriceTracker

class OrderMonitor:
    def __init__(self):
        """Initialize order monitor with required components"""
        self.order_manager = OrderManager()
        self.order_executor = OrderExecutor()
        self.price_tracker = PriceTracker()
        self._stop = False
        self._monitor_task = None
        
    async def start(self):
        """Start order monitoring"""
        self._stop = False
        self._monitor_task = asyncio.create_task(self._monitor_orders())
        await self.price_tracker.start()
        
    async def stop(self):
        """Stop order monitoring"""
        self._stop = True
        if self._monitor_task:
            self._monitor_task.cancel()
        await self.price_tracker.stop()
        
    async def _monitor_orders(self):
        """Monitor and execute pending orders"""
        while not self._stop:
            try:
                # Get all pending orders
                orders = await self.order_manager.get_pending_orders()
                
                for order in orders:
                    if order['status'] != 'pending':
                        continue
                        
                    # Check if it's time to execute
                    current_time = datetime.utcnow()
                    execute_at = order.get('execute_at')
                    
                    if not execute_at or current_time < execute_at:
                        continue
                        
                    if order['type'] == 'conditional':
                        await self._check_conditional_order(order)
                    else:
                        await self.order_executor.execute_order(order['id'])
                        
                # Sleep to prevent high CPU usage
                await asyncio.sleep(1)
                
            except Exception as e:
                cprint(f"❌ Order monitoring error: {str(e)}", "red")
                await asyncio.sleep(5)  # Sleep longer on error
                
    async def _check_conditional_order(self, order: Dict[str, Any]):
        """Check and execute conditional order if conditions are met"""
        try:
            # Get current price change
            price_change = await self.price_tracker.get_price_change(
                order['token'],
                order['entry_price']
            )
            
            condition_met = False
            if order['condition']['type'] == 'above_entry' and price_change > 0:
                condition_met = True
            elif order['condition']['type'] == 'below_entry' and price_change < 0:
                condition_met = True
                
            if condition_met:
                await self.order_executor.execute_order(order['id'])
            else:
                # Update order status if condition not met at execution time
                await self.order_manager.update_order_status(
                    order['id'],
                    'cancelled',
                    {'reason': 'condition_not_met'}
                )
                
        except Exception as e:
            cprint(f"❌ Conditional order check failed: {str(e)}", "red")
            
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get current order status with details"""
        order = await self.order_manager.get_order(order_id)
        if not order:
            return {
                'status': 'not_found',
                'message': {
                    'en': f'Order {order_id} not found',
                    'zh': f'未找到订单 {order_id}'
                }
            }
            
        status_messages = {
            'pending': {
                'en': 'Order is pending execution',
                'zh': '订单等待执行'
            },
            'executed': {
                'en': 'Order executed successfully',
                'zh': '订单执行成功'
            },
            'cancelled': {
                'en': 'Order was cancelled',
                'zh': '订单已取消'
            },
            'failed': {
                'en': 'Order execution failed',
                'zh': '订单执行失败'
            }
        }
        
        return {
            'status': order['status'],
            'order_type': order['type'],
            'execution_time': order.get('execute_at'),
            'message': status_messages.get(order['status'], {
                'en': 'Unknown status',
                'zh': '未知状态'
            })
        }
