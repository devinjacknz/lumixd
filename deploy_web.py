import os
import sys
import subprocess
from pathlib import Path
from waitress import serve
from src.web.app_v2 import app

def setup_environment():
    """Set up required environment variables"""
    env_vars = {
        'PYTHONPATH': os.path.abspath('.'),
        'WALLET_KEY': os.getenv('walletkey'),
        'SOLANA_PRIVATE_KEY': os.getenv('walletkey'),
        'RPC_ENDPOINT': 'https://solana-mainnet.core.chainstack.com/60d783949ddfbc48b7f1232aa308d7b8',
        'MAX_TRADE_SIZE_SOL': '10.0',
        'DEFAULT_SLIPPAGE_BPS': '250',
        'JUPITER_API_URL': 'https://quote-api.jup.ag/v6',
        'MONGODB_URI': 'mongodb://localhost:27017',
        'MONGODB_DB': 'lumixd',
        'REDIS_URL': 'redis://localhost:6379',
        'LOG_LEVEL': 'INFO',
        'LOG_FILE': 'user_operations.log'
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value

def install_dependencies():
    """Install required packages"""
    requirements = [
        'flask==3.0.2',
        'waitress==3.0.0',
        'aiohttp==3.9.3',
        'redis==5.0.1',
        'motor==3.3.2',
        'pymongo==4.6.1'
    ]
    
    for req in requirements:
        subprocess.run([sys.executable, '-m', 'pip', 'install', req])

def setup_logging():
    """Configure logging"""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

def deploy_web():
    """Deploy the web application"""
    print("\n🚀 部署网页应用 Deploying Web Application...")
    print("==========================================")
    
    try:
        print("⚙️ 设置环境变量 Setting up environment...")
        setup_environment()
        
        print("📦 安装依赖 Installing dependencies...")
        install_dependencies()
        
        print("📝 配置日志 Configuring logging...")
        setup_logging()
        
        print("🖥️ 启动应用 Starting application...")
        # Configure app for frp proxy
        app.config['PREFERRED_URL_SCHEME'] = 'https'
        app.config['PROXY_FIX_X_PROTO'] = 1
        app.config['PROXY_FIX_X_HOST'] = 1
        app.config['PROXY_FIX_X_PREFIX'] = 1
        
        # Configure CORS for deployment URL
        app.config['CORS_ORIGINS'] = ['https://pr-playbook-app-tunnel-jncimc99.devinapps.com']
        app.config['CORS_SUPPORTS_CREDENTIALS'] = True
        
        # Use waitress for production deployment with proxy settings
        serve(
            app,
            host='0.0.0.0',
            port=8082,
            url_scheme='https',
            url_prefix='/',
            threads=4,
            connection_limit=1000,
            cleanup_interval=30,
            channel_timeout=60
        )
        
        print("✅ 部署成功 Deployment successful")
        return True
        
    except Exception as e:
        print(f"❌ 部署失败 Deployment failed: {str(e)}")
        return False

if __name__ == "__main__":
    deploy_web()
