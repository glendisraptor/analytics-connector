"""
Health Check Routes
System health and status endpoints
"""
from flask import Blueprint, jsonify, current_app
from app import db
from models import DocumentTable, DocumentResult
from sqlalchemy import text

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    api_key_configured = bool(
        current_app.config['GROQ_API_KEY'] and 
        current_app.config['GROQ_API_KEY'] != 'your_groq_api_key_here'
    )
    
    try:
        db.session.execute(text("SELECT 1"))
        db_ok = True
        table_count = DocumentTable.query.filter_by(is_active=True).count()
        result_count = DocumentResult.query.count()
    except Exception as e:
        print(f"Health check error: {e}")
        db_ok = False
        table_count = 0
        result_count = 0

    return jsonify({
        'status': 'healthy' if api_key_configured and db_ok else 'degraded',
        'extraction_method': 'groq+ocr_fallback',
        'api_configured': api_key_configured,
        'db_connected': db_ok,
        'model': current_app.config['GROQ_MODEL'],
        'tables_configured': table_count,
        'total_results': result_count,
    }), 200