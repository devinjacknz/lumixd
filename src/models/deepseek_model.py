"""
Lumix DeepSeek Model Implementation
"""

import os
import json
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from termcolor import cprint
from .base_model import BaseModel, ModelResponse

class DialogueContext:
    """Maintains dialogue history and context for trading conversations"""
    def __init__(self):
        self.history: List[Dict[str, str]] = []
        self.last_analysis: Optional[Dict[str, Any]] = None
        self.risk_checks: Dict[str, Any] = {}
        self.market_data: Dict[str, Any] = {}
        
    def add_message(self, role: str, content: str) -> None:
        """Add a message to dialogue history"""
        self.history.append({"role": role, "content": content})
        if len(self.history) > 10:  # Keep last 10 messages
            self.history.pop(0)
            
    def get_context(self) -> str:
        """Get formatted dialogue context"""
        return "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in self.history[-5:]  # Last 5 messages for context
        ])
        
    def update_market_data(self, token: str, data: Dict[str, Any]) -> None:
        """Update market data for a token"""
        self.market_data[token] = {
            "data": data,
            "timestamp": time.time()
        }
        
    def clear(self) -> None:
        """Clear dialogue context"""
        self.history = []
        self.last_analysis = None
        self.risk_checks = {}

class DeepSeekModel(BaseModel):
    """Implementation for DeepSeek's models"""
    
    @property
    def AVAILABLE_MODELS(self) -> dict[str, str]:
        return {
            "deepseek-r1:1.5b": "DeepSeek R1 1.5B model",
            "deepseek-chat": "Fast chat model",
            "deepseek-coder": "Code-specialized model",
            "deepseek-reasoner": "Enhanced reasoning model"
        }
    
    def __init__(self, model_name: str = "deepseek-r1:1.5b", base_url: str = "http://localhost:11434", **kwargs):
        self.model_name = model_name
        self.base_url = base_url
        self.client = None
        self.context = DialogueContext()
        print("✨ Initializing DeepSeek model via ollama...")
        print(f"Using model: {self.model_name}")
        super().__init__()
        self.initialize_client()
    
    def initialize_client(self, **kwargs) -> None:
        """Initialize the DeepSeek client via ollama"""
        try:
            import requests
            response = requests.post(f"{self.base_url}/api/pull", json={
                "name": self.model_name
            })
            if response.status_code == 200:
                self.client = requests
                cprint(f"✨ Initialized DeepSeek model via ollama: {self.model_name}", "green")
            else:
                raise Exception(f"Failed to pull model: {response.text}")
        except Exception as e:
            cprint(f"❌ Failed to initialize DeepSeek model: {str(e)}", "red")
            self.client = None
    
    def generate_response(self, 
        system_prompt: str,
        user_content: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        use_context: bool = True,
        **kwargs
    ) -> ModelResponse:
        """Generate a response using DeepSeek via ollama"""
        try:
            if not self.client:
                raise Exception("Client not initialized")
                
            # Prepare prompt with system, context, and user content
            context_str = self.context.get_context() if use_context else ""
            full_prompt = f"""
{system_prompt}

对话历史 | Dialogue History:
{context_str}

用户输入 | User Input:
{user_content}

请用JSON格式回复 | Please respond in JSON format.
Assistant:"""
            
            # Add message to context
            self.context.add_message("user", user_content)
            
            # Call ollama API
            response = self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": full_prompt,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"API error: {response.text}")
                
            result = response.json()
            
            # Process response to extract structured data
            content = result.get('response', '')
            
            # Try to find JSON in the response
            try:
                # Look for JSON-like structure
                start_idx = content.find('{')
                end_idx = content.rfind('}')
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx + 1]
                    response_content = json.loads(json_str)
                else:
                    raise json.JSONDecodeError("No JSON found", content, 0)
                    
            except json.JSONDecodeError:
                # If not JSON, create structured format
                response_content = {
                    "error": "Failed to parse response",
                    "raw_text": content
                }
                
            # Create formatted response
            formatted_response = {
                "choices": [{
                    "message": {
                        "content": json.dumps(response_content)
                    }
                }],
                "model": self.model_name,
                "created": int(time.time())
            }
            
            response = ModelResponse(
                content=json.dumps(response_content),
                raw_response=formatted_response
            )
            
            # Add response to context
            self.context.add_message("assistant", response.content)
            return response
        except Exception as e:
            print(f"❌ DeepSeek generation error: {str(e)}")
            return ModelResponse(
                content="{}",
                raw_response={"error": str(e)}
            )
            
            # End of try block
    
    def is_available(self) -> bool:
        """Check if DeepSeek is available"""
        return self.client is not None
    
    @property
    def model_type(self) -> str:
        return "deepseek"
        
    async def analyze_trade(self, instruction: str) -> dict:
        """Analyze trading instruction and return structured data"""
        system_prompt = """你是一个专业的Solana生态DeFi交易助手。分析用户的交易指令并返回JSON格式的结果。

示例输入 | Example input:
"买入500个SOL代币，滑点不超过2%"
"Buy 500 SOL tokens with max 2% slippage"

示例输出 | Example output:
{
    "trade_type": "buy",
    "token": "SOL",
    "amount": "500",
    "slippage": "2",
    "input_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "output_mint": "So11111111111111111111111111111111111111112"
}

规则说明 | Rules:
1. 如果是买入SOL，input_mint是USDC (EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v)
2. 如果是卖出SOL，input_mint是SOL (So11111111111111111111111111111111111111112)
3. 默认滑点是2.5%
4. 金额必须是数字格式
5. trade_type必须是"buy"或"sell"

请分析以下交易指令并返回JSON格式结果："""
        
        response = self.generate_response(
            system_prompt=system_prompt,
            user_content=instruction,
            temperature=0.7
        )
        
        try:
            result = json.loads(response.content)
            
            # Add default values if missing
            if 'slippage' not in result:
                result['slippage'] = "2.5"
                
            # Convert SOL amount to lamports if buying/selling SOL
            if result.get('token', '').upper() == 'SOL':
                try:
                    amount = float(result['amount'])
                    result['amount'] = str(int(amount * 1e9))  # Convert to lamports
                except (ValueError, TypeError):
                    pass
                    
            return result
            
        except json.JSONDecodeError:
            print(f"\n❌ 分析错误 | Analysis error: Failed to parse model response")
            return {
                'error': 'Failed to parse trade instruction',
                'raw_response': response.content
            }                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              