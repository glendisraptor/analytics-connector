"""
Routes package for Analytics Connector
"""
from .auth import auth_bp
from .database_connections import db_connections_bp
from .document_extraction import document_extraction_bp
from .superset import superset_bp
from .etl import etl_bp

__all__ = [
    'auth_bp',
    'db_connections_bp',
    'document_extraction_bp',
    'superset_bp',
    'etl_bp'
]