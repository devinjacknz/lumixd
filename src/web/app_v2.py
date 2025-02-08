from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
from datetime import datetime
from src.data.jupiter_client_v2 import JupiterClientV2
from trading_strategy_v2 import TradingStrategy
from src.services.logging_service import logging_service

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "X-User-ID"]
    }
})

@app.route('/')
async def index():
    """Serve the main trading interface"""
    try:
        user_id = request.headers.get('X-User-ID', 'anonymous')
        await logging_service.log_user_action(
            'page_view',
            {'page': 'index'},
            user_id
        )
        return render_template('index.html')
    except Exception as e:
        await logging_service.log_error(str(e), {'route': '/'}, user_id)
        return render_template('index.html')

@app.route('/api/execute_trade', methods=['POST', 'OPTIONS'])
async def execute_trade():
    """Execute trade with comprehensive logging"""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,X-User-ID')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response

    try:
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'message': '请求必须是JSON格式 | Request must be JSON'
            }), 400, {'Content-Type': 'application/json'}

        user_id = request.headers.get('X-User-ID', 'anonymous')
        instruction = request.json.get('instruction')
        
        if not instruction:
            return jsonify({
                'status': 'error',
                'message': '无效的交易指令 | Invalid trade instruction'
            }), 400, {'Content-Type': 'application/json'}

        # Log trade attempt
        try:
            await logging_service.log_trade_attempt(instruction, user_id)
        except Exception as e:
            print(f"Logging error: {str(e)}")  # Debug log

        try:
            # Initialize trading components
            client = JupiterClientV2()
            strategy = TradingStrategy()

            # Get quote
            quote = await client.get_quote(
                input_mint='So11111111111111111111111111111111111111112',
                output_mint='6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump',
                amount='1000000000'
            )

            if not quote:
                await logging_service.log_error('Failed to get quote', {'instruction': instruction}, user_id)
                return jsonify({
                    'status': 'error',
                    'message': '无法获取报价 | Failed to get quote'
                }), 400
        except Exception as e:
            await logging_service.log_error(str(e), {'instruction': instruction}, user_id)
            return jsonify({
                'status': 'error',
                'message': f'交易执行错误 | Trade execution error: {str(e)}'
            }), 500

        # Execute trade
        result = await client.execute_swap(quote, os.getenv('WALLET_KEY'))
        if result:
            response_data = {
                'status': 'success',
                'transaction': result,
                'solscan_url': f"https://solscan.io/tx/{result}"
            }
            await logging_service.log_trade_result(response_data, user_id)
            return jsonify(response_data)

        await logging_service.log_error('Trade execution failed', {'instruction': instruction}, user_id)
        return jsonify({
            'status': 'error',
            'message': '交易执行失败 | Trade execution failed'
        }), 400
        
    except Exception as e:
        error_data = {
            'status': 'error',
            'message': str(e)
        }
        # Log execution error
        await logging_service.log_error(
            str(e),
            {'instruction': instruction},
            user_id
        )
        return jsonify(error_data), 500

@app.route('/api/recent_trades', methods=['GET'])
async def get_recent_trades():
    """Get recent trade history with logging"""
    try:
        user_id = request.headers.get('X-User-ID', 'anonymous')
        limit = int(request.args.get('limit', 100))
        
        # Log history request
        await logging_service.log_user_action(
            'trade_history_request',
            {'limit': limit},
            user_id
        )
        
        recent_actions = await logging_service.get_recent_actions(limit)
        return jsonify(recent_actions)
        
    except Exception as e:
        await logging_service.log_error(
            str(e),
            {'route': '/api/recent_trades'},
            user_id
        )
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=8080)
