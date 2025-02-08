import os
import sys
import shutil
import subprocess
from pathlib import Path

def setup_environment():
    """Set up required environment variables and directories"""
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
        'PyQt6==6.6.1',
        'qt-material==2.14',
        'darkdetect==0.8.0',
        'aiohttp==3.9.3',
        'redis==5.0.1',
        'motor==3.3.2',
        'pymongo==4.6.1'
    ]
    
    for req in requirements:
        subprocess.run([sys.executable, '-m', 'pip', 'install', req])

def setup_logging():
    """Create logging directory and configure logging"""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    log_config = """
[loggers]
keys=root

[handlers]
keys=fileHandler,consoleHandler

[formatters]
keys=defaultFormatter

[logger_root]
level=INFO
handlers=fileHandler,consoleHandler

[handler_fileHandler]
class=FileHandler
level=INFO
formatter=defaultFormatter
args=('logs/user_operations.log', 'a')

[handler_consoleHandler]
class=StreamHandler
level=INFO
formatter=defaultFormatter
args=(sys.stdout,)

[formatter_defaultFormatter]
format=%(asctime)s - %(levelname)s - %(message)s
datefmt=%Y-%m-%d %H:%M:%S
    """
    
    with open('logging.conf', 'w') as f:
        f.write(log_config.strip())

def deploy_gui():
    """Deploy the GUI application"""
    print("🚀 Deploying GUI application...")
    
    try:
        # Setup environment
        print("⚙️ Setting up environment...")
        setup_environment()
        
        # Install dependencies
        print("📦 Installing dependencies...")
        install_dependencies()
        
        # Setup logging
        print("📝 Configuring logging...")
        setup_logging()
        
        # Start the GUI application
        print("🖥️ Starting GUI application...")
        subprocess.run([
            sys.executable,
            'src/gui/main_window.py'
        ], env=os.environ)
        
        print("✅ GUI application deployed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Deployment failed: {str(e)}")
        return False

if __name__ == "__main__":
    deploy_gui()
