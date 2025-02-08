# Multi-Instance Trading Configuration Guide

## Overview
The Lumix Trading System supports running multiple trading instances simultaneously, each with its own:
- Trading strategy
- Token pairs
- Balance allocation
- Risk parameters

## Instance Limits
- Minimum allocation per instance: 0.1%
- Maximum allocation per instance: 50%
- Minimum trade size: 0.001 SOL
- Maximum trade size: 10 SOL
- API rate limit: 5 requests per second per instance

## Configuration Parameters
```json
{
  "slippage_bps": 250,      // 2.5% slippage
  "max_retries": 3,         // Maximum retry attempts
  "allocation": 0.1,        // Fund allocation (10%)
  "use_shared_accounts": true,
  "force_simpler_route": true
}
```

## API Endpoints

### Create Instance
```bash
curl -X POST "http://localhost:8000/api/v1/instances/create" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Instance 1",
    "description": "First trading instance",
    "strategy_id": "strategy_1",
    "tokens": ["SOL", "AI16z"],
    "amount_sol": 0.001,
    "parameters": {
      "allocation": 0.1,
      "slippage_bps": 250
    }
  }'
```

### List Instances
```bash
curl "http://localhost:8000/api/v1/instances/list"
```

### Get Instance Metrics
```bash
curl "http://localhost:8000/api/v1/instances/{instance_id}/metrics"
```

### Update Instance
```bash
curl -X PUT "http://localhost:8000/api/v1/instances/{instance_id}/update" \
  -H "Content-Type: application/json" \
  -d '{
    "active": true,
    "parameters": {
      "allocation": 0.2
    }
  }'
```

### Toggle Instance
```bash
curl -X POST "http://localhost:8000/api/v1/instances/{instance_id}/toggle"
```

## Instance Management
1. Balance Allocation
   - Total allocation across all instances cannot exceed 100%
   - Each instance maintains isolated balance tracking
   - Automatic validation of allocation limits

2. Performance Monitoring
   - Instance-specific metrics tracking
   - Real-time performance monitoring
   - Trade execution verification
   - Health checks and alerts

3. Risk Management
   - Per-instance position limits
   - Strategy-specific risk parameters
   - Automatic trade validation
   - Balance protection mechanisms

## System Requirements
- FastAPI server running on port 8000
- Chainstack RPC endpoint configured
- Sufficient SOL balance for all instances
- Proper environment variables set

## Important Notes
- Always verify instance creation with metrics endpoint
- Monitor total allocation across instances
- Keep track of individual instance performance
- Regularly check system health endpoints
- Maintain proper security practices
