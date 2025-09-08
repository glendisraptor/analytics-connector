#!/usr/bin/env python3
"""
ETL Debugging Script - Diagnose why ETL jobs aren't showing up
This script will check every step of the ETL process
"""

import requests
import psycopg2
import json
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "http://localhost:8000"
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "admin",
    "database": "analytics_connector"
}

def debug_etl_pipeline():
    print("🔍 ETL Pipeline Diagnostic Tool")
    print("=" * 50)
    
    # Step 1: Check API connectivity
    print("\n1️⃣ Testing API Connectivity")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend API is accessible")
        else:
            print(f"❌ Backend API responded with status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to backend API: {e}")
        print("   Make sure backend is running at http://localhost:8000")
        return False
    
    # Step 2: Test authentication
    print("\n2️⃣ Testing Authentication")
    token = test_authentication()
    if not token:
        return False
    
    headers = {'Authorization': f'Bearer {token}'}
    
    # Step 3: Check database connections
    print("\n3️⃣ Checking Database Connections")
    connections = check_connections(headers)
    if not connections:
        return False
    
    # Step 4: Check ETL endpoints
    print("\n4️⃣ Testing ETL Endpoints")
    if not test_etl_endpoints(headers):
        return False
    
    # Step 5: Check database tables
    print("\n5️⃣ Checking Database Tables")
    if not check_database_tables():
        return False
    
    # Step 6: Test ETL job creation
    print("\n6️⃣ Testing ETL Job Creation")
    connected_connections = [c for c in connections if c.get('status') == 'connected']
    
    if not connected_connections:
        print("❌ No connected database connections found")
        print("   You need at least one connection with status='connected' to run ETL jobs")
        print("\n💡 To fix this:")
        print("   1. Go to /connections in your app")
        print("   2. Add a database connection")
        print("   3. Make sure connection test passes (status becomes 'connected')")
        return False
    
    print(f"✅ Found {len(connected_connections)} connected database(s)")
    
    # Try to create an ETL job
    connection_id = connected_connections[0]['id']
    connection_name = connected_connections[0]['name']
    
    print(f"   Testing ETL job creation for: {connection_name} (ID: {connection_id})")
    
    job_result = create_test_etl_job(connection_id, headers)
    if job_result:
        print("✅ ETL job creation successful!")
        
        # Wait a moment and check job status
        time.sleep(2)
        jobs = get_etl_jobs(headers)
        
        if jobs:
            print(f"✅ Found {len(jobs)} ETL job(s) in database")
            for job in jobs[:3]:  # Show first 3 jobs
                print(f"   • Job {job['id']}: {job['status']} - {job.get('records_processed', 0)} records")
        else:
            print("⚠️  ETL job created but not found in jobs list")
    
    # Step 7: Check analytics database
    print("\n7️⃣ Checking Analytics Database")
    check_analytics_database()
    
    print("\n🎉 ETL Pipeline Diagnostic Complete!")
    print("\n📋 Summary:")
    print(f"   • Backend API: ✅ Working")
    print(f"   • Authentication: ✅ Working") 
    print(f"   • Database connections: {len(connections)} total, {len(connected_connections)} connected")
    print(f"   • ETL endpoints: ✅ Available")
    print(f"   • ETL job creation: {'✅ Working' if job_result else '❌ Failed'}")
    
    return True

def test_authentication() -> Optional[str]:
    """Test authentication and return token"""
    
    # Try default admin credentials first
    credentials_to_try = [
        {"username": "admin", "password": "admin123"},
        {"username": "admin", "password": "admin"},
        {"username": "glen.mogane", "password": "admin123"},
    ]
    
    for creds in credentials_to_try:
        try:
            response = requests.post(f"{BASE_URL}/api/v1/auth/login", data=creds)
            if response.status_code == 200:
                token = response.json().get('access_token')
                print(f"✅ Authentication successful with user: {creds['username']}")
                return token
        except Exception as e:
            continue
    
    print("❌ Authentication failed with all default credentials")
    print("💡 To fix this:")
    print("   1. Make sure you have a user account")
    print("   2. Try registering at /register first")
    print("   3. Or create user via API: POST /api/v1/auth/register")
    
    return None

