from decimal import Decimal
from typing import Dict, Any, List
import os
from pathlib import Path

TEST_CONFIG = {
    'duration_hours': 2,
    'instances': [
        {
            'name': 'SOL-AI16z Instance',
            'tokens': ['SOL', 'AI16z'],
            'amount_sol': Decimal('0.0001'),
            'allocation': Decimal('0.1'),
            'parameters': {
                'slippage_bps': 250,
                'max_retries': 3,
                'use_shared_accounts': True,
                'force_simpler_route': True,
                'max_position_size': Decimal('0.2'),
                'stop_loss': Decimal('-0.05'),
                'take_profit': Decimal('0.1'),
                'cash_buffer': Decimal('0.3')
            }
        },
        {
            'name': 'SOL-SWARM Instance',
            'tokens': ['SOL', 'SWARM'],
            'amount_sol': Decimal('0.0001'),
            'allocation': Decimal('0.1'),
            'parameters': {
                'slippage_bps': 250,
                'max_retries': 3,
                'use_shared_accounts': True,
                'force_simpler_route': True,
                'max_position_size': Decimal('0.2'),
                'stop_loss': Decimal('-0.05'),
                'take_profit': Decimal('0.1'),
                'cash_buffer': Decimal('0.3')
            }
        }
    ],
    'trade_interval_seconds': 900,  # 15 minutes
    'performance_thresholds': {
        'min_success_rate': Decimal('0.95'),
        'max_rpc_latency_ms': 2000,
        'max_execution_time_ms': 5000,
        'max_slippage_bps': 300,
        'min_sol_balance': Decimal('0.05'),
        'max_cpu_usage': 80,
        'max_memory_usage': 80
    },
    'token_addresses': {
        'SOL': 'So11111111111111111111111111111111111111112',
        'AI16z': 'HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC',
        'SWARM': 'GHoewwgqzpyr4honfYZXDjWVqEQf4UVnNkbzqpqzwxPr'
    },
    'log_dir': str(Path('logs/performance')),
    'rpc_endpoint': os.getenv('RPC_ENDPOINT'),
    'wallet_address': os.getenv('WALLET_ADDRESS')
}
