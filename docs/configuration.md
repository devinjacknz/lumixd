# Configuration Guide / 配置指南

## Environment Setup / 环境设置

### Required Environment Variables / 必需的环境变量
- `SOLANA_PRIVATE_KEY`: Wallet private key / 钱包私钥
- `WALLET_ADDRESS`: Solana wallet address / Solana钱包地址
- `RPC_ENDPOINT`: Primary RPC endpoint / 主要RPC节点

### Trading Parameters / 交易参数
- Trade Amount: 0.001 SOL / 交易数量：0.001 SOL
  - Small transaction size for testing / 用于测试的小额交易
  - Configurable in settings.py / 可在settings.py中配置

- Trading Interval: 15 minutes / 交易间隔：15分钟
  - Allows market stabilization / 允许市场稳定
  - Reduces network congestion / 减少网络拥堵

- Verification Duration: 2 hours / 验证持续时间：2小时
  - Sufficient time for multiple trades / 足够进行多次交易
  - Tests system stability / 测试系统稳定性

- Slippage Tolerance: 2.5% / 滑点容忍度：2.5%
  - Optimal for current market conditions / 适合当前市场条件
  - Balances execution speed and price impact / 平衡执行速度和价格影响

### RPC Configuration / RPC配置
- Primary Endpoint / 主要节点: 
  - Provider: Chainstack / 提供商：Chainstack
  - Endpoint: https://solana-mainnet.core.chainstack.com/[YOUR-KEY]
  - High reliability and performance / 高可靠性和性能

- Fallback Endpoint / 备用节点:
  - Provider: Solana Mainnet / 提供商：Solana主网
  - Endpoint: https://api.mainnet-beta.solana.com
  - Used when primary is unavailable / 主节点不可用时使用

### Monitoring Settings / 监控设置
- Minimum SOL Balance: 0.05 SOL / 最小SOL余额：0.05 SOL
  - Ensures sufficient funds for trades / 确保有足够资金进行交易
  - Includes buffer for transaction fees / 包含交易费用缓冲

- Alert on Failure / 失败时报警
  - Enabled by default / 默认启用
  - Logs all failures / 记录所有失败
  - Helps track system health / 帮助跟踪系统健康状况

- Max Consecutive Failures: 3 / 最大连续失败次数：3
  - Prevents continuous failed attempts / 防止持续失败尝试
  - Protects system stability / 保护系统稳定性

## Token Configuration / 代币配置
### AI16z Token / AI16z代币
- Address: HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC
- Primary trading target / 主要交易目标
- Uses Raydium liquidity pools / 使用Raydium流动性池

### SWARM Token / SWARM代币
- Address: GHoewwgqzpyr4honfYZXDjWVqEQf4UVnNkbzqpqzwxPr
- Secondary trading target / 次要交易目标
- Uses Jupiter aggregator for best routes / 使用Jupiter聚合器获取最佳路由

### SOL Token / SOL代币
- Address: So11111111111111111111111111111111111111112
- Base currency for all trades / 所有交易的基础货币
- Native blockchain token / 原生区块链代币

## Error Handling / 错误处理
- Automatic retry on failure / 失败时自动重试
- Maximum 3 retry attempts / 最多重试3次
- 5-second delay between retries / 重试间隔5秒
- Detailed error logging / 详细的错误日志记录

## Logging System / 日志系统
- Location: logs/trades_YYYYMMDD.log / 位置：logs/trades_YYYYMMDD.log
- Includes timestamps / 包含时间戳
- Records all trade attempts / 记录所有交易尝试
- Tracks success/failure status / 跟踪成功/失败状态

## System Requirements / 系统要求
- Python 3.12+ / Python 3.12或更高版本
- Required packages in requirements.txt / 所需包在requirements.txt中
- Minimum 0.1 SOL for trading / 最少0.1 SOL用于交易
- Stable internet connection / 稳定的网络连接