def check_connections(headers: Dict[str, str]) -> list:
    """Check database connections"""
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/connections/", headers=headers)
        if response.status_code == 200:
            connections = response.json()
            print(f"✅ Found {len(connections)} database connection(s)")
            
            for conn in connections:
                status_emoji = "✅" if conn['status'] == 'connected' else "❌" if conn['status'] == 'failed' else "⏳"
                print(f"   {status_emoji} {conn['name']}: {conn['status']} ({conn['database_type']})")
            
            return connections
        else:
            print(f"❌ Failed to get connections: {response.status_code}")
            print(f"   Response: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Error checking connections: {e}")
        return []

def test_etl_endpoints(headers: Dict[str, str]) -> bool:
    """Test if ETL endpoints are available"""
    
    endpoints_to_test = [
        "/api/v1/jobs/",
        "/api/v1/jobs/trigger"
    ]
    
    for endpoint in endpoints_to_test:
        try:
            # Test GET endpoints
            if endpoint.endswith('/'):
                response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
                if response.status_code == 200:
                    print(f"✅ {endpoint} - Available")
                else:
                    print(f"⚠️  {endpoint} - Status: {response.status_code}")
            else:
                print(f"📋 {endpoint} - POST endpoint (will test in job creation)")
        except Exception as e:
            print(f"❌ {endpoint} - Error: {e}")
            return False
    
    return True

def check_database_tables() -> bool:
    """Check if required database tables exist"""
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Check required tables
        required_tables = ['users', 'database_connections', 'etl_jobs']
        
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = ANY(%s)
        """, (required_tables,))
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        print(f"✅ Database connection successful")
        print(f"   Required tables: {required_tables}")
        print(f"   Found tables: {existing_tables}")
        
        missing_tables = set(required_tables) - set(existing_tables)
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            print("💡 Run your database setup/migration scripts")
            return False
        
        # Check table contents
        for table in required_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   • {table}: {count} records")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("💡 Check your PostgreSQL connection and credentials")
        return False

def create_test_etl_job(connection_id: int, headers: Dict[str, str]) -> bool:
    """Try to create a test ETL job"""
    
    job_data = {
        "connection_id": connection_id,
        "job_type": "full_sync",
        "trigger_type": "manual"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/jobs/trigger", 
                               json=job_data, headers=headers)
        
        if response.status_code == 200:
            job = response.json()
            print(f"✅ ETL job created: ID {job.get('id')}")
            return True
        else:
            print(f"❌ ETL job creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating ETL job: {e}")
        return False

def get_etl_jobs(headers: Dict[str, str]) -> list:
    """Get list of ETL jobs"""
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/jobs/", headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"⚠️  Could not fetch jobs: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error fetching jobs: {e}")
        return []

def check_analytics_database():
    """Check analytics database for extracted data"""
    
    analytics_config = DB_CONFIG.copy()
    analytics_config['database'] = 'analytics_data'
    
    try:
        conn = psycopg2.connect(**analytics_config)
        cursor = conn.cursor()
        
        # Check for analytics tables
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name LIKE 'conn_%'
        """)
        
        analytics_tables = [row[0] for row in cursor.fetchall()]
        
        if analytics_tables:
            print(f"✅ Found {len(analytics_tables)} analytics tables:")
            for table in analytics_tables[:5]:  # Show first 5
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   • {table}: {count} records")
        else:
            print("📋 No analytics tables found yet")
            print("   Analytics tables will appear after successful ETL jobs")
        
        conn.close()
        
    except Exception as e:
        print(f"⚠️  Could not check analytics database: {e}")

def main():
    """Main diagnostic function"""
    success = debug_etl_pipeline()
    
    if not success:
        print("\n🔧 Common Issues and Fixes:")
        print("=" * 30)
        print("1. Backend not running:")
        print("   → Start with: python -m app.main or docker-compose up")
        print("\n2. No user account:")
        print("   → Register at /register or create via API")
        print("\n3. No database connections:")
        print("   → Add connections at /connections page")
        print("\n4. Connection not 'connected':")
        print("   → Check database credentials and connectivity")
        print("\n5. Missing database tables:")
        print("   → Run database setup scripts")

if __name__ == "__main__":
    main()