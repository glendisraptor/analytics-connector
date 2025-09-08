from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any
from ...db.database import get_db
from ...models.user import User
from ...services.superset_integration import SupersetIntegration
from ...core.security import get_current_user

router = APIRouter()

@router.post("/sync-connection/{connection_id}")
async def sync_connection_to_superset(
    connection_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sync a specific database connection to Superset"""
    
    # Verify the connection belongs to the current user
    from ...models.connection import DatabaseConnection
    connection = db.query(DatabaseConnection).filter(
        DatabaseConnection.id == connection_id,
        DatabaseConnection.owner_id == current_user.id
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    # Run sync in background
    superset_integration = SupersetIntegration()
    background_tasks.add_task(superset_integration.sync_connection_to_superset, connection_id)
    
    return {
        "message": "Superset sync started",
        "connection_id": connection_id,
        "connection_name": connection.name
    }

@router.post("/sync-all-connections")
async def sync_all_connections_to_superset(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Sync all user's database connections to Superset"""
    
    # For admin users, sync all connections
    # For regular users, sync only their connections
    
    superset_integration = SupersetIntegration()
    
    if current_user.is_superuser:
        # Admin can sync all connections
        background_tasks.add_task(superset_integration.sync_all_connections)
        message = "Started syncing all connections to Superset"
    else:
        # Regular users sync only their connections
        # You'd implement a user-specific sync method
        message = "User-specific sync not implemented yet"
    
    return {"message": message}

@router.get("/superset-url")
async def get_superset_url():
    """Get the Superset URL for frontend integration"""
    from ...core.config import settings
    return {
        "superset_url": settings.SUPERSET_URL,
        "login_required": True
    }