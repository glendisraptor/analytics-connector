from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from ...db.database import get_db
from ...models.connection import DatabaseConnection, ConnectionStatus, DatabaseType
from ...models.user import User
from ...utils.encryption import encryption_service
from ...services.database_service import DatabaseService
from ...services.superset_integration import SupersetIntegration
from ...core.security import get_current_user

router = APIRouter()

# Pydantic models
class ConnectionCredentials(BaseModel):
    host: str
    port: int
    username: str
    password: str
    database_name: str
    additional_params: dict = {}

class ConnectionCreate(BaseModel):
    name: str
    database_type: DatabaseType
    credentials: ConnectionCredentials
    sync_frequency: str = "daily"

class ConnectionResponse(BaseModel):
    id: int
    name: str
    database_type: DatabaseType
    status: ConnectionStatus
    last_tested: Optional[datetime]
    last_sync: Optional[datetime]
    sync_frequency: str
    is_active: bool
    analytics_ready: bool = False  # Add this field
    created_at: datetime

class ConnectionUpdate(BaseModel):
    name: Optional[str] = None
    sync_frequency: Optional[str] = None
    is_active: Optional[bool] = None

@router.get("/", response_model=List[ConnectionResponse])
async def list_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all database connections for current user"""
    connections = db.query(DatabaseConnection)\
        .filter(DatabaseConnection.owner_id == current_user.id)\
        .all()
    
    return connections

@router.post("/", response_model=ConnectionResponse)
async def create_connection(
    connection_data: ConnectionCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new database connection"""
    
    # Encrypt credentials
    encrypted_creds = encryption_service.encrypt_credentials(
        connection_data.credentials.dict()
    )
    
    print("#########################################")
    print(connection_data.database_type)
    print("#########################################")
    
    # Create connection record
    db_connection = DatabaseConnection(
        name=connection_data.name,
        database_type=connection_data.database_type.value,
        encrypted_credentials=encrypted_creds,
        sync_frequency=connection_data.sync_frequency,
        owner_id=current_user.id,
        status=ConnectionStatus.TESTING,
        analytics_ready=False  # Initialize as False
    )
    print("***********************************************")
    print(db_connection.name)
    print(db_connection.database_type)
    print(db_connection.sync_frequency)
    print("***********************************************")
    
    db.add(db_connection)
    db.commit()
    db.refresh(db_connection)
    
    # Test connection in background
    background_tasks.add_task(
        test_connection_async,
        db_connection.id
    )
    
    return db_connection

@router.get("/{connection_id}", response_model=ConnectionResponse)
async def get_connection(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific database connection"""
    connection = db.query(DatabaseConnection)\
        .filter(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.owner_id == current_user.id
        )\
        .first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    return connection

@router.put("/{connection_id}", response_model=ConnectionResponse)
async def update_connection(
    connection_id: int,
    connection_update: ConnectionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a database connection"""
    connection = db.query(DatabaseConnection)\
        .filter(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.owner_id == current_user.id
        )\
        .first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    # Update fields
    for field, value in connection_update.dict(exclude_unset=True).items():
        setattr(connection, field, value)
    
    db.commit()
    db.refresh(connection)
    
    return connection

@router.delete("/{connection_id}")
async def delete_connection(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a database connection"""
    connection = db.query(DatabaseConnection)\
        .filter(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.owner_id == current_user.id
        )\
        .first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    db.delete(connection)
    db.commit()
    
    return {"message": "Connection deleted successfully"}

@router.post("/{connection_id}/test")
async def test_connection(
    connection_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Test a database connection"""
    connection = db.query(DatabaseConnection)\
        .filter(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.owner_id == current_user.id
        )\
        .first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    # Update status to testing
    connection.status = ConnectionStatus.TESTING
    db.commit()
    
    # Test connection in background
    background_tasks.add_task(
        test_connection_async,
        connection_id
    )
    
    return {"message": "Connection test started"}

# # Background task functions
async def test_connection_async(connection_id: int):
    """Test database connection asynchronously"""
    from ...db.database import SessionLocal
    
    db = SessionLocal()
    try:
        connection = db.query(DatabaseConnection)\
            .filter(DatabaseConnection.id == connection_id)\
            .first()
        
        if not connection:
            return
        
        # Decrypt credentials
        credentials = encryption_service.decrypt_credentials(
            connection.encrypted_credentials
        )
        
        # Test connection
        db_service = DatabaseService()
        success = db_service.test_connection(
            connection.database_type,
            credentials
        )
        
        # Update status
        connection.status = ConnectionStatus.CONNECTED if success else ConnectionStatus.FAILED
        connection.last_tested = datetime.utcnow()
        
        db.commit()
        
    finally:
        db.close()
        
        
@router.post("/{connection_id}/sync-to-superset")
async def sync_connection_to_superset(
    connection_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually sync a database connection to Superset"""
    
    # Verify connection ownership
    connection = db.query(DatabaseConnection)\
        .filter(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.owner_id == current_user.id
        )\
        .first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    if connection.status != ConnectionStatus.CONNECTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Connection must be in 'connected' state to sync to Superset"
        )
    
    # Start sync in background
    background_tasks.add_task(sync_to_superset_task, connection_id)
    
    return {
        "message": "Superset sync started",
        "connection_id": connection_id,
        "connection_name": connection.name
    }

@router.get("/{connection_id}/superset-status")
async def get_superset_sync_status(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get Superset sync status for a connection"""
    
    connection = db.query(DatabaseConnection)\
        .filter(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.owner_id == current_user.id
        )\
        .first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    # Check if connection exists in Superset
    superset_integration = SupersetIntegration()
    
    return {
        "connection_id": connection_id,
        "superset_synced": connection.analytics_ready,  # Use the database field
        "last_sync": connection.last_sync,
        "superset_url": f"{superset_integration.superset_service.base_url}/databaseview/list/",
        "analytics_available": connection.status == ConnectionStatus.CONNECTED and connection.analytics_ready
    }

# Background task functions
async def test_and_sync_connection(connection_id: int, auto_sync_to_superset: bool = True):
    """Test database connection and optionally sync to Superset"""
    from ...db.database import SessionLocal
    
    db = SessionLocal()
    try:
        connection = db.query(DatabaseConnection)\
            .filter(DatabaseConnection.id == connection_id)\
            .first()
        
        if not connection:
            return
        
        # Decrypt credentials and test connection
        credentials = encryption_service.decrypt_credentials(
            connection.encrypted_credentials
        )
        
        db_service = DatabaseService()
        success = db_service.test_connection(
            connection.database_type,
            credentials
        )
        
        # Update connection status
        connection.status = ConnectionStatus.CONNECTED if success else ConnectionStatus.FAILED
        connection.last_tested = datetime.utcnow()
        
        db.commit()
        
        # If connection successful and auto-sync enabled, sync to Superset
        if success and auto_sync_to_superset:
            superset_integration = SupersetIntegration()
            sync_success = superset_integration.sync_connection_to_superset(connection_id)
            
            if sync_success:
                # Update analytics_ready and last_sync fields
                connection.analytics_ready = True
                connection.last_sync = datetime.utcnow()
                db.commit()
                print(f"✅ Connection {connection_id} synced to Superset")
            else:
                print(f"❌ Failed to sync connection {connection_id} to Superset")
        
    except Exception as e:
        print(f"Error in test_and_sync_connection: {e}")
        if connection:
            connection.status = ConnectionStatus.FAILED
            db.commit()
    finally:
        db.close()

async def sync_to_superset_task(connection_id: int):
    """Background task to sync connection to Superset"""
    from ...db.database import SessionLocal
    
    db = SessionLocal()
    try:
        connection = db.query(DatabaseConnection)\
            .filter(DatabaseConnection.id == connection_id)\
            .first()
        
        if not connection:
            print(f"❌ Connection {connection_id} not found")
            return
        
        superset_integration = SupersetIntegration()
        success = superset_integration.sync_connection_to_superset(connection_id)
        
        if success:
            # Update analytics_ready and last_sync fields
            connection.analytics_ready = True
            connection.last_sync = datetime.utcnow()
            db.commit()
            print(f"✅ Successfully synced connection {connection_id} to Superset")
        else:
            # Reset analytics_ready to False if sync failed
            connection.analytics_ready = False
            db.commit()
            print(f"❌ Failed to sync connection {connection_id} to Superset")
            
    except Exception as e:
        print(f"Error in sync_to_superset_task: {e}")
        # Reset analytics_ready to False on error
        if connection:
            connection.analytics_ready = False
            db.commit()
    finally:
        db.close()