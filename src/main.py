"""
✨ Lumix AI Trading System
Main entry point for running trading agents
"""

import os
import sys
from termcolor import cprint
from dotenv import load_dotenv
import time
from datetime import datetime, timedelta
from src.config.settings import TRADING_CONFIG

# Import trading parameters
TRADING_INTERVAL = TRADING_CONFIG["trade_parameters"]["interval_minutes"]
MONITORED_TOKENS = [
    TRADING_CONFIG["tokens"]["AI16Z"],
    TRADING_CONFIG["tokens"]["SWARM"]
]
EXCLUDED_TOKENS = [
    TRADING_CONFIG["tokens"]["USDC"],
    TRADING_CONFIG["tokens"]["SOL"]
]

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Import agents and config
import asyncio
from src.agents.trading_agent import TradingAgent
from src.agents.risk_agent import RiskAgent
from src.agents.strategy_agent import StrategyAgent
from src.agents.copybot_agent import CopyBotAgent
from src.agents.sentiment_agent import SentimentAgent
from src.models import ModelFactory

# Load environment variables
load_dotenv()

# Agent Configuration
ACTIVE_AGENTS = {
    'risk': True,      # Risk management agent
    'trading': True,   # LLM trading agent
    'strategy': True,  # Strategy-based trading agent
    'copybot': True,   # CopyBot agent
    'sentiment': True, # Run sentiment_agent.py directly instead
    # whale_agent is run from whale_agent.py
    # Add more agents here as we build them:
    # 'portfolio': False,  # Future portfolio optimization agent
}

async def run_agents():
    """Run all active agents in sequence"""
    try:
        # Initialize active agents with proper instance IDs
        trading_agent = TradingAgent(instance_id='main') if ACTIVE_AGENTS['trading'] else None
        risk_agent = RiskAgent(instance_id='main') if ACTIVE_AGENTS['risk'] else None
        strategy_agent = StrategyAgent(instance_id='main') if ACTIVE_AGENTS['strategy'] else None
        copybot_agent = CopyBotAgent(instance_id='main') if ACTIVE_AGENTS['copybot'] else None
        sentiment_agent = SentimentAgent(instance_id='main') if ACTIVE_AGENTS['sentiment'] else None

        while True:
            try:
                # Run Risk Management
                try:
                    # Run Risk Management
                    if risk_agent and risk_agent.active:
                        cprint("\n🛡️ Running Risk Management...", "cyan")
                        await risk_agent.run()

                    # Run Trading Analysis
                    if trading_agent and trading_agent.active:
                        cprint("\n🤖 Running Trading Analysis...", "cyan")
                        await trading_agent.run()

                    # Run Strategy Analysis
                    if strategy_agent and strategy_agent.active:
                        cprint("\n📊 Running Strategy Analysis...", "cyan")
                        for token in MONITORED_TOKENS:
                            if token not in EXCLUDED_TOKENS:  # Skip USDC and other excluded tokens
                                cprint(f"\n🔍 Analyzing {token}...", "cyan")
                                try:
                                    analysis = await strategy_agent.analyze_market_data({'symbol': token})
                                    if analysis and 'error' in analysis:
                                        cprint(f"⚠️ Analysis warning: {analysis['error']}", "yellow")
                                except Exception as e:
                                    cprint(f"❌ Analysis error: {str(e)}", "red")

                    # Run CopyBot Analysis
                    if copybot_agent and copybot_agent.active:
                        cprint("\n🤖 Running CopyBot Portfolio Analysis...", "cyan")
                        await copybot_agent.run_analysis_cycle()

                    # Run Sentiment Analysis
                    if sentiment_agent and sentiment_agent.active:
                        cprint("\n🎭 Running Sentiment Analysis...", "cyan")
                        await sentiment_agent.run()
                except Exception as e:
                    cprint(f"\n❌ Agent execution error: {str(e)}", "red")
                    # Continue to next cycle even if one agent fails

                # Sleep until next cycle
                next_run = datetime.now() + timedelta(minutes=TRADING_INTERVAL)
                cprint(f"\n😴 Sleeping until {next_run.strftime('%H:%M:%S')}", "cyan")
                await asyncio.sleep(60 * TRADING_INTERVAL)

            except Exception as e:
                cprint(f"\n❌ Error running agents: {str(e)}", "red")
                cprint("🔄 Continuing to next cycle...", "yellow")
                await asyncio.sleep(60)  # Sleep for 1 minute on error before retrying

    except KeyboardInterrupt:
        cprint("\n👋 Gracefully shutting down...", "yellow")
        # Cleanup
        if trading_agent:
            trading_agent.active = False
        if risk_agent:
            risk_agent.active = False
        if strategy_agent:
            strategy_agent.active = False
        if copybot_agent:
            copybot_agent.active = False
        if sentiment_agent:
            sentiment_agent.active = False
    except Exception as e:
        cprint(f"\n❌ Fatal error in main loop: {str(e)}", "red")
        raise

if __name__ == "__main__":
    try:
        cprint("\n✨ Lumix AI Agent Trading System Starting...", "white", "on_blue")
        cprint("\n📊 Active Agents:", "white", "on_blue")
        for agent, active in ACTIVE_AGENTS.items():
            status = "✅ ON" if active else "❌ OFF"
            cprint(f"  • {agent.title()}: {status}", "white", "on_blue")
        print("\n")

        import asyncio
        asyncio.run(run_agents())
    except KeyboardInterrupt:
        cprint("\n👋 Gracefully shutting down...", "yellow")
    except Exception as e:
        cprint(f"\n❌ Fatal error: {str(e)}", "red")
        sys.exit(1)
