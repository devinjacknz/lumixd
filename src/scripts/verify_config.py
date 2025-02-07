from src.utils.env import load_environment, verify_environment
from src.config.settings import REQUIRED_ENV_VARS, TRADING_CONFIG
from termcolor import cprint

def verify_configuration():
    """Verify all configuration is properly set"""
    # Check environment variables
    if not load_environment():
        cprint("❌ Failed to load .env file", "red")
        return False
        
    env_error = verify_environment(REQUIRED_ENV_VARS)
    if env_error:
        cprint(f"❌ {env_error}", "red")
        return False
        
    # Verify trading configuration
    try:
        min_sol = TRADING_CONFIG["monitoring"]["min_sol_balance"]
        trade_amount = TRADING_CONFIG["trade_parameters"]["amount_sol"]
        interval = TRADING_CONFIG["trade_parameters"]["interval_minutes"]
        
        cprint(f"✅ Configuration verified", "green")
        cprint(f"💰 Trade amount: {trade_amount} SOL", "cyan")
        cprint(f"⏱️ Trade interval: {interval} minutes", "cyan")
        cprint(f"💼 Minimum SOL balance: {min_sol} SOL", "cyan")
        return True
    except KeyError as e:
        cprint(f"❌ Invalid trading configuration: {e}", "red")
        return False

if __name__ == "__main__":
    verify_configuration()
