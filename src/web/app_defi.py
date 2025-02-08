"""
Solana DeFi Agent Web Application
"""

from flask import Flask, render_template
from flask_cors import CORS
from src.web.routes.defi_routes import defi

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "X-User-ID", "X-Wallet-Key"]
    }
})

# Register blueprints
app.register_blueprint(defi)

@app.route('/')
def index():
    """Serve the main DeFi agent interface"""
    return render_template('defi_agent.html')

if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=8080)
