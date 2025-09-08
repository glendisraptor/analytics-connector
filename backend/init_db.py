"""
Database initialization script
Run this after setting up the environment to create the database schema
"""
import subprocess
import sys
import os
from pathlib import Path

def check_alembic_setup():
    """Check if Alembic is properly set up"""
    alembic_dir = Path("alembic")
    alembic_ini = Path("alembic.ini")
    
    if not alembic_ini.exists():
        print("❌ alembic.ini not found. Please run alembic init first.")
        return False
    
    if not alembic_dir.exists():
        print("❌ alembic directory not found. Please run alembic init first.")
        return False
    
    return True

def run_alembic_command(command, description):
    """Run an Alembic command with error handling"""
    print(f"🔧 {description}...")
    result = subprocess.run(f"alembic {command}", shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Failed: {result.stderr}")
        return False
    
    if result.stdout:
        print(f"✅ {result.stdout}")
    else:
        print(f"✅ {description} completed successfully")
    
    return True

def main():
    print("🚀 Analytics Connector Database Initialization")
    print("=" * 55)
    
    # Check if we're in the right directory
    if not os.path.exists("app"):
        print("❌ Please run this script from the backend directory")
        sys.exit(1)
    
    # Check Alembic setup
    if not check_alembic_setup():
        print("\n🔧 Setting up Alembic...")
        if not run_alembic_command("init alembic", "Initializing Alembic"):
            sys.exit(1)
    
    # Check current migration status
    print("\n📊 Checking current database status...")
    result = subprocess.run("alembic current", shell=True, capture_output=True, text=True)
    
    if "head" not in result.stdout.lower():
        print("📝 Creating initial migration...")
        
        # Create initial migration
        if not run_alembic_command(
            'revision --autogenerate -m "Initial database schema with users and connections"',
            "Creating initial migration"
        ):
            sys.exit(1)
        
        # Apply migration
        if not run_alembic_command("upgrade head", "Applying database migrations"):
            sys.exit(1)
    else:
        print("✅ Database is up to date")
    
    print("\n" + "=" * 55)
    print("🎉 Database initialization complete!")
    print("\n📋 Your database now includes:")
    print("  • users table (authentication)")
    print("  • database_connections table (customer DB connections)")
    print("  • etl_jobs table (background job tracking)")
    
    print("\n🔍 Next steps:")
    print("  1. Start the FastAPI server: python -m app.main")
    print("  2. Visit http://localhost:8000/docs for API documentation")
    print("  3. Create a user account via /api/v1/auth/register")

if __name__ == "__main__":
    main()