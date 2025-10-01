import os
from datetime import timedelta
from flask import Flask, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # JWT Configuration - CRITICAL
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', app.config['SECRET_KEY'])
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
    app.config['JWT_TOKEN_LOCATION'] = ['headers']
    app.config['JWT_HEADER_NAME'] = 'Authorization'
    app.config['JWT_HEADER_TYPE'] = 'Bearer'
    
    # File upload configuration
    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
    app.config['RESULTS_FOLDER'] = os.getenv('RESULTS_FOLDER', 'results')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    
    # Superset configuration
    app.config['SUPERSET_URL'] = os.getenv('SUPERSET_URL', 'http://localhost:8088')
    app.config['SUPERSET_USERNAME'] = os.getenv('SUPERSET_USERNAME', 'admin')
    app.config['SUPERSET_PASSWORD'] = os.getenv('SUPERSET_PASSWORD', 'admin')
    
    # Groq API configuration
    app.config['GROQ_API_KEY'] = os.getenv('GROQ_API_KEY')
    app.config['GROQ_API_URL'] = os.getenv('GROQ_API_URL', 'https://api.groq.com/openai/v1/chat/completions')
    app.config['GROQ_MODEL'] = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')
    
    # Initialize extensions with app
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    # CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    CORS(app, 
    resources={r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type", "Authorization"]
    }},
    supports_credentials=True
    )
    
    # Create upload directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)
    
    # JWT Error Handlers - ADD THESE
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'error': 'Token expired',
            'message': 'Your session has expired. Please login again.'
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        print(f"JWT Invalid token error: {error}")
        return jsonify({
            'error': 'Invalid token',
            'message': str(error)
        }), 422
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        print(f"JWT Unauthorized error: {error}")
        return jsonify({
            'error': 'Authorization required',
            'message': 'Access token is missing'
        }), 401
    
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'error': 'Token revoked',
            'message': 'This token has been revoked'
        }), 401
    
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        from routes.auth import token_blacklist
        jti = jwt_payload.get('jti')
        return jti in token_blacklist
    
    # Import models here to avoid circular imports
    with app.app_context():
        from models import models
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.database_connections import db_connections_bp
    from routes.document_extraction import document_extraction_bp
    from routes.superset import superset_bp
    from routes.etl import etl_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(db_connections_bp, url_prefix='/api/connections')
    app.register_blueprint(document_extraction_bp, url_prefix='/api/documents')
    app.register_blueprint(superset_bp, url_prefix='/api/superset')
    app.register_blueprint(etl_bp, url_prefix='/api/etl')
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {
            'status': 'healthy',
            'database': 'connected' if db.engine else 'disconnected',
            'superset_configured': bool(app.config['SUPERSET_URL']),
            'groq_configured': bool(app.config['GROQ_API_KEY'])
        }
    
    return app

# Create app instance
app = create_app()

if __name__ == '__main__':
    # Create all database tables
    with app.app_context():
        db.create_all()
        print("✓ Database tables created")
    
    print("\n" + "="*60)
    print(" Analytics Connector API Server")
    print("="*60)
    print(f"✓ Server running on http://0.0.0.0:8000")
    print(f"✓ Database: {os.getenv('DATABASE_URL', 'Not configured')}")
    print(f"✓ JWT Secret configured: {bool(os.getenv('JWT_SECRET_KEY'))}")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=8000)