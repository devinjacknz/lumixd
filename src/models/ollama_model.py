"""
Ollama Model Integration
Handles interaction with local Ollama API
"""

import os
import json
import requests
from .base_model import BaseModel, ModelResponse

class OllamaModel(BaseModel):
    @property
    def AVAILABLE_MODELS(self):
        return ['deepseek-r1:1.5b']
    
    def __init__(self, model_name="deepseek-r1:1.5b"):
        super().__init__()
        self.model_name = model_name
        self.api_url = "http://localhost:11434/api/generate"
        self.headers = {"Content-Type": "application/json"}
        self.client = None
        self.initialize_client()
        
    def initialize_client(self):
        """Initialize connection to Ollama API"""
        try:
            response = requests.get("http://localhost:11434/api/tags")
            response.raise_for_status()
            self.client = True
            print("✨ Successfully connected to Ollama API")
            print(f"📚 Available Ollama models: {self.AVAILABLE_MODELS}")
            return True
        except Exception as e:
            print(f"Error connecting to Ollama API: {e}")
            return False
            
    def is_available(self):
        """Check if model is available"""
        return self.client is not None
        
    @property
    def model_type(self):
        """Get model type"""
        return "ollama"
        
    def generate_response(self, system_prompt, user_content, temperature=0.7):
        """Generate response from Ollama model"""
        if not self.is_available():
            print("Model not initialized")
            return None
            
        try:
            # Format prompt to encourage JSON response
            formatted_prompt = f"""
{system_prompt}

请用JSON格式回复。确保回复以 '{{' 开始，以 '}}' 结束。
Please respond in JSON format. Ensure the response starts with '{{' and ends with '}}'.

{user_content}
"""
            data = {
                "model": self.model_name,
                "prompt": formatted_prompt,
                "temperature": temperature,
                "stream": True  # Use streaming mode
            }
            
            # Stream response and collect all chunks
            full_response = ""
            with requests.post(self.api_url, json=data, headers=self.headers, stream=True) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if 'response' in chunk:
                                full_response += chunk['response']
                        except json.JSONDecodeError:
                            continue
            
            # Clean up and parse JSON from full response
            try:
                # Remove code blocks and clean whitespace
                content = full_response.replace('```json', '').replace('```', '').strip()
                content = ' '.join(line.strip() for line in content.split('\n'))
                
                # Find JSON content
                start_idx = content.find('{')
                end_idx = content.rfind('}')
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx + 1]
                    parsed_content = json.loads(json_str)
                    
                    return ModelResponse(
                        content=json.dumps(parsed_content),
                        raw_response={'response': full_response}
                    )
                        
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")
                pass
                
            # Return raw response if JSON parsing fails
            return ModelResponse(
                content=content,
                raw_response=response.json()
            )
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return None
            
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
}"""
        
        response = self.generate_response(
            system_prompt=system_prompt,
            user_content=instruction,
            temperature=0.7
        )
        
        if not response:
            return {
                'error': 'Failed to generate response',
                'error_cn': '无法生成响应'
            }
            
        try:
            # Try to parse JSON from response
            content = response.content
            if isinstance(content, str):
                # Look for JSON-like structure
                start_idx = content.find('{')
                end_idx = content.rfind('}')
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx + 1]
                    result = json.loads(json_str)
                    return result
                    
            return {
                'error': 'Invalid response format',
                'error_cn': '响应格式无效'
            }
        except json.JSONDecodeError:
            return {
                'error': 'Failed to parse response',
                'error_cn': '无法解析响应'
            }
            
    async def check_risk_dialogue(self, trade_request: dict) -> dict:
        """Risk check with bilingual dialogue"""
        system_prompt = """你是一个专业的风险管理助手，负责分析交易风险。
You are a professional risk management assistant analyzing trade risks.

请分析以下交易风险并返回JSON格式结果 | Please analyze the following trade risk and return JSON result:

示例输出 | Example output:
{
    "risk_level": "low/medium/high",
    "approved": true/false,
    "reason": "Risk analysis explanation in both languages",
    "warnings": ["Warning 1", "警告 1"],
    "suggestions": ["Suggestion 1", "建议 1"]
}"""
        
        risk_prompt = f"""
分析以下交易风险 | Analyze trade risk:
代币 | Token: {trade_request.get('token', 'Unknown')}
数量 | Amount: {trade_request.get('amount', '0')}
方向 | Direction: {trade_request.get('direction', 'Unknown')}
滑点 | Slippage: {trade_request.get('slippage', '2.5')}%"""
        
        response = self.generate_response(
            system_prompt=system_prompt,
            user_content=risk_prompt,
            temperature=0.7
        )
        
        if not response:
            return {
                'error': 'Failed to generate response',
                'error_cn': '无法生成响应',
                'approved': False
            }
            
        try:
            # Try to parse JSON from response
            content = response.content
            if isinstance(content, str):
                # Look for JSON-like structure
                start_idx = content.find('{')
                end_idx = content.rfind('}')
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx + 1]
                    result = json.loads(json_str)
                    return result
                    
            return {
                'error': 'Invalid response format',
                'error_cn': '响应格式无效',
                'approved': False
            }
        except json.JSONDecodeError:
            return {
                'error': 'Failed to parse response',
                'error_cn': '无法解析响应',
                'approved': False
            }              