# Trading System Documentation / 交易系统文档

## Configuration / 配置
- `TRADE_AMOUNT_SOL`: Trade size in SOL / SOL交易数量
- `MAX_RETRIES`: Maximum retry attempts for failed trades / 失败交易重试最大次数
- `RETRY_DELAY`: Delay between retries in seconds / 重试间隔时间（秒）
- `SLIPPAGE_BPS`: Slippage tolerance in basis points / 滑点容忍度（基点）

## Environment Setup / 环境设置
1. Install dependencies / 安装依赖:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment variables / 配置环境变量:
   - `SOLANA_PRIVATE_KEY`: Wallet private key / 钱包私钥
   - `RPC_ENDPOINT`: Solana RPC endpoint / Solana RPC节点地址

## Usage / 使用方法
Execute trades / 执行交易:
```bash
python src/scripts/execute_trades.py
```

## Logging / 日志
- Trade execution logs are stored in `logs/trades_YYYYMMDD.log` / 交易执行日志存储在 `logs/trades_YYYYMMDD.log`
- Each log entry includes timestamp, level, and detailed message / 每个日志条目包含时间戳、级别和详细信息
- Both successful and failed trades are logged / 成功和失败的交易都会被记录

## Trading Parameters / 交易参数
- Default trade size: 0.001 SOL / 默认交易数量：0.001 SOL
- Slippage tolerance: 2.5% / 滑点容忍度：2.5%
- Maximum retry attempts: 3 / 最大重试次数：3
- Retry delay: 5 seconds / 重试延迟：5秒

## Error Handling / 错误处理
- Failed trades are automatically retried / 失败的交易会自动重试
- Detailed error messages are logged / 详细的错误信息会被记录
- System maintains stability through proper error recovery / 系统通过适当的错误恢复保持稳定性
