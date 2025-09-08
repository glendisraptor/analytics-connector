"""
Fix for Superset SQL Lab tabstateview errors
The issue is usually related to session/CSRF token problems
"""

# Updated superset_config.py with fixes
SUPERSET_CONFIG_FIXES = '''
import os
from celery.schedules import crontab

# Basic Configuration
ROW_LIMIT = 5000
SECRET_KEY = 'analytics-connector-superset-secret-key-2024'
SQLALCHEMY_DATABASE_URI = 'sqlite:///superset.db'

# Fix for SQL Lab errors
WTF_CSRF_ENABLED = False  # Disable CSRF for now to fix tabstateview errors
WTF_CSRF_TIME_LIMIT = None

# Session Configuration
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
SESSION_COOKIE_SAMESITE = 'Lax'

# Fix for iframe embedding (if needed)
TALISMAN_ENABLED = False
TALISMAN_CONFIG = {
    "force_https": False,
    "frame_options": "ALLOWALL",
}

# Feature Flags
FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
    "DASHBOARD_CROSS_FILTERS": True,
    "DASHBOARD_NATIVE_FILTERS": True,
    "GLOBAL_ASYNC_QUERIES": True,
    "VERSIONED_EXPORT": True,
    "ENABLE_JAVASCRIPT_CONTROLS": True,
}

# SQL Lab Configuration
SQLLAB_CTAS_NO_LIMIT = True
SQL_MAX_ROW = 100000
SQLLAB_TIMEOUT = 300
SQLLAB_DEFAULT_DBID = None

# Database Configuration
DATABASE_TIMEOUT = 30
DATABASE_RETRY_LIMIT = 3

# Cache Configuration (optional, but helps with performance)
CACHE_CONFIG = {
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 300
}

# Logging
ENABLE_PROXY_FIX = True
LOG_LEVEL = 'INFO'

# Custom CSS (optional)
APP_NAME = "Analytics Connector - Superset"
'''

def fix_superset_config():
    """Apply fixes to Superset configuration"""
    print("🔧 Applying Superset configuration fixes...")
    
    with open("superset_config.py", "w") as f:
        f.write(SUPERSET_CONFIG_FIXES)
    
    print("✅ Superset configuration updated")
    print("🔄 Please restart Superset for changes to take effect:")
    print("   docker-compose restart superset")

if __name__ == "__main__":
    fix_superset_config()