"""
Ollama Model Integration
Handles interaction with local Ollama API
"""

import os
import json
import re
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

请严格按照以下格式回复 | Please respond in the following format:
```json
{{
    "key": "value"
}}
```

{user_content}

注意事项 | Notes:
1. 只返回JSON格式，不要添加任何其他文本 | Return only JSON, no other text
2. 所有字符串必须用双引号 | All strings must use double quotes
3. 数字不需要引号 | Numbers should not have quotes"""
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
                # Extract JSON from code blocks or raw response
                content = full_response.strip()
                json_str = ""
                
                # Try to find JSON in code blocks first
                if "```json" in content:
                    parts = content.split("```json")
                    if len(parts) > 1:
                        json_block = parts[1].split("```")[0].strip()
                        try:
                            parsed_content = json.loads(json_block)
                            return ModelResponse(
                                content=json.dumps(parsed_content),
                                raw_response={'response': full_response}
                            )
                        except json.JSONDecodeError:
                            pass
                
                # Try to find raw JSON if no code blocks or invalid JSON in code blocks
                content = content.replace('```json', '').replace('```', '').strip()
                content = ' '.join(line.strip() for line in content.split('\n'))
                
                # Find JSON content
                start_idx = content.find('{')
                end_idx = content.rfind('}')
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx + 1]
                    # Clean up any non-JSON text
                    json_str = re.sub(r'[^\x00-\x7F]+', '', json_str)  # Remove non-ASCII chars
                    json_str = re.sub(r'(?<!["{\s,])\s*:\s*(?![\s,}"])', '": "', json_str)  # Fix missing quotes
                    json_str = re.sub(r'(?<=[}\]"])\s*(?=,)', '', json_str)  # Fix spacing
                    parsed_content = json.loads(json_str)
                    
                    # Map trade_type to direction for trading commands
                    if 'trade_type' in parsed_content:
                        parsed_content['direction'] = parsed_content['trade_type']
                        
                    # Convert slippage to slippage_bps
                    if 'slippage' in parsed_content:
                        try:
                            parsed_content['slippage_bps'] = int(float(parsed_content['slippage']) * 100)
                        except (ValueError, TypeError):
                            parsed_content['slippage_bps'] = 250  # Default 2.5%
                    
                    return ModelResponse(
                        content=json.dumps(parsed_content),
                        raw_response={'response': full_response}
                    )
                        
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")
                pass
                
            # Return raw response if JSON parsing fails
            return ModelResponse(
                content=full_response,
                raw_response={'response': full_response}
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
    "direction": "buy",
    "token": "SOL",
    "amount": "500",
    "slippage_bps": 200,
    "input_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "output_mint": "So11111111111111111111111111111111111111112"
}

注意事项 | Notes:
1. direction必须是"buy"或"sell" | direction must be "buy" or "sell"
2. slippage_bps是基点数，例如2%=200基点 | slippage_bps is in basis points, e.g., 2% = 200 bps
3. amount必须是正数 | amount must be positive"""
        
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
                    
                    # Map trade parameters
                    if 'trade_type' in result:
                        result['direction'] = result['trade_type']
                    if 'slippage' in result:
                        try:
                            result['slippage_bps'] = int(float(result['slippage']) * 100)
                        except (ValueError, TypeError):
                            result['slippage_bps'] = 250  # Default 2.5%
                    
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