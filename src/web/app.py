from flask import Flask, render_template, jsonify, request
import logging
import os
from datetime import datetime
from src.data.jupiter_client_v2 import JupiterClientV2
from trading_strategy_v2 import TradingStrategy

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    filename='user_operations.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/execute_trade', methods=['POST'])
async def execute_trade():
    try:
        instruction = request.json.get('instruction')
        user_id = request.headers.get('X-User-ID', 'anonymous')
        
        # Log trade attempt
        await logging_service.log_trade_attempt(instruction, user_id)
        
        client = JupiterClientV2()
        strategy = TradingStrategy()
        
        quote = await client.get_quote(
            input_mint='So11111111111111111111111111111111111111112',
            output_mint='6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump',
            amount='1000000000'
        )
        
        if quote:
            result = await client.execute_swap(quote, os.getenv('WALLET_KEY'))
            response_data = {
                'status': 'success',
                'transaction': result,
                'solscan_url': f"https://solscan.io/tx/{result}" if result else None
            }
            # Log successful trade
            await logging_service.log_trade_result(response_data, user_id)
            return jsonify(response_data)
        
        error_data = {
            'status': 'error',
            'message': 'Failed to get quote'
        }
        # Log quote failure
        await logging_service.log_error('Failed to get quote', {'instruction': instruction}, user_id)
        return jsonify(error_data), 400
        
    except Exception as e:
        error_data = {
            'status': 'error',
            'message': str(e)
        }
        # Log execution error
        await logging_service.log_error(str(e), {'instruction': instruction}, user_id)
        return jsonify(error_data), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
