import json
from datetime import datetime, timedelta

class TradingStrategy:
    def __init__(self):
        self.token_address = "6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump"
        self.max_position_size = 10.0  # SOL
        self.slippage_bps = 250  # 2.5%
        self.entry_price = None
        self.position_size = 0

    def generate_orders(self):
        """Generate sequence of trading orders based on strategy"""
        try:
            orders = []
            
            # Order 1: Full position buy
            orders.append({
                "type": "immediate",
                "action": "buy",
                "token_address": self.token_address,
                "position_size": 1.0,
                "amount": self.max_position_size,
                "slippage_bps": self.slippage_bps
            })
            
            # Order 2: Timed half position sell
            orders.append({
                "type": "timed",
                "action": "sell",
                "token_address": self.token_address,
                "position_size": 0.5,
                "delay_minutes": 10,
                "slippage_bps": self.slippage_bps
            })
            
            # Order 3: Conditional order
            orders.append({
                "type": "conditional",
                "action": "sell",
                "token_address": self.token_address,
                "position_size": 1.0,
                "delay_minutes": 20,
                "condition": {
                    "type": "above_entry",
                    "action": "sell_remaining"
                },
                "alternative": {
                    "type": "below_entry",
                    "action": "buy",
                    "amount": 10.0
                },
                "slippage_bps": self.slippage_bps
            })
            
            return orders
        except Exception as e:
            print(f"❌ Order generation error: {str(e)}")
            return []

    def validate_order(self, order):
        """Validate order parameters"""
        try:
            assert order["token_address"] == self.token_address, "Invalid token address"
            assert 0 < order["position_size"] <= 1.0, "Invalid position size"
            if "amount" in order:
                assert 0 < order["amount"] <= self.max_position_size, "Invalid amount"
            if "delay_minutes" in order:
                assert 0 < order["delay_minutes"] <= 60, "Invalid delay"
            return True
        except Exception as e:
            print(f"❌ Order validation error: {str(e)}")
            return False

    def execute_strategy(self):
        """Execute the complete trading strategy"""
        try:
            orders = self.generate_orders()
            execution_plan = []
            
            for order in orders:
                if self.validate_order(order):
                    execution_time = datetime.now()
                    if "delay_minutes" in order:
                        execution_time += timedelta(minutes=order["delay_minutes"])
                    
                    execution_plan.append({
                        "order": order,
                        "execution_time": execution_time,
                        "status": "pending"
                    })
            
            return execution_plan
        except Exception as e:
            print(f"❌ Strategy execution error: {str(e)}")
            return []

    def __str__(self):
        return json.dumps({
            "token_address": self.token_address,
            "max_position_size": self.max_position_size,
            "slippage_bps": self.slippage_bps,
            "entry_price": self.entry_price,
            "position_size": self.position_size
        }, indent=2)
