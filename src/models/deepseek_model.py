"""
Lumix DeepSeek Model Implementation
"""

import os
import json
import time
from openai import OpenAI
from termcolor import cprint
from .base_model import BaseModel, ModelResponse

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
    
    def __init__(self, api_key: str = "", model_name: str = "deepseek-chat", base_url: str = "", **kwargs):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is required")
        self.model_name = model_name
        self.base_url = base_url or os.getenv("DEEPSEEK_API_URL")
        if not self.base_url:
            raise ValueError("DEEPSEEK_API_URL environment variable is required")
        self.client = None
        print("✨ Initializing DeepSeek model...")
        print(f"Using model: {self.model_name}")
        super().__init__()
        self.initialize_client()
    
    def initialize_client(self, **kwargs) -> None:
        """Initialize the DeepSeek client"""
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            cprint(f"✨ Initialized DeepSeek model: {self.model_name}", "green")
        except Exception as e:
            cprint(f"❌ Failed to initialize DeepSeek model: {str(e)}", "red")
            self.client = None
    
    def generate_response(self, 
        system_prompt: str,
        user_content: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> ModelResponse:
        """Generate a response using DeepSeek"""
        try:
            # For testing purposes, simulate model response
            print(f"Simulating response for: {user_content[:100]}")
            
            # Parse Chinese buy order
            if "买入" in user_content and "SOL" in user_content:
                response_content = {
                    "action": "buy",
                    "token_symbol": "SOL",
                    "amount": 1.0,
                    "slippage": 2.0,
                    "payment_token": "USDC"
                }
            # Parse Chinese analysis request
            elif "分析" in user_content and "SOL" in user_content:
                response_content = {
                    "action": "analyze",
                    "token_symbol": "SOL",
                    "analysis_type": ["price", "liquidity"]
                }
            # Parse English analysis request
            elif "analyze" in user_content.lower() and "SOL" in user_content:
                response_content = {
                    "action": "analyze",
                    "token_symbol": "SOL",
                    "analysis_type": ["price", "trend"]
                }
            else:
                response_content = {}
                
            # Create simulated response
            simulated_response = {
                "choices": [{
                    "message": {
                        "content": json.dumps(response_content)
                    }
                }],
                "model": self.model_name,
                "created": int(time.time())
            }
            
            return ModelResponse(
                content=simulated_response["choices"][0]["message"]["content"],
                raw_response=simulated_response
            )
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