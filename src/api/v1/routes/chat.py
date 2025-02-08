"""
Chat Route for DeFi Agent
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from typing import Dict
from src.models.deepseek_model import DeepSeekModel
from src.services.logging_service import logging_service
from src.data.chainstack_client import ChainStackClient

# Bilingual error messages
ERROR_MESSAGES: Dict[str, Dict[str, str]] = {
    'model_error': {
        'en': 'Error generating response from model',
        'zh': '生成模型响应时出错'
    },
    'token_error': {
        'en': 'Error fetching token information',
        'zh': '获取代币信息时出错'
    },
    'invalid_request': {
        'en': 'Invalid request format',
        'zh': '无效的请求格式'
    },
    'server_error': {
        'en': 'Internal server error',
        'zh': '服务器内部错误'
    }
}

router = APIRouter()
deepseek_model = DeepSeekModel(model_name="deepseek-r1:1.5b")
chainstack_client = ChainStackClient()

@router.post("/chat")
async def chat(request: Request):
    """Handle chat messages with DeFi agent"""
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Accept, X-User-ID, X-Wallet-Connected"
    }
    
    try:
        try:
            data = await request.json()
            message = data.get("message", "")
            wallet_connected = data.get("wallet_connected", False)
        except Exception:
            error_msg = ERROR_MESSAGES['invalid_request']
            await logging_service.log_error(
                f"{error_msg['zh']} | {error_msg['en']}",
                {'raw_data': str(await request.body())},
                request.headers.get('X-User-ID', 'anonymous')
            )
            return JSONResponse(
                content={
                    "status": "error",
                    "message": f"{error_msg['zh']} | {error_msg['en']}"
                },
                status_code=400,
                headers=headers
            )
        
        # Log user message
        await logging_service.log_user_action(
            'chat_message',
            {'message': message, 'wallet_connected': wallet_connected},
            request.headers.get('X-User-ID', 'anonymous')
        )
        
        # Get token info if message contains token analysis request
        token_info = None
        if "分析" in message and ("代币" in message or "token" in message.lower()):
            try:
                token_symbol = "SOL"  # Default to SOL for now
                token_info = await chainstack_client.get_token_data(token_symbol)
            except Exception as e:
                error_msg = ERROR_MESSAGES['token_error']
                await logging_service.log_error(
                    f"{error_msg['zh']} | {error_msg['en']}",
                    {'error': str(e), 'token_symbol': token_symbol},
                    request.headers.get('X-User-ID', 'anonymous')
                )
        
        try:
            # Generate response using DeepSeek model
            response = deepseek_model.generate_response(
                system_prompt="你是一个专业的交易助手，帮助用户分析和执行交易。",
                user_content=message
            )
        except Exception as e:
            error_msg = ERROR_MESSAGES['model_error']
            await logging_service.log_error(
                f"{error_msg['zh']} | {error_msg['en']}",
                {'error': str(e), 'message': message},
                request.headers.get('X-User-ID', 'anonymous')
            )
            return JSONResponse(
                content={
                    "status": "error",
                    "message": f"{error_msg['zh']} | {error_msg['en']}"
                },
                status_code=500,
                headers=headers
            )
        
        # Format response with real data
        response_data = {
            "status": "success",
            "response": response.content,
            "requires_confirmation": False,
            "token_info": token_info
        }
        
        return JSONResponse(
            content=response_data,
            headers=headers
        )
            
    except Exception as e:
        error_msg = ERROR_MESSAGES['server_error']
        await logging_service.log_error(
            f"{error_msg['zh']} | {error_msg['en']}",
            {'error': str(e), 'message': message if 'message' in locals() else None},
            request.headers.get('X-User-ID', 'anonymous')
        )
        return JSONResponse(
            content={
                "status": "error",
                "message": f"{error_msg['zh']} | {error_msg['en']}: {str(e)}"
            },
            status_code=500,
            headers=headers
        )
