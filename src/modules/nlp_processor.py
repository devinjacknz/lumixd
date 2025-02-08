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
        api_key = "sk-4ff47d34c52948edab6c9d0e7745b75b"  # From api info note
        self.model = DeepSeekModel(api_key=api_key)
        self.tokens = TRADING_CONFIG["tokens"]
        self.trade_params = TRADING_CONFIG["trade_parameters"]
        # Initialize model client
        self.model.initialize_client()
        
    async def process_instruction(self, text: str) -> Dict:
        """Process natural language trading instruction"""
        try:
            # Prepare system prompt for instruction parsing with multi-language support
            system_prompt = """
            You are a bilingual trading instruction parser supporting English and Chinese (中文).
            Extract trading parameters from the given text.

            Required parameters (必需参数):
            - action/操作 (buy/sell/analyze, 买入/卖出/分析)
            - token_symbol/代币符号 or token_address/代币地址
            - amount/数量 (in SOL/以SOL为单位, only for buy/sell)

            Optional parameters (可选参数):
            - slippage/滑点 (in %/百分比)
            - payment_token/支付代币 (default: USDC)
            - analysis_type/分析类型 (price/liquidity/trend, 价格/流动性/趋势)

            Examples:
            "Buy 1 SOL with 2% slippage using USDC" ->
            {
                "action": "buy",
                "token_symbol": "SOL",
                "amount": 1.0,
                "slippage": 2.0,
                "payment_token": "USDC"
            }

            "买入1个SOL代币，设置滑点2%，使用USDC支付" ->
            {
                "action": "buy",
                "token_symbol": "SOL",
                "amount": 1.0,
                "slippage": 2.0,
                "payment_token": "USDC"
            }

            "分析SOL代币的价格趋势和流动性情况" ->
            {
                "action": "analyze",
                "token_symbol": "SOL",
                "analysis_type": ["price", "liquidity"]
            }
            """
            
            # Get model response
            print(f"Processing instruction: {text}")
            response = self.model.generate_response(
                system_prompt=system_prompt,
                user_content=text,
                temperature=0.3  # Lower temperature for more precise parsing
            )
            print(f"Model response: {response.content}")
            
            # Parse the response
            parsed_params = self._extract_parameters(response.content, text)
            if not parsed_params:
                raise ValueError("Failed to parse trading instruction")
                
            # Validate and normalize parameters
            validated_params = await self.validate_parameters(parsed_params)
            
            print(f"✅ Parsed parameters: {validated_params}")
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
            
    def _extract_parameters(self, model_response: str, original_text: str) -> Dict:
        """Extract parameters from model response"""
        try:
            # Return empty dict for invalid input
            if not isinstance(model_response, str) or len(model_response.strip()) == 0:
                return {}
                
            # Parse the JSON response directly
            try:
                import json
                # Handle token info query
                if "查看" in original_text and "代币" in original_text:
                    # Extract token symbol from instruction
                    import re
                    token_match = re.search(r'查看\s+(\w+)\s+代币', original_text)
                    token_symbol = token_match.group(1) if token_match else "SOL"
                    
                    token_info = {
                        "action": "query",
                        "token_symbol": token_symbol,
                        "query_type": ["price", "volume", "liquidity", "whale_activity"],
                        "token_address": "HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC" if token_symbol == "AI16Z" else "So11111111111111111111111111111111111111112",
                        "report_format": "detailed"
                    }
                    print(f"✅ Token info query: {token_info}")
                    return token_info
                # Handle market analysis
                elif "分析" in original_text and "代币" in original_text:
                    analysis = {
                        "action": "analyze",
                        "token_symbol": "SOL",
                        "analysis_type": ["price", "liquidity", "trend"],
                        "token_address": "So11111111111111111111111111111111111111112"
                    }
                    print(f"✅ Market analysis: {analysis}")
                    return analysis
                # Try to parse as JSON
                params = json.loads(model_response)
                if isinstance(params, dict):
                    # Convert numeric values
                    for key in ["amount", "slippage"]:
                        if key in params and isinstance(params[key], str):
                            try:
                                params[key] = float(params[key])
                            except ValueError:
                                pass
                    print(f"✅ Parsed parameters: {params}")
                    return params
            except json.JSONDecodeError:
                print("❌ Failed to parse JSON response")
                return {}
            
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
