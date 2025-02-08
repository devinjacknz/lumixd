from decimal import Decimal
from typing import Dict, Tuple
from .trading_instance import TradingInstance

MIN_TRADE_SIZE_SOL = Decimal('0.001')
MAX_TRADE_SIZE_SOL = Decimal('10.0')
MIN_ALLOCATION = Decimal('0.001')
MAX_ALLOCATION = Decimal('0.5')

class InstanceValidator:
    @staticmethod
    def validate_instance(instance: TradingInstance, instances_db: Dict[str, TradingInstance]) -> Tuple[bool, str]:
        try:
            # Validate trade size
            amount = Decimal(str(instance.amount_sol))
            if amount < MIN_TRADE_SIZE_SOL:
                return False, f"Trade size below minimum ({MIN_TRADE_SIZE_SOL} SOL)"
            if amount > MAX_TRADE_SIZE_SOL:
                return False, f"Trade size above maximum ({MAX_TRADE_SIZE_SOL} SOL)"
                
            # Validate allocation
            allocation = Decimal(str(instance.parameters.get("allocation", 0)))
            if allocation < MIN_ALLOCATION:
                return False, f"Allocation below minimum ({MIN_ALLOCATION})"
            if allocation > MAX_ALLOCATION:
                return False, f"Allocation above maximum ({MAX_ALLOCATION})"
                
            # Validate total allocation
            total_allocation = sum(
                Decimal(str(i.parameters.get("allocation", 0)))
                for i in instances_db.values()
                if i.id != instance.id
            )
            if total_allocation + allocation > Decimal('1.0'):
                return False, f"Total allocation would exceed 100%: {(total_allocation + allocation) * 100}%"
                
            # Validate tokens
            if not instance.tokens:
                return False, "No tokens specified for trading"
                
            return True, ""
        except Exception as e:
            return False, str(e)
