"""
Strategy Agent
Manages trading strategies and execution
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from termcolor import cprint
from src.models import ModelFactory

class StrategyAgent:
    def __init__(self):
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

    def analyze_market_data(self, token_data: dict) -> dict:
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

    def run(self):
        """Main processing loop"""
        print("\nStrategy Agent starting...")
        print("Ready to execute strategies!")
        
        try:
            while True:
                time.sleep(1)  # Rate limiting for Chainstack
                
        except KeyboardInterrupt:
            print("\nStrategy Agent shutting down...")

if __name__ == "__main__":
    agent = StrategyAgent()
    agent.run()
