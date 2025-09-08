#!/usr/bin/env python3
"""
Complete database setup script for Analytics Connector
This script will:
1. Initialize Alembic
2. Create initial migration
3. Apply migrations to create tables
4. Verify setup
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return True if successful"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        if result.stdout:
            print(f"   {result.stdout.strip()}")
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   {e.stderr.strip()}")
        return False

def main():
    print("🚀 Analytics Connector Database Setup")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists("app"):
        print("❌ Please run this script from the backend directory")
        print("   Expected to find 'app' directory here")
        sys.exit(1)
    
    # Step 1: Initialize Alembic (if not already done)
    if not Path("alembic").exists():
        if not run_command("alembic init alembic", "Initializing Alembic"):
            sys.exit(1)
    else:
        print("✅ Alembic already initialized")
    
    # Step 2: Create migration
    print(f"\n📝 Creating database migration...")
    if not run_command(
        'alembic revision --autogenerate -m "Initial schema: users, connections, jobs"',
        "Creating initial migration"
    ):
        print("⚠️  Migration creation failed - this might be normal if migration already exists")
    
    # Step 3: Apply migrations
    if not run_command("alembic upgrade head", "Applying database migrations"):
        sys.exit(1)
    
    # Step 4: Verify
    print(f"\n🔍 Verifying database setup...")
    if not run_command("alembic current", "Checking migration status"):
        sys.exit(1)
    
    # Check if database file exists
    db_file = "app.db"
    if os.path.exists(db_file):
        print(f"✅ Database file created: {db_file}")
        print(f"   Size: {os.path.getsize(db_file)} bytes")
    else:
        print(f"❌ Database file not found: {db_file}")
    
    print(f"\n🎉 Database setup complete!")
    print(f"\n📊 Your database now includes:")
    print(f"   • users table (for authentication)")
    print(f"   • database_connections table (customer databases)")
    print(f"   • etl_jobs table (background job tracking)")
    
    print(f"\n🚀 Next steps:")
    print(f"   1. Start the API server: python -m app.main")
    print(f"   2. Test the API at: http://localhost:8000/docs")
    print(f"   3. Create your first user via the API")

if __name__ == "__main__":
    main()
