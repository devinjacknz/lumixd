"""
NLP Processor Module
Handles trading instruction parsing and parameter validation using DeepSeek model
"""

from typing import Dict, Optional, Tuple
from termcolor import cprint
from src.models.deepseek_model import DeepSeekModel
from src.config.settings import TRADING_CONFIG

class NLPProcessor:
    def __init__(self):
        self.model = DeepSeekModel()
        self.tokens = TRADING_CONFIG["tokens"]
        self.trade_params = TRADING_CONFIG["trade_parameters"]
        
    async def process_instruction(self, text: str) -> Dict:
        """Process natural language trading instruction"""
        try:
            # Prepare system prompt for instruction parsing
            system_prompt = """
            You are a trading instruction parser. Extract trading parameters from the given text.
            Required parameters:
            - action (buy/sell)
            - token_symbol or token_address
            - amount (in SOL)
            Optional parameters:
            - slippage (in %)
            - urgency (high/medium/low)
            """
            
            # Get model response
            response = self.model.generate_response(
                system_prompt=system_prompt,
                user_content=text,
                temperature=0.3  # Lower temperature for more precise parsing
            )
            
            # Parse the response
            parsed_params = self._extract_parameters(response.content)
            if not parsed_params:
                raise ValueError("Failed to parse trading instruction")
                
            # Validate and normalize parameters
            validated_params = await self.validate_parameters(parsed_params)
            
            return {
                "original_text": text,
                "parsed_params": validated_params,
                "confidence": self._calculate_confidence(response.content)
            }
        except Exception as e:
            cprint(f"❌ Failed to process instruction: {str(e)}", "red")
            return {
                "error": str(e),
                "original_text": text
            }
            
    async def validate_parameters(self, params: Dict) -> Dict:
        """Validate and normalize trading parameters"""
        try:
            # Validate required parameters
            if "action" not in params:
                raise ValueError("Trading action (buy/sell) is required")
            if "token_symbol" not in params and "token_address" not in params:
                raise ValueError("Token symbol or address is required")
            if "amount" not in params:
                raise ValueError("Trading amount is required")
                
            # Normalize action
            params["action"] = params["action"].lower()
            if params["action"] not in ["buy", "sell"]:
                raise ValueError(f"Invalid action: {params['action']}")
                
            # Resolve token address
            if "token_symbol" in params:
                symbol = params["token_symbol"].upper()
                if symbol in self.tokens:
                    params["token_address"] = self.tokens[symbol]
                else:
                    raise ValueError(f"Unknown token symbol: {symbol}")
                    
            # Normalize amount
            try:
                params["amount"] = float(params["amount"])
                if params["amount"] <= 0:
                    raise ValueError("Amount must be positive")
            except (TypeError, ValueError):
                raise ValueError(f"Invalid amount: {params['amount']}")
                
            # Normalize slippage
            if "slippage" in params:
                try:
                    params["slippage"] = float(params["slippage"])
                    if not (0 < params["slippage"] <= 5):  # Max 5% slippage
                        raise ValueError("Slippage must be between 0 and 5%")
                except (TypeError, ValueError):
                    params["slippage"] = self.trade_params["slippage_bps"] / 100
                    
            # Apply default parameters
            params.setdefault("slippage", self.trade_params["slippage_bps"] / 100)
            params.setdefault("urgency", "medium")
            
            return params
        except Exception as e:
            cprint(f"❌ Parameter validation failed: {str(e)}", "red")
            raise
            
    def _extract_parameters(self, model_response: str) -> Dict:
        """Extract parameters from model response"""
        try:
            # Use another model call to structure the output
            response = self.model.generate_response(
                system_prompt="Extract and structure the following trading parameters as a Python dictionary. Include only valid parameters.",
                user_content=model_response,
                temperature=0.1  # Very low temperature for consistent formatting
            )
            
            # Safely evaluate the response
            import ast
            try:
                # Find dictionary-like structure in the response
                start = response.content.find("{")
                end = response.content.rfind("}") + 1
                if start >= 0 and end > start:
                    dict_str = response.content[start:end]
                    return ast.literal_eval(dict_str)
            except:
                pass
                
            # Fallback to manual parsing if ast.literal_eval fails
            params = {}
            lines = model_response.lower().split("\n")
            for line in lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().replace(" ", "_")
                    value = value.strip().strip('"\'')
                    if value:
                        params[key] = value
                        
            return params
        except Exception as e:
            cprint(f"❌ Failed to extract parameters: {str(e)}", "red")
            return {}
            
    def _calculate_confidence(self, model_response: str) -> float:
        """Calculate confidence score for parameter extraction"""
        try:
            # Check for confidence indicators in the response
            indicators = {
                "high": ["confident", "clear", "explicit", "definitely"],
                "medium": ["likely", "probably", "should be"],
                "low": ["unclear", "ambiguous", "might be", "possibly"]
            }
            
            response_lower = model_response.lower()
            
            # Count indicators
            scores = {
                "high": sum(1 for word in indicators["high"] if word in response_lower) * 1.0,
                "medium": sum(1 for word in indicators["medium"] if word in response_lower) * 0.6,
                "low": sum(1 for word in indicators["low"] if word in response_lower) * 0.3
            }
            
            # Calculate weighted score
            total_indicators = sum(scores.values())
            if total_indicators == 0:
                return 0.5  # Default medium confidence
                
            confidence = (scores["high"] + scores["medium"] + scores["low"]) / total_indicators
            return min(1.0, max(0.0, confidence))
        except Exception:
            return 0.5  # Default to medium confidence on error
