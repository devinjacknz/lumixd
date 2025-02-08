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
            # Prepare system prompt for instruction parsing with multi-language support
            system_prompt = """
            You are a bilingual trading instruction parser supporting English and Chinese (中文).
            Extract trading parameters from the given text.

            Required parameters (必需参数):
            - action/操作 (buy/sell, 买入/卖出)
            - token_symbol/代币符号 or token_address/代币地址
            - amount/数量 (in SOL/以SOL为单位)

            Optional parameters (可选参数):
            - slippage/滑点 (in %/百分比)
            - urgency/紧急程度 (high/medium/low, 高/中/低)

            Examples:
            "Buy 500 AI16z tokens with 2% slippage" ->
            {
                "action": "buy",
                "token_symbol": "AI16z",
                "amount": 500,
                "slippage": 2.0
            }

            "买入500个AI16z代币，滑点不超过2%" ->
            {
                "action": "buy",
                "token_symbol": "AI16z",
                "amount": 500,
                "slippage": 2.0
            }
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
            # Validate required parameters with bilingual messages
            if "action" not in params:
                raise ValueError({
                    "en": "Trading action (buy/sell) is required",
                    "zh": "交易操作（买入/卖出）为必填项"
                })
            if "token_symbol" not in params and "token_address" not in params:
                raise ValueError({
                    "en": "Token symbol or address is required",
                    "zh": "代币符号或地址为必填项"
                })
            if "amount" not in params:
                raise ValueError({
                    "en": "Trading amount is required",
                    "zh": "交易数量为必填项"
                })
                
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
            # Return empty dict for invalid input
            if not isinstance(model_response, str) or len(model_response.strip()) == 0:
                return {}
                
            # Use another model call to structure the output
            response = self.model.generate_response(
                system_prompt="Extract and structure the following trading parameters as a Python dictionary. Include only valid parameters.",
                user_content=model_response,
                temperature=0.1  # Very low temperature for consistent formatting
            )
            
            # Return empty dict for invalid model response
            if not response or not response.content:
                return {}
                
            # Safely evaluate the response
            import ast
            try:
                # Find dictionary-like structure in the response
                start = response.content.find("{")
                end = response.content.rfind("}") + 1
                if start >= 0 and end > start:
                    dict_str = response.content[start:end]
                    params = ast.literal_eval(dict_str)
                    # Convert numeric values
                    for key in ["amount", "slippage"]:
                        if key in params and isinstance(params[key], str):
                            try:
                                params[key] = float(params[key])
                            except ValueError:
                                pass
                    return params
            except:
                return {}  # Return empty dict on any parsing error
            
            return {}
        except Exception as e:
            cprint(f"❌ Failed to extract parameters: {str(e)}", "red")
            return {}
            
    def _calculate_confidence(self, model_response: str) -> float:
        """Calculate confidence score for parameter extraction"""
        try:
            if not isinstance(model_response, str):
                return 0.5
                
            # Check for confidence indicators in the response
            indicators = {
                "high": ["confident", "clear", "explicit", "definitely", "certain", "sure", "absolutely"],
                "medium": ["likely", "probably", "should be", "appears", "seems", "expect"],
                "low": ["unclear", "ambiguous", "might be", "possibly", "maybe", "uncertain", "not sure"]
            }
            
            response_lower = model_response.lower()
            
            # Count indicators with adjusted weights
            high_matches = sum(1 for word in indicators["high"] if word in response_lower)
            medium_matches = sum(1 for word in indicators["medium"] if word in response_lower)
            low_matches = sum(1 for word in indicators["low"] if word in response_lower)
            
            # Base confidence starts at medium (0.5)
            confidence = 0.5
            
            # Adjust confidence based on matches
            if high_matches > 0:
                confidence += 0.3 * min(high_matches, 2)  # Max boost of 0.6 from high confidence words
            if medium_matches > 0:
                confidence += 0.1 * min(medium_matches, 2)  # Max boost of 0.2 from medium confidence words
            if low_matches > 0:
                confidence -= 0.2 * min(low_matches, 2)  # Max reduction of 0.4 from low confidence words
                
            return min(1.0, max(0.0, confidence))
        except Exception:
            return 0.5  # Default to medium confidence on error
