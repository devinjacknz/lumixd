import os
import time
from termcolor import cprint
from src.nice_funcs import market_buy
from src.utils.logger import setup_logger
from src.config.trade_config import TRADE_CONFIG

logger = setup_logger()

def execute_ai16z_trades():
    """Execute two small trades for AI16z token"""
    try:
        trade_size = TRADE_CONFIG["TRADE_AMOUNT_SOL"]
        max_retries = TRADE_CONFIG["MAX_RETRIES"]
        
        for i in range(2):
            logger.info(f"Executing trade {i+1} of 2 for {trade_size} SOL")
            cprint(f"\n🔄 Executing trade {i+1} of 2 for {trade_size} SOL...", "cyan")
            
            retry_count = 0
            while retry_count < max_retries:
                try:
                    success = market_buy(
                        TRADE_CONFIG["AI16Z_TOKEN"],
                        str(int(trade_size * 1e9))
                    )
                    if success:
                        logger.info(f"Trade {i+1} completed successfully")
                        cprint(f"✅ Trade {i+1} completed successfully\n", "green")
                        break
                    else:
                        logger.error(f"Trade {i+1} failed, attempt {retry_count + 1}/{max_retries}")
                        retry_count += 1
                        if retry_count < max_retries:
                            time.sleep(TRADE_CONFIG["RETRY_DELAY"])
                except Exception as e:
                    logger.error(f"Error in trade {i+1}, attempt {retry_count + 1}: {str(e)}")
                    retry_count += 1
                    if retry_count < max_retries:
                        time.sleep(TRADE_CONFIG["RETRY_DELAY"])
            
            if retry_count == max_retries:
                logger.error(f"Trade {i+1} failed after {max_retries} attempts")
                cprint(f"❌ Trade {i+1} failed after {max_retries} attempts\n", "red")
                
    except Exception as e:
        logger.error(f"Fatal error executing trades: {str(e)}")
        cprint(f"❌ Fatal error executing trades: {str(e)}", "red")
    finally:
        cprint("🧹 Cleaning up temporary data...", "cyan")

if __name__ == "__main__":
    execute_ai16z_trades()
