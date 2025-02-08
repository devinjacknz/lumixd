"""
Solana DeFi Agent Web Application
"""

from flask import Flask, render_template
from flask_cors import CORS
from src.web.routes.defi_routes import defi

app = Flask(__name__)
app.config['PREFERRED_URL_SCHEME'] = 'https'
app.config['PROXY_FIX_X_PROTO'] = 1
app.config['PROXY_FIX_X_HOST'] = 1
app.config['PROXY_FIX_X_PREFIX'] = 1

from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_proto=1,
    x_host=1,
    x_prefix=1
)

CORS(app, resources={
    r"/api/*": {
        "origins": ["https://pr-playbook-app-tunnel-jncimc99.devinapps.com"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "X-User-ID", "X-Wallet-Key", "Authorization"],
        "supports_credentials": True
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
