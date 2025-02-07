# Lumix AI Trading System 🤖

A real-time trading system powered by Chainstack RPC and Jupiter V6 Swap API for Solana trading, with AI-driven decision making using the DeepSeek R1 1.5B model.

## System Requirements
- Python 3.12+
- Node.js 18+
- Linux/macOS (recommended)

## Environment Setup 环境设置

1. Clone the repository:
   ```bash
   git clone https://github.com/kwannz/lumixd.git
   cd lumixd
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   pip install twikit==2.3.2  # Required for Twitter sentiment analysis
   ```

3. Configure environment variables:
   ```bash
   cp .env_example .env
   ```
   Required variables:
   - `RPC_ENDPOINT`: Chainstack RPC endpoint (https://solana-mainnet.core.chainstack.com/YOUR_KEY)
     - Sign up at https://chainstack.com
     - Create a new Solana node
     - Copy the RPC endpoint URL
   - `SOLANA_PRIVATE_KEY`: Your Solana wallet private key (base58 format)
     - Ensure wallet has sufficient SOL for transaction fees
     - Minimum recommended balance: 0.1 SOL
   - `DEEPSEEK_KEY`: Required for AI model (obtain from DeepSeek dashboard)
   - `TWITTER_USERNAME`: Twitter account username for sentiment analysis
   - `TWITTER_PASSWORD`: Twitter account password
   - `TWITTER_EMAIL`: Twitter account email
     - Twitter credentials used for real-time sentiment analysis
     - Ensure account has API access enabled

4. Install and configure Ollama:
   ```bash
   # Install Ollama
   curl https://ollama.ai/install.sh | sh

   # Pull DeepSeek model
   ollama pull deepseek-r1:1.5b

   # Start Ollama server
   ollama serve
   ```
   The system will automatically connect to http://localhost:11434/api

## Running the System 运行系统

1. Verify environment setup:
   ```bash
   # Check environment configuration
   python src/scripts/verify_env.py
   
   # Ensure Ollama server is running
   curl http://localhost:11434/api/tags
   ```

2. Start the trading system:
   ```bash
   # Set Python path and start main system
   PYTHONPATH=/home/ubuntu/repos/lumixd python src/main.py
   ```

3. Monitor trading activity (in separate terminals):
   ```bash
   # Monitor real-time transactions
   PYTHONPATH=/home/ubuntu/repos/lumixd python src/scripts/monitor_trading.py

   # Verify trading correctness
   PYTHONPATH=/home/ubuntu/repos/lumixd python src/scripts/verify_trading.py
   ```

4. Verify system operation:
   - Check Solscan for transactions: https://solscan.io/account/4BKPzFyjBaRP3L1PNDf3xTerJmbbxxESmDmZJ2CZYdQ5
   - Monitor Twitter sentiment analysis output
   - Verify Chainstack RPC connectivity
   - Check agent status in logs

## Trading Parameters 交易参数

- Default slippage: 2.5% (可调整滑点)
- Maximum position size: 20% (最大仓位)
- Cash buffer: 30% (现金缓冲)
- Stop loss: -5% (止损)
- Rate limits: 1 request per second (RPC限制)

## Monitoring System 监控系统

1. Transaction Verification 交易验证
   - View transactions on Solscan: https://solscan.io/account/4BKPzFyjBaRP3L1PNDf3xTerJmbbxxESmDmZJ2CZYdQ5
   - Check transaction status and fees
   - Verify Jupiter swaps execution

2. Log Monitoring 日志监控
   - Real-time transaction monitoring in terminal
   - Error tracking and retry status
   - Trading performance metrics

3. Agent Status 代理状态
   - Trading agent activity and decisions
   - Risk management checks
   - Position tracking and PnL

## Troubleshooting 故障排除

1. RPC Connection Issues:
   - Verify RPC_ENDPOINT in .env
   - Check Chainstack dashboard for rate limits
   - Ensure proper API authentication

2. Trading Errors:
   - Check SOL balance for transaction fees
   - Verify slippage settings
   - Monitor Jupiter API status

3. AI Model Issues:
   - Ensure Ollama server is running
   - Check DEEPSEEK_KEY configuration
   - Monitor model response times

## License
MIT License

## API Documentation / API文档

### Trading API / 交易API
- POST /api/v1/trades/execute - Execute trade / 执行交易
- GET /api/v1/trades/history - Get trade history / 获取交易历史
- GET /api/v1/trades/status - Get trading status / 获取交易状态

### Strategy API / 策略API
- POST /api/v1/strategies/create - Create custom strategy / 创建自定义策略
- GET /api/v1/strategies/list - List all strategies / 列出所有策略
- PUT /api/v1/strategies/{id}/update - Update strategy / 更新策略
- POST /api/v1/strategies/{id}/execute - Execute strategy / 执行策略

### Configuration API / 配置API
- GET /api/v1/config - Get system config / 获取系统配置
- PUT /api/v1/config/update - Update config / 更新配置

### Monitoring API / 监控API
- GET /api/v1/monitor/health - System health / 系统健康
- GET /api/v1/monitor/performance - Performance metrics / 性能指标
