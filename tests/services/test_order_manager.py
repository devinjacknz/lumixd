"""
Test OrderManager Service
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from src.services.order_manager import OrderManager

@pytest.fixture
async def order_manager():
    manager = OrderManager()
    yield manager
    # Cleanup after tests
    await manager.client.drop_database(manager.db.name)

@pytest.mark.asyncio
async def test_immediate_buy_order(order_manager):
    """Test immediate full position buy order"""
    order_id = await order_manager.create_immediate_order(
        instance_id="test_instance",
        token="6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump",
        position_size=1.0  # Full position
    )
    
    order = await order_manager.get_order(order_id)
    assert order is not None
    assert order['type'] == 'immediate'
    assert order['direction'] == 'buy'
    assert order['position_size'] == 1.0
    assert order['status'] in ['pending', 'executed']

@pytest.mark.asyncio
async def test_timed_sell_order(order_manager):
    """Test timed half position sell order"""
    order_id = await order_manager.create_timed_order(
        instance_id="test_instance",
        token="6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump",
        direction="sell",
        position_size=0.5,  # Half position
        delay_minutes=10
    )
    
    order = await order_manager.get_order(order_id)
    assert order is not None
    assert order['type'] == 'timed'
    assert order['direction'] == 'sell'
    assert order['position_size'] == 0.5
    assert order['status'] == 'pending'
    
    # Verify execution time
    expected_time = datetime.utcnow() + timedelta(minutes=10)
    assert abs((order['execute_at'] - expected_time).total_seconds()) < 5

@pytest.mark.asyncio
async def test_conditional_order(order_manager):
    """Test conditional order with price movement condition"""
    entry_price = 1.0
    order_id = await order_manager.create_conditional_order(
        instance_id="test_instance",
        token="6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump",
        direction="sell",
        position_size=0.5,
        delay_minutes=20,
        condition={'type': 'above_entry'},
        entry_price=entry_price
    )
    
    order = await order_manager.get_order(order_id)
    assert order is not None
    assert order['type'] == 'conditional'
    assert order['condition']['type'] == 'above_entry'
    assert order['entry_price'] == entry_price
    assert order['status'] == 'pending'

@pytest.mark.asyncio
async def test_prevent_duplicate_execution(order_manager):
    """Test prevention of duplicate order execution"""
    order_id = await order_manager.create_immediate_order(
        instance_id="test_instance",
        token="6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump",
        position_size=1.0
    )
    
    # Try to execute same order twice
    result1 = await order_manager.execute_order(order_id)
    result2 = await order_manager.execute_order(order_id)
    
    assert result1 != result2  # Second execution should fail
    
    order = await order_manager.get_order(order_id)
    assert order['status'] == 'executed'

@pytest.mark.asyncio
async def test_recover_pending_orders(order_manager):
    """Test recovery of pending orders after restart"""
    # Create a timed order
    order_id = await order_manager.create_timed_order(
        instance_id="test_instance",
        token="6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump",
        direction="sell",
        position_size=0.5,
        delay_minutes=10
    )
    
    # Simulate restart
    new_manager = OrderManager()
    await new_manager.recover_pending_orders()
    
    # Verify order was recovered
    order = await new_manager.get_order(order_id)
    assert order is not None
    assert order['status'] == 'pending'
    
    # Cleanup
    await new_manager.client.drop_database(new_manager.db.name)
