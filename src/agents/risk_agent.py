"""
Risk Agent
Monitors and manages trading risk
"""

import os
import sys
import time
import requests
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
        self.positions = []
        
    def get_current_positions(self) -> list:
        """Get current trading positions"""
        return self.positions
        
    def check_risk_limits(self, trade_amount: float) -> bool:
        """Check if trade amount is within risk limits"""
        try:
            # Get current positions
            positions = self.get_current_positions()
            
            # Calculate total position size
            total_position = sum(float(pos.get('amount', 0)) for pos in positions) if positions else 0
            
            # Get SOL balance from RPC
            response = requests.post(
                os.getenv("RPC_ENDPOINT"),
                headers={"Content-Type": "application/json"},
                json={
                    "jsonrpc": "2.0",
                    "id": "get-balance",
                    "method": "getBalance",
                    "params": [os.getenv("WALLET_ADDRESS")]
                }
            )
            response.raise_for_status()
            balance = float(response.json().get("result", {}).get("value", 0)) / 1e9  # Convert lamports to SOL
            
            # Check if trade amount exceeds balance
            if trade_amount > balance:
                cprint(f"❌ Trade amount {trade_amount} SOL exceeds balance {balance} SOL", "red")
                return False
            
            # Check if new trade would exceed max position size
            max_trade_size = balance * self.max_position_size
            if total_position + trade_amount > max_trade_size:
                cprint(f"❌ Trade would exceed max position size of {max_trade_size} SOL", "red")
                return False
                
            return True
        except Exception as e:
            cprint(f"❌ Error checking risk limits: {str(e)}", "red")
            return False
        
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
        """Check multi-layer circuit breakers with dynamic thresholds"""
        try:
            # Dynamic loss threshold based on volatility
            volatility = trade_data.get('market_volatility', 0)
            max_loss = 0.02 * (1 + volatility)  # Increase threshold in high volatility
            
            # Circuit breaker 1: Single trade loss with dynamic threshold
            if trade_data.get('unrealized_loss_percentage', 0) > max_loss:
                return False, f"Loss exceeds {max_loss:.1%} threshold - reducing position by 50%"
                
            # Circuit breaker 2: Liquidity depth check
            if trade_data.get('liquidity_score', 1) < 0.5:
                return False, "Insufficient liquidity depth - halting trading"
                
            # Circuit breaker 3: Smart contract risk
            if trade_data.get('contract_risk_score', 0) > 0.7:
                return False, "High contract risk detected - halting trading"
                
            # Circuit breaker 4: Portfolio volatility with dynamic threshold
            portfolio_volatility = trade_data.get('portfolio_volatility', 0)
            if portfolio_volatility > 0.25 * (1 + volatility):
                return False, f"Portfolio volatility exceeds {(0.25 * (1 + volatility)):.1%} - reducing leverage"
                
            return True, ""
        except Exception as e:
            print(f"Error in circuit breakers: {e}")
            return False, f"Circuit breaker error: {str(e)}"
            
    def calculate_contract_risk(self, token_data: dict) -> float:
        """Calculate contract risk score based on multiple factors"""
        try:
            # Get token data
            age = float(token_data.get('contract_age_days', 0))
            verified = bool(token_data.get('is_verified', False))
            audit_count = int(token_data.get('audit_count', 0))
            owner_balance = float(token_data.get('owner_balance_percentage', 100))
            
            # Calculate risk components
            age_risk = max(0, min(1, 30 / age if age > 0 else 1))
            verification_risk = 0.0 if verified else 0.5
            audit_risk = max(0, min(1, 1 - (audit_count * 0.25)))
            ownership_risk = max(0, min(1, owner_balance / 50))
            
            # Weighted risk score
            risk_score = (
                0.3 * age_risk +
                0.3 * verification_risk +
                0.2 * audit_risk +
                0.2 * ownership_risk
            )
            
            return float(risk_score)
        except Exception as e:
            print(f"Error calculating contract risk: {e}")
            return 1.0  # Return maximum risk on error
            
    def analyze_risk(self, portfolio_data: dict) -> dict:
        """Analyze portfolio risk with enhanced risk metrics"""
        if not portfolio_data or not isinstance(portfolio_data, dict):
            return {
                'risk_level': 'high',
                'warnings': ['Invalid portfolio data'],
                'actions': ['halt_trading'],
                'reason': 'Invalid input data'
            }
            
        try:
            # Calculate contract risk for each position
            positions = portfolio_data.get('positions', {})
            for token, data in positions.items():
                contract_risk = self.calculate_contract_risk(data)
                portfolio_data['contract_risk_score'] = contract_risk
            
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
            Contract Risk Score: {portfolio_data.get('contract_risk_score', 0):.2%}
            Liquidity Score: {portfolio_data.get('liquidity_score', 0):.2%}
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
