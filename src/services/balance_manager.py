from typing import Dict, Optional
from decimal import Decimal
from termcolor import cprint

class BalanceManager:
    def __init__(self):
        self.instance_allocations: Dict[str, Decimal] = {}
        self.min_allocation = Decimal('0.001')  # 0.1% minimum
        self.max_allocation = Decimal('0.5')    # 50% maximum per instance
        
    def allocate_balance(self, instance_id: str, percentage: Decimal) -> bool:
        if percentage < self.min_allocation:
            cprint(f"❌ Allocation too small: {percentage}", "red")
            return False
            
        if percentage > self.max_allocation:
            cprint(f"❌ Allocation too large: {percentage}", "red")
            return False
            
        total_allocated = sum(self.instance_allocations.values())
        if total_allocated + percentage > Decimal('1.0'):
            cprint(f"❌ Total allocation would exceed 100%: {(total_allocated + percentage) * 100}%", "red")
            return False
            
        self.instance_allocations[instance_id] = percentage
        return True
        
    def get_instance_allocation(self, instance_id: str) -> Decimal:
        return self.instance_allocations.get(instance_id, Decimal('0'))
        
    def update_allocation(self, instance_id: str, percentage: Decimal) -> bool:
        if instance_id not in self.instance_allocations:
            return False
            
        current = self.instance_allocations[instance_id]
        total_others = sum(alloc for id_, alloc in self.instance_allocations.items() if id_ != instance_id)
        
        if total_others + percentage > Decimal('1.0'):
            cprint(f"❌ Total allocation would exceed 100%: {(total_others + percentage) * 100}%", "red")
            return False
            
        if percentage < self.min_allocation or percentage > self.max_allocation:
            cprint(f"❌ Invalid allocation: {percentage}", "red")
            return False
            
        self.instance_allocations[instance_id] = percentage
        return True
        
    def remove_allocation(self, instance_id: str) -> bool:
        if instance_id not in self.instance_allocations:
            return False
        del self.instance_allocations[instance_id]
        return True
        
    def get_available_allocation(self) -> Decimal:
        total_allocated = sum(self.instance_allocations.values())
        return Decimal('1.0') - total_allocated
        
    def get_all_allocations(self) -> Dict[str, Decimal]:
        return dict(self.instance_allocations)
