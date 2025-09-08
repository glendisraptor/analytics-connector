from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from ...db.database import get_db
from ...models.user import User
from ...models.connection import DatabaseConnection
from ...services.superset_integration import SupersetIntegration
from ...core.security import get_current_user
from ...core.config import settings

router = APIRouter()

@router.get("/superset-info")
async def get_superset_info():
    """Get Superset connection information"""
    return {
        "superset_url": settings.SUPERSET_URL,
        "login_url": f"{settings.SUPERSET_URL}/login/",
        "dashboard_url": f"{settings.SUPERSET_URL}/dashboard/list/",
        "sql_lab_url": f"{settings.SUPERSET_URL}/sqllab/",
        "default_credentials": {
            "username": "admin",
            "password": "admin"
        }
    }

@router.get("/connections-status")
async def get_analytics_connections_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analytics status for all user connections"""
    
    connections = db.query(DatabaseConnection)\
        .filter(DatabaseConnection.owner_id == current_user.id)\
        .all()
    
    analytics_status = []
    
    for connection in connections:
        status_info = {
            "connection_id": connection.id,
            "name": connection.name,
            "database_type": connection.database_type,
            "status": connection.status,
            "analytics_ready": connection.status == "connected",
            "last_sync": connection.last_sync,
            "superset_available": True,  # Assuming Superset is running
        }
        analytics_status.append(status_info)
    
    return {
        "connections": analytics_status,
        "superset_url": settings.SUPERSET_URL,
        "total_connections": len(connections),
        "analytics_ready": len([c for c in connections if c.status == "connected"])
    }

@router.post("/sync-all-to-superset")
async def sync_all_connections_to_superset(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sync all user's connected databases to Superset"""
    
    connections = db.query(DatabaseConnection)\
        .filter(
            DatabaseConnection.owner_id == current_user.id,
            DatabaseConnection.status == "connected",
            DatabaseConnection.is_active == True
        )\
        .all()
    
    if not connections:
        return {
            "message": "No connected databases found to sync",
            "synced_count": 0
        }
    
    superset_integration = SupersetIntegration()
    synced_count = 0
    failed_count = 0
    
    for connection in connections:
        try:
            success = superset_integration.sync_connection_to_superset(connection.id)
            if success:
                synced_count += 1
            else:
                failed_count += 1
        except Exception as e:
            print(f"Failed to sync connection {connection.id}: {e}")
            failed_count += 1
    
    return {
        "message": f"Sync completed: {synced_count} successful, {failed_count} failed",
        "synced_count": synced_count,
        "failed_count": failed_count,
        "total_connections": len(connections)
    }

@router.get("/sample-queries/{connection_id}")
async def get_sample_queries(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get sample SQL queries for a connection"""
    
    connection = db.query(DatabaseConnection)\
        .filter(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.owner_id == current_user.id
        )\
        .first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    # Generate sample queries based on database type
    queries = []
    
    if connection.database_type in ["postgresql", "mysql"]:
        queries = [
            {
                "title": "Show all tables",
                "query": "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';",
                "description": "List all tables available in your database"
            },
            {
                "title": "Table row counts",
                "query": """
SELECT 
    schemaname,
    tablename,
    n_tup_ins - n_tup_del as row_count
FROM pg_stat_user_tables 
ORDER BY row_count DESC;
                """,
                "description": "Get row counts for all tables"
            },
            {
                "title": "Sample data exploration",
                "query": "-- Replace 'your_table_name' with an actual table\nSELECT * FROM your_table_name LIMIT 100;",
                "description": "Sample data from any table"
            }
        ]
    
    elif connection.database_type == "mongodb":
        queries = [
            {
                "title": "List collections",
                "query": "show collections",
                "description": "Show all collections in your MongoDB database"
            },
            {
                "title": "Sample documents",
                "query": "db.your_collection.find().limit(10)",
                "description": "Get sample documents from a collection"
            }
        ]
    
    return {
        "connection_id": connection_id,
        "connection_name": connection.name,
        "database_type": connection.database_type,
        "sample_queries": queries,
        "superset_sql_lab_url": f"{settings.SUPERSET_URL}/sqllab/"
    }