"""
Risk Agent
Monitors and manages trading risk
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from termcolor import cprint
from src.agents.focus_agent import MODEL_TYPE, MODEL_NAME
from src.models import ModelFactory

class RiskAgent:
    def __init__(self, model_type=MODEL_TYPE, model_name=MODEL_NAME):
        self.model_type = model_type
        self.model_name = model_name
        self.model_factory = ModelFactory()
        self.model = self.model_factory.get_model(self.model_type)
        self.min_balance = 50.00
        self.max_position_size = 0.20
        self.cash_buffer = 0.30
        self.slippage = 0.025
        
    def _parse_analysis(self, response: str) -> dict:
        """Parse AI model response into structured data"""
        default_analysis = {
            'risk_level': 'high',
            'warnings': ['System error occurred'],
            'actions': ['halt_trading'],
            'reason': ''
        }
        
        try:
            lines = response.strip().split('\n')
            analysis = {
                'risk_level': 'low',
                'warnings': [],
                'actions': [],
                'reason': ''
            }
            
            for line in lines:
                if 'risk level:' in line.lower():
                    analysis['risk_level'] = line.split(':')[1].strip().lower()
                elif 'warning:' in line.lower():
                    analysis['warnings'].append(line.split(':')[1].strip())
                elif 'action:' in line.lower():
                    analysis['actions'].append(line.split(':')[1].strip())
                elif 'reason:' in line.lower():
                    analysis['reason'] = line.split(':')[1].strip()
                    
            return analysis
        except Exception as e:
            print(f"Error parsing analysis: {e}")
            default_analysis['reason'] = f'Error: {e}'
            return default_analysis
            
    def check_circuit_breakers(self, trade_data: dict) -> tuple[bool, str]:
        """Check multi-layer circuit breakers"""
        try:
            # Circuit breaker 1: Single trade loss
            if trade_data.get('unrealized_loss_percentage', 0) > 2:
                return False, "Single trade loss exceeds 2% - reducing position by 50%"
                
            # Circuit breaker 2: Market volatility
            if trade_data.get('market_volatility', 0) > 0.3:
                return False, "Market volatility exceeds 30% - halting trading"
                
            # Circuit breaker 3: Portfolio volatility
            if trade_data.get('portfolio_volatility', 0) > 0.25:
                return False, "Portfolio volatility high - reducing leverage to 50%"
                
            return True, ""
        except Exception as e:
            print(f"Error in circuit breakers: {e}")
            return False, f"Circuit breaker error: {str(e)}"
            
    def analyze_risk(self, portfolio_data: dict) -> dict:
        """Analyze portfolio risk with circuit breakers"""
        if not portfolio_data or not isinstance(portfolio_data, dict):
            return {
                'risk_level': 'high',
                'warnings': ['Invalid portfolio data'],
                'actions': ['halt_trading'],
                'reason': 'Invalid input data'
            }
            
        try:
            # Check circuit breakers first
            circuit_ok, circuit_msg = self.check_circuit_breakers(portfolio_data)
            if not circuit_ok:
                return {
                    'risk_level': 'high',
                    'warnings': [circuit_msg],
                    'actions': ['halt_trading'],
                    'reason': 'Circuit breaker triggered'
                }
            
            context = f"""
            Portfolio Value: ${portfolio_data.get('total_value', 0):.2f}
            Current PnL: ${portfolio_data.get('pnl', 0):.2f}
            Position Sizes: {portfolio_data.get('positions', {})}
            Market Volatility: {portfolio_data.get('market_volatility', 0):.2%}
            Portfolio Volatility: {portfolio_data.get('portfolio_volatility', 0):.2%}
            """
            
            if self.model:
                response = self.model.generate_response(
                    system_prompt="You are the Risk Analysis AI. Analyze portfolio risk.",
                    user_content=context,
                    temperature=0.7
                )
                return self._parse_analysis(response)
            else:
                return {
                    'risk_level': 'high',
                    'warnings': ['Model not initialized'],
                    'actions': ['halt_trading'],
                    'reason': 'Risk model unavailable'
                }
                
        except Exception as e:
            print(f"Error analyzing risk: {e}")
            return {
                'risk_level': 'high',
                'warnings': [str(e)],
                'actions': ['halt_trading'],
                'reason': f'Error: {str(e)}'
            }

    def run(self):
        """Main monitoring loop"""
        print("\nRisk Agent starting...")
        print("Ready to monitor portfolio risk!")
        
        try:
            while True:
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\nRisk Agent shutting down...")

if __name__ == "__main__":
    agent = RiskAgent()
    agent.run()
