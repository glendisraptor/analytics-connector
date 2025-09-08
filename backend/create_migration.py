"""
Script to create initial database migration
"""
import subprocess
import sys
import os

def run_command(command):
    """Run a shell command and handle errors"""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    
    print(f"Success: {result.stdout}")
    return True

def main():
    print("🔧 Setting up Alembic for Analytics Connector")
    print("=" * 50)
    
    # Check if alembic directory exists
    if not os.path.exists("alembic"):
        print("📁 Initializing Alembic...")
        if not run_command("alembic init alembic"):
            print("❌ Failed to initialize Alembic")
            sys.exit(1)
        print("✅ Alembic initialized")
    else:
        print("📁 Alembic directory already exists")
    
    # Create initial migration
    print("\n📝 Creating initial migration...")
    if not run_command('alembic revision --autogenerate -m "Initial database schema"'):
        print("❌ Failed to create migration")
        sys.exit(1)
    
    print("✅ Initial migration created")
    
    # Apply migration
    print("\n🚀 Applying migration to database...")
    if not run_command("alembic upgrade head"):
        print("❌ Failed to apply migration")
        sys.exit(1)
    
    print("✅ Database schema created successfully!")
    
    print("\n" + "=" * 50)
    print("🎉 Database setup complete!")
    print("\n📋 Available Alembic commands:")
    print("  alembic revision --autogenerate -m 'description'  # Create new migration")
    print("  alembic upgrade head                               # Apply migrations")
    print("  alembic downgrade -1                               # Rollback last migration")
    print("  alembic history                                    # View migration history")
    print("  alembic current                                    # Show current migration")

if __name__ == "__main__":
    main()
