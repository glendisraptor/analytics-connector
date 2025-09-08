#!/bin/bash
# fix_superset_issues.sh - Complete fix for Superset SQL Lab issues

echo "🔧 Fixing Superset SQL Lab Issues"
echo "=================================="

# Step 1: Stop Superset
echo "1️⃣ Stopping Superset..."
docker-compose down

# Step 2: Create fixed configuration
echo "2️⃣ Creating fixed superset_config.py..."

cat > superset_config.py << 'EOF'
import os
from celery.schedules import crontab

# Basic Configuration
ROW_LIMIT = 5000
SECRET_KEY = 'analytics-connector-superset-secret-key-2024-fixed'
SQLALCHEMY_DATABASE_URI = 'sqlite:///superset.db'

# FIX: Disable CSRF to resolve tabstateview errors
WTF_CSRF_ENABLED = False
WTF_CSRF_TIME_LIMIT = None

# FIX: Session configuration
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = 'Lax'

# FIX: Disable security headers that cause issues
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
    # FIX: Disable features that might cause issues
    "ALERT_REPORTS": False,
    "DYNAMIC_PLUGINS": False,
}

# SQL Lab Configuration
SQLLAB_CTAS_NO_LIMIT = True
SQL_MAX_ROW = 100000
SQLLAB_TIMEOUT = 300
SQLLAB_DEFAULT_DBID = None
SQLLAB_BACKEND_PERSISTENCE = True

# FIX: Database configuration
DATABASE_TIMEOUT = 30
DATABASE_RETRY_LIMIT = 3

# FIX: Simple cache to avoid Redis dependency issues
CACHE_CONFIG = {
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 300
}

# FIX: Logging configuration
ENABLE_PROXY_FIX = True
LOG_LEVEL = 'INFO'

# FIX: Custom app name
APP_NAME = "Analytics Connector"
EOF

echo "✅ Fixed superset_config.py created"

# Step 3: Create fixed Docker Compose
echo "3️⃣ Creating fixed docker-compose.yml..."

cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  superset:
    image: apache/superset:latest
    container_name: analytics_superset_fixed
    ports:
      - "8088:8088"
    volumes:
      - ./superset_config.py:/app/superset_config.py
      - superset_data:/app/superset_home
    environment:
      SUPERSET_CONFIG_PATH: /app/superset_config.py
      SUPERSET_SECRET_KEY: analytics-connector-superset-secret-key-2024-fixed
      # FIX: Additional environment variables
      FLASK_ENV: production
      SUPERSET_ENV: production
    command: >
      sh -c "
        echo '🔧 Starting Superset with fixes...' &&
        superset db upgrade &&
        echo '👤 Creating admin user...' &&
        superset fab create-admin --username admin --firstname Admin --lastname User --email admin@analytics-connector.com --password admin &&
        echo '⚙️ Initializing Superset...' &&
        superset init &&
        echo '🚀 Starting Superset server...' &&
        superset run -h 0.0.0.0 -p 8088 --with-threads --reload --debugger
      "
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8088/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  superset_data:
EOF

echo "✅ Fixed docker-compose.yml created"

# Step 4: Clean up old data (optional)
echo "4️⃣ Cleaning up old Superset data..."
read -p "Do you want to remove old Superset data? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker volume rm $(docker volume ls -q | grep superset) 2>/dev/null || true
    echo "✅ Old data cleaned"
else
    echo "⏭️ Keeping existing data"
fi

# Step 5: Start Superset with fixes
echo "5️⃣ Starting Superset with fixes..."
docker-compose up -d

echo ""
echo "⏳ Waiting for Superset to start (this may take 2-3 minutes)..."
echo "📊 Check progress with: docker-compose logs -f superset"
echo ""
echo "✅ Superset fixes applied!"
echo ""
echo "🔍 Test the fixes:"
echo "   1. Wait for startup to complete"
echo "   2. Visit: http://localhost:8088"
echo "   3. Login: admin / admin"
echo "   4. Go to SQL Lab"
echo "   5. Try running a query"
echo ""
echo "🎯 If SQL Lab still has issues:"
echo "   1. Check browser console for errors"
echo "   2. Try incognito/private mode"
echo "   3. Clear browser cache and cookies"

# ============================================================================
# test_etl_flow.py - Complete test of ETL job flow
# ============================================================================

cat > test_etl_flow.py << 'EOF'
#!/usr/bin/env python3
"""
Test script for complete ETL flow:
1. Create database connection
2. Trigger ETL job
3. Verify data in analytics database
4. Check Superset integration
"""

import requests
import time
import json
import psycopg2
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
SUPERSET_URL = "http://localhost:8088"

def test_complete_etl_flow():
    print("🧪 Testing Complete ETL Flow")
    print("=" * 40)
    
    # Step 1: Login to get auth token
    print("1️⃣ Authenticating with Analytics Connector...")
    auth_response = login_to_analytics_connector()
    if not auth_response:
        print("❌ Authentication failed")
        return False
    
    token = auth_response['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    
    # Step 2: Create test database connection
    print("2️⃣ Creating test database connection...")
    connection_data = {
        "name": "Test PostgreSQL Connection",
        "database_type": "postgresql",
        "credentials": {
            "host": "localhost",
            "port": 5432,
            "username": "analytics_user",
            "password": "analytics_password",
            "database_name": "analytics_connector"
        },
        "sync_frequency": "manual",
        "auto_sync_to_superset": True
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/connections/", 
                           json=connection_data, headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to create connection: {response.text}")
        return False
    
    connection = response.json()
    connection_id = connection['id']
    print(f"✅ Created connection with ID: {connection_id}")
    
    # Step 3: Wait for connection to be tested
    print("3️⃣ Waiting for connection test...")
    time.sleep(5)
    
    # Check connection status
    response = requests.get(f"{BASE_URL}/api/v1/connections/{connection_id}", 
                          headers=headers)
    connection_status = response.json()
    print(f"   Connection status: {connection_status['status']}")
    
    if connection_status['status'] != 'connected':
        print("❌ Connection not in 'connected' state")
        return False
    
    # Step 4: Trigger ETL job
    print("4️⃣ Triggering ETL job...")
    job_data = {
        "connection_id": connection_id,
        "job_type": "full_sync",
        "trigger_type": "manual"
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/jobs/trigger", 
                           json=job_data, headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to trigger ETL job: {response.text}")
        return False
    
    job = response.json()
    job_id = job['id']
    print(f"✅ ETL job started with ID: {job_id}")
    
    # Step 5: Monitor job progress
    print("5️⃣ Monitoring job progress...")
    for i in range(30):  # Wait up to 5 minutes
        response = requests.get(f"{BASE_URL}/api/v1/jobs/{job_id}", 
                              headers=headers)
        job_status = response.json()
        
        print(f"   Job status: {job_status['status']}")
        
        if job_status['status'] == 'completed':
            print(f"✅ ETL job completed! Processed {job_status['records_processed']} records")
            break
        elif job_status['status'] == 'failed':
            print(f"❌ ETL job failed: {job_status.get('error_message', 'Unknown error')}")
            return False
        
        time.sleep(10)
    else:
        print("⏰ ETL job taking longer than expected")
    
    # Step 6: Verify data in analytics database
    print("6️⃣ Verifying data in analytics database...")
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="analytics_user",
            password="analytics_password",
            database="analytics_data"
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        tables = cursor.fetchall()
        
        print(f"   Found {len(tables)} tables in analytics database:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"     - {table[0]}: {count} records")
        
        conn.close()
        print("✅ Analytics database verification completed")
        
    except Exception as e:
        print(f"❌ Failed to verify analytics database: {e}")
        return False
    
    # Step 7: Check Superset integration
    print("7️⃣ Checking Superset integration...")
    try:
        response = requests.get(f"{SUPERSET_URL}/health")
        if response.status_code == 200:
            print("✅ Superset is accessible")
            print(f"   Visit {SUPERSET_URL} to explore your data")
            print("   Login: admin / admin")
        else:
            print("⚠️ Superset health check failed")
    except:
        print("⚠️ Could not connect to Superset")
    
    print("\n🎉 ETL Flow Test Completed!")
    print("\n📋 Summary:")
    print(f"   • Connection ID: {connection_id}")
    print(f"   • Job ID: {job_id}")
    print(f"   • Analytics Database: {len(tables)} tables")
    print(f"   • Superset: {SUPERSET_URL}")
    
    return True

def login_to_analytics_connector() -> Dict[str, Any]:
    """Login to Analytics Connector and get auth token"""
    try:
        # Try with test credentials
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", data=login_data)
        if response.status_code == 200:
            return response.json()
        
        print("ℹ️ Default admin login failed, you may need to create a user first")
        return None
        
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return None

if __name__ == "__main__":
    test_complete_etl_flow()
EOF

chmod +x test_etl_flow.py

echo ""
echo "📁 Created test_etl_flow.py"
echo "   Run with: python test_etl_flow.py"

# ============================================================================
# Quick commands summary
# ============================================================================

echo ""
echo "🎯 Quick Commands Summary:"
echo "=========================="
echo ""
echo "# Fix and restart Superset:"
echo "bash fix_superset_issues.sh"
echo ""
echo "# Test complete ETL flow:"
echo "python test_etl_flow.py"
echo ""
echo "# Monitor Superset logs:"
echo "docker-compose logs -f superset"
echo ""
echo "# Trigger ETL via API:"
echo "curl -X POST http://localhost:8000/api/v1/jobs/trigger \\"
echo "  -H 'Authorization: Bearer YOUR_TOKEN' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"connection_id\": 1, \"job_type\": \"full_sync\"}'"
echo ""
echo "# Check job status:"
echo "curl http://localhost:8000/api/v1/jobs/ \\"
echo "  -H 'Authorization: Bearer YOUR_TOKEN'"