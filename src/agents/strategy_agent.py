"""
Strategy Agent
Manages trading strategies and execution
"""

import os
import sys
import time
import asyncio
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from termcolor import cprint
from src.models import ModelFactory
from src.agents.base_agent import BaseAgent

class StrategyAgent(BaseAgent):
    def __init__(self, agent_type: str = 'strategy', instance_id: str = 'main'):
        super().__init__(agent_type=agent_type, instance_id=instance_id)
        self.strategies = {}
        self.model_factory = ModelFactory()
        self.model = self.model_factory.get_model("ollama")
        self.load_strategies()
        
    def load_strategies(self):
        """Load all available trading strategies"""
        strategy_dir = Path(__file__).parent.parent / "strategies"
        if not strategy_dir.exists():
            print(f"Strategy directory not found: {strategy_dir}")
            return
            
        for strategy_file in strategy_dir.glob("*.py"):
            if strategy_file.stem not in ["__init__", "base_strategy"]:
                strategy_name = strategy_file.stem.replace("_strategy", "")
                self.strategies[strategy_name] = strategy_file
                
        print(f"✅ Loaded {len(self.strategies)} strategies!")
        for name in self.strategies:
            print(f"  • {name.title()} Strategy")
        print("Strategy Agent initialized!")

    async def analyze_market_data(self, token_data: dict) -> dict:
        """Analyze market data using loaded strategies"""
        if not token_data or 'symbol' not in token_data:
            return {'action': 'hold', 'reason': 'Invalid token data'}
            
        results = []
        for strategy_name, strategy_file in self.strategies.items():
            try:
                context = f"""
                Token: {token_data['symbol']}
                Strategy: {strategy_name}
                """
                
                if self.model:
                    response = self.model.generate_response(
                        system_prompt="You are the Strategy Analysis AI. Analyze token data.",
                        user_content=context,
                        temperature=0.7
                    )
                    results.append({
                        'strategy': strategy_name,
                        'analysis': response
                    })
            except Exception as e:
                print(f"Error in {strategy_name} strategy: {e}")
                
        return {
            'action': 'hold' if not results else 'analyze',
            'strategies': results
        }

    async def run(self):
        """Main processing loop"""
        print(f"\nStrategy Agent {self.instance_id} starting...")
        print("Ready to execute strategies!")
        
        try:
            while self.active:
                # Process strategies
                for strategy_name in self.strategies:
                    try:
                        token_data = {'symbol': strategy_name}
                        analysis = await self.analyze_market_data(token_data)
                        if analysis['action'] != 'hold':
                            cprint(f"Strategy {strategy_name}: {analysis['action']}", "cyan")
                    except Exception as e:
                        cprint(f"❌ Error in strategy {strategy_name}: {str(e)}", "red")
                        
                await asyncio.sleep(60)  # Check every minute
                
        except Exception as e:
            cprint(f"\n❌ Strategy Agent error: {str(e)}", "red")
        except KeyboardInterrupt:
            cprint("\nStrategy Agent shutting down...", "yellow")

if __name__ == "__main__":
    agent = StrategyAgent()
    agent.run()
