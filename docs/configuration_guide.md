# Configuration Guide / 配置指南

## Environment Setup / 环境设置

### Prerequisites / 前置要求
- Python 3.12+ / Python 3.12或更高版本
- Node.js 18+ / Node.js 18或更高版本
- Git / Git版本控制

### Installation / 安装
```bash
git clone https://github.com/kwannz/lumixd.git
cd lumixd
pip install -r requirements.txt
```

### Environment Variables / 环境变量
Create `.env` file / 创建 `.env` 文件:
```bash
SOLANA_PRIVATE_KEY=your_private_key
WALLET_ADDRESS=your_wallet_address
RPC_ENDPOINT=your_chainstack_endpoint
```

## Trading Configuration / 交易配置

### Token Settings / 代币设置
```python
# src/config/trade_config.py
TRADE_CONFIG = {
    "AI16Z_TOKEN": "HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC",
    "SOL_TOKEN": "So11111111111111111111111111111111111111112",
    "TRADE_AMOUNT_SOL": 0.001,  # Trade size / 交易数量
    "MAX_RETRIES": 3,           # Max retry attempts / 最大重试次数
    "RETRY_DELAY": 5,           # Retry delay in seconds / 重试延迟（秒）
    "SLIPPAGE_BPS": 250,        # 2.5% slippage / 2.5%滑点
}
```

### Trading Parameters / 交易参数
- Trading Interval: 15 minutes / 交易间隔：15分钟
- Verification Duration: 2 hours / 验证持续时间：2小时
- Default Trade Size: 0.001 SOL / 默认交易数量：0.001 SOL

## Logging / 日志记录
Logs are stored in `logs/trades_YYYYMMDD.log` / 日志存储在 `logs/trades_YYYYMMDD.log`

### Log Format / 日志格式
```
TIMESTAMP - LEVEL - MESSAGE
Example / 示例:
2025-02-07 21:36:52,143 - INFO - Executing trade 1 of 2 for 0.001 SOL
```

## Error Handling / 错误处理
- Failed trades are automatically retried / 失败的交易自动重试
- Maximum 3 retry attempts / 最多重试3次
- 5-second delay between retries / 重试间隔5秒

## System Verification / 系统验证
1. Check environment setup / 检查环境设置:
   ```bash
   python src/scripts/verify_env.py
   ```

2. Verify wallet balance / 验证钱包余额:
   ```bash
   python src/scripts/check_wallet.py
   ```

3. Start trading verification / 开始交易验证:
   ```bash
   python src/scripts/verify_trading.py
   ```

## Transaction Monitoring / 交易监控
- View transactions on Solscan / 在Solscan上查看交易:
  https://solscan.io/account/[WALLET_ADDRESS]
- Check logs for trade status / 检查日志了解交易状态:
  ```bash
  tail -f logs/trades_YYYYMMDD.log
  ```
