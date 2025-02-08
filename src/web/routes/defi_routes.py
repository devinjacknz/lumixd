"""
Solana DeFi Agent API Routes
Handles chat interactions, strategy generation, and trade execution
"""

from flask import Blueprint, jsonify, request
from src.agents.defi_dialogue_agent import DefiDialogueAgent
from src.services.logging_service import logging_service

defi = Blueprint('defi', __name__)
agent = DefiDialogueAgent()

@defi.route('/api/chat', methods=['POST'])
async def chat():
    """Handle chat interactions and strategy generation"""
    try:
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'message': '请求必须是JSON格式 | Request must be JSON'
            }), 400, {'Content-Type': 'application/json'}
            
        user_id = request.headers.get('X-User-ID', 'anonymous')
        message = request.json.get('message')
        
        if not message:
            return jsonify({
                'status': 'error',
                'message': '消息不能为空 | Message cannot be empty'
            }), 400, {'Content-Type': 'application/json'}
            
        # Process user input
        result = await agent.process_user_input(message, user_id)
        return jsonify(result), 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        await logging_service.log_error(str(e), {'route': '/api/chat'}, user_id)
        return jsonify({
            'status': 'error',
            'message': f'系统错误 | System error: {str(e)}'
        }), 500, {'Content-Type': 'application/json'}

@defi.route('/api/execute_trade', methods=['POST'])
async def execute_trade():
    """Execute trade with wallet key"""
    try:
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'message': '请求必须是JSON格式 | Request must be JSON'
            }), 400, {'Content-Type': 'application/json'}
            
        user_id = request.headers.get('X-User-ID', 'anonymous')
        wallet_key = request.headers.get('X-Wallet-Key')
        
        if not wallet_key:
            return jsonify({
                'status': 'error',
                'message': '需要提供钱包密钥 | Wallet key is required'
            }), 400, {'Content-Type': 'application/json'}
            
        # Execute trade
        result = await agent.execute_trade(wallet_key, user_id)
        return jsonify(result), 200 if result['status'] == 'success' else 400, {'Content-Type': 'application/json'}
        
    except Exception as e:
        await logging_service.log_error(str(e), {'route': '/api/execute_trade'}, user_id)
        return jsonify({
            'status': 'error',
            'message': f'交易错误 | Trade error: {str(e)}'
        }), 500, {'Content-Type': 'application/json'}

@defi.route('/api/clear_context', methods=['POST'])
async def clear_context():
    """Clear the current dialogue context"""
    try:
        user_id = request.headers.get('X-User-ID', 'anonymous')
        agent.clear_context()
        
        await logging_service.log_user_action(
            'clear_context',
            {'message': 'Context cleared'},
            user_id
        )
        
        return jsonify({
            'status': 'success',
            'message': '对话上下文已清除 | Dialogue context cleared'
        }), 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        await logging_service.log_error(str(e), {'route': '/api/clear_context'}, user_id)
        return jsonify({
            'status': 'error',
            'message': f'系统错误 | System error: {str(e)}'
        }), 500, {'Content-Type': 'application/json'}
