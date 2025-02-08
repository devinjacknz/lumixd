"""
Order Manager Service
Handles order creation, tracking, and execution using MongoDB
"""
import os
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from motor.motor_asyncio import AsyncIOMotorClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from termcolor import cprint
from src.data.jupiter_client import JupiterClient
from src.data.chainstack_client import ChainStackClient
from src.data.price_tracker import PriceTracker

class OrderManager:
    def __init__(self):
        """Initialize OrderManager with MongoDB connection"""
        try:
            # Initialize MongoDB connection
            self.client = AsyncIOMotorClient(
                os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
                serverSelectionTimeoutMS=5000
            )
            self.db = self.client[os.getenv("MONGODB_DB", "lumixd")]
            self.orders = self.db.orders
            self.positions = self.db.positions
            
            # Create indexes
            asyncio.create_task(self._create_indexes())
            
            # Initialize trading components
            self.jupiter_client = JupiterClient()
            self.chainstack_client = ChainStackClient()
            
            # Initialize tracked tokens set
            self._tracked_tokens = set()
            
            # Initialize scheduler for timed orders
            self.scheduler = AsyncIOScheduler(timezone="UTC")
            print("✅ OrderManager initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize OrderManager: {str(e)}")
            raise
            
    async def _create_indexes(self):
        """Create MongoDB indexes"""
        try:
            await self.orders.create_index([("status", 1)])
            await self.orders.create_index([("execute_at", 1)])
            await self.orders.create_index([("instance_id", 1)])
            await self.positions.create_index([("instance_id", 1)])
            await self.positions.create_index([("token", 1)])
            print("✅ MongoDB indexes created")
        except Exception as e:
            print(f"❌ Failed to create MongoDB indexes: {str(e)}")
            raise
        
    async def start(self):
        """Start the order manager"""
        if not self.scheduler.running:
            self.scheduler.start()
            await self.recover_pending_orders()
        
    async def update_order_status(self, order_id: str, status: str, details: Optional[Dict[str, Any]] = None) -> bool:
        """Update order status with optional details"""
        try:
            update = {'$set': {'status': status}}
            if details:
                update['$set'].update(details)
            result = await self.orders.update_one({'id': order_id}, update)
            return result.modified_count > 0
        except Exception as e:
            cprint(f"❌ Failed to update order status: {str(e)}", "red")
            return False
            
    async def get_tracked_tokens(self) -> List[str]:
        """Get list of tracked token addresses"""
        try:
            cursor = self.orders.distinct('token')
            tokens = await cursor
            return list(set(tokens) | self._tracked_tokens)
        except Exception as e:
            cprint(f"❌ Failed to get tracked tokens: {str(e)}", "red")
            return []
        
    async def create_immediate_order(self, instance_id: str, token: str, 
                                   position_size: float = 1.0, amount: Optional[float] = None) -> str:
        """Create immediate full position buy order"""
        order_id = str(uuid.uuid4())
        
        if amount is None:
            amount = float(os.getenv("MAX_TRADE_SIZE_SOL", "10.0"))
        
        order = {
            'id': order_id,
            'instance_id': instance_id,
            'type': 'immediate',
            'token': token,
            'direction': 'buy',
            'position_size': position_size,
            'amount': amount,
            'status': 'pending',
            'created_at': datetime.utcnow(),
            'execute_at': datetime.utcnow()
        }
        
        await self.orders.insert_one(order)
        # Execute immediately
        await self.execute_order(order_id)
        return order_id
        
    async def create_timed_order(self, instance_id: str, token: str,
                               direction: str, position_size: float,
                               delay_minutes: int) -> str:
        """Create timed order with specified delay"""
        order_id = str(uuid.uuid4())
        execute_at = datetime.utcnow() + timedelta(minutes=delay_minutes)
        
        order = {
            'id': order_id,
            'instance_id': instance_id,
            'type': 'timed',
            'token': token,
            'direction': direction,
            'position_size': position_size,
            'status': 'pending',
            'created_at': datetime.utcnow(),
            'execute_at': execute_at
        }
        
        await self.orders.insert_one(order)
        
        # Schedule execution
        self.scheduler.add_job(
            self.execute_order,
            'date',
            run_date=execute_at,
            args=[order_id]
        )
        return order_id
        
    async def create_conditional_order(self, instance_id: str, token: str,
                                     direction: str, position_size: float,
                                     delay_minutes: int, condition: Dict[str, Any],
                                     entry_price: float) -> str:
        """Create conditional order based on price movement"""
        order_id = str(uuid.uuid4())
        execute_at = datetime.utcnow() + timedelta(minutes=delay_minutes)
        
        order = {
            'id': order_id,
            'instance_id': instance_id,
            'type': 'conditional',
            'token': token,
            'direction': direction,
            'position_size': position_size,
            'status': 'pending',
            'created_at': datetime.utcnow(),
            'execute_at': execute_at,
            'condition': condition,
            'entry_price': entry_price
        }
        
        await self.orders.insert_one(order)
        
        # Schedule condition check
        self.scheduler.add_job(
            self.check_conditional_order,
            'date',
            run_date=execute_at,
            args=[order_id]
        )
        return order_id
        
    async def execute_order(self, order_id: str) -> bool:
        """Execute a pending order"""
        order = await self.orders.find_one({'id': order_id})
        if not order or order['status'] != 'pending':
            return False
            
        try:
            # Get current position for partial sells
            current_position = await self.positions.find_one({
                'instance_id': order['instance_id'],
                'token': order['token']
            })
            
            if order['direction'] == 'sell' and not current_position:
                cprint(f"❌ No position found for order {order_id}", "red")
                return False
                
            # Calculate trade amount
            trade_amount = 0
            if order['direction'] == 'sell':
                position_amount = float(current_position['amount'])
                trade_amount = position_amount * order['position_size']
            else:
                trade_amount = float(order.get('amount', os.getenv("MAX_TRADE_SIZE_SOL", "10.0")))
                
            # Execute trade
            # Get quote first
            quote = self.jupiter_client.get_quote(
                input_mint=order['token'] if order['direction'] == 'sell' else self.jupiter_client.sol_token,
                output_mint=self.jupiter_client.sol_token if order['direction'] == 'sell' else order['token'],
                amount=str(int(trade_amount * 1e9))  # Convert to lamports
            )
            
            if not quote:
                cprint("❌ Failed to get quote", "red")
                return False
                
            # Execute swap
            signature = self.jupiter_client.execute_swap(
                quote_response=quote,
                wallet_pubkey=os.getenv("WALLET_ADDRESS", ""),
                use_shared_accounts=True
            )
            
            if signature:
                await self.orders.update_one(
                    {'id': order_id},
                    {'$set': {
                        'status': 'executed',
                        'executed_at': datetime.utcnow(),
                        'signature': signature
                    }}
                )
                return True
                
            return False
        except Exception as e:
            cprint(f"❌ Error executing order {order_id}: {str(e)}", "red")
            return False
            
    async def check_conditional_order(self, order_id: str) -> None:
        """Check and execute conditional order if conditions are met"""
        order = await self.orders.find_one({'id': order_id})
        if not order or order['status'] != 'pending':
            return
            
        try:
            # Get current price using Jupiter quote
            quote = self.jupiter_client.get_quote(
                input_mint=self.jupiter_client.sol_token,
                output_mint=order['token'],
                amount="1000000000"  # 1 SOL in lamports
            )
            
            if not quote:
                cprint("❌ Failed to get price quote", "red")
                return
                
            # Calculate price from quote (outAmount in lamports)
            out_amount = float(quote.get('outAmount', 0))
            current_price = out_amount / 1e9  # Convert from lamports to SOL
            price_change = (current_price - order['entry_price']) / order['entry_price']
            
            condition_met = False
            if order['condition']['type'] == 'above_entry' and price_change > 0:
                condition_met = True
            elif order['condition']['type'] == 'below_entry' and price_change < 0:
                condition_met = True
                
            if condition_met:
                await self.execute_order(order_id)
            else:
                # Update order status to cancelled if condition not met
                await self.orders.update_one(
                    {'id': order_id},
                    {'$set': {
                        'status': 'cancelled',
                        'cancelled_at': datetime.utcnow(),
                        'reason': 'condition_not_met'
                    }}
                )
        except Exception as e:
            cprint(f"❌ Error checking conditional order {order_id}: {str(e)}", "red")
            
    async def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order details by ID"""
        return await self.orders.find_one({'id': order_id})
        
    async def get_pending_orders(self) -> List[Dict]:
        """Get all pending orders"""
        cursor = self.orders.find({'status': 'pending'})
        return await cursor.to_list(length=None)
        
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order"""
        result = await self.orders.update_one(
            {'id': order_id, 'status': 'pending'},
            {'$set': {
                'status': 'cancelled',
                'cancelled_at': datetime.utcnow(),
                'reason': 'user_cancelled'
            }}
        )
        return result.modified_count > 0
        
    async def recover_pending_orders(self) -> None:
        """Recover pending orders after system restart"""
        try:
            # Get all pending orders
            pending_orders = await self.get_pending_orders()
            recovered_count = 0
            
            for order in pending_orders:
                # Skip orders that should have executed while system was down
                if order['execute_at'] <= datetime.utcnow():
                    await self.update_order_status(
                        order['id'],
                        'cancelled',
                        {'reason': 'system_restart_missed_execution'}
                    )
                    continue
                    
                # Reschedule order execution
                if order['type'] == 'conditional':
                    self.scheduler.add_job(
                        self.check_conditional_order,
                        'date',
                        run_date=order['execute_at'],
                        args=[order['id']],
                        id=f"conditional_{order['id']}"
                    )
                else:
                    self.scheduler.add_job(
                        self.execute_order,
                        'date',
                        run_date=order['execute_at'],
                        args=[order['id']],
                        id=f"timed_{order['id']}"
                    )
                recovered_count += 1
                
            cprint(f"✅ Recovered {recovered_count} pending orders", "green")
            
            # Update positions from blockchain
            await self._sync_positions()
            
        except Exception as e:
            cprint(f"❌ Order recovery failed: {str(e)}", "red")
            
    async def _sync_positions(self) -> None:
        """Sync positions with blockchain state"""
        try:
            wallet_address = os.getenv("WALLET_ADDRESS")
            if not wallet_address:
                return
                
            # Clear existing positions
            await self.positions.delete_many({})
            
            # Get token balances from chain
            tokens = await self.get_tracked_tokens()
            for token in tokens:
                balance = await self.chainstack_client.get_token_balance(token, wallet_address)
                if balance and float(balance) > 0:
                    await self.positions.insert_one({
                        'instance_id': 'system',
                        'token': token,
                        'amount': float(balance),
                        'updated_at': datetime.utcnow()
                    })
                    
            cprint("✅ Positions synced with blockchain", "green")
        except Exception as e:
            cprint(f"❌ Position sync failed: {str(e)}", "red")
