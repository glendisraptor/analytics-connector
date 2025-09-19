from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from enum import Enum
import logging

from ...services.superset_integration import SupersetIntegration
from ...db.database import get_db
from ...models.connection import ETLJob, DatabaseConnection
from ...models.user import User
from ...services.etl_service import ETLService
from ...core.security import get_current_user


logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models
class JobTriggerType(str, Enum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    AUTO = "auto"

class JobCreate(BaseModel):
    connection_id: int
    job_type: str = "full_sync"
    trigger_type: JobTriggerType = JobTriggerType.MANUAL

class JobResponse(BaseModel):
    id: int
    connection_id: int
    status: str
    job_type: str
    records_processed: int
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    

@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    connection_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List ETL jobs for current user"""
    
    # Get user's connections first
    user_connections = db.query(DatabaseConnection.id)\
        .filter(DatabaseConnection.owner_id == current_user.id)\
        .subquery()
    
    # Fix the SQL warning by using proper subquery
    query = db.query(ETLJob)\
        .filter(ETLJob.connection_id.in_(
            db.query(user_connections.c.id)
        ))
    
    if connection_id:
        # Also verify the user owns this specific connection
        connection = db.query(DatabaseConnection)\
            .filter(
                DatabaseConnection.id == connection_id,
                DatabaseConnection.owner_id == current_user.id
            )\
            .first()
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        query = query.filter(ETLJob.connection_id == connection_id)
    
    jobs = query.order_by(ETLJob.created_at.desc()).limit(50).all()
    return jobs

# Get route by job ID
@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get details of a specific ETL job"""
    
    job = db.query(ETLJob).join(DatabaseConnection).filter(
        ETLJob.id == job_id,
        DatabaseConnection.owner_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job

@router.post("/trigger", response_model=JobResponse)
async def trigger_etl_job(
    job_data: JobCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually trigger an ETL job for a database connection"""
    
    # Verify connection ownership
    connection = db.query(DatabaseConnection)\
        .filter(
            DatabaseConnection.id == job_data.connection_id,
            DatabaseConnection.owner_id == current_user.id
        )\
        .first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    if connection.status != "connected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Connection must be in 'connected' state to run ETL"
        )
    
    # Check if there's already a running job for this connection
    existing_job = db.query(ETLJob)\
        .filter(
            ETLJob.connection_id == job_data.connection_id,
            ETLJob.status.in_(["pending", "running"])
        )\
        .first()
    
    if existing_job:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"ETL job already running for this connection (Job ID: {existing_job.id})"
        )
    
    # Create job record
    job = ETLJob(
        connection_id=job_data.connection_id,
        job_type=job_data.job_type,
        status="pending"
    )
    
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Start job in background
    background_tasks.add_task(run_etl_job_async, job.id)
    
    return job

@router.post("/trigger-all")
async def trigger_all_etl_jobs(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trigger ETL jobs for all connected databases"""
    
    connections = db.query(DatabaseConnection)\
        .filter(
            DatabaseConnection.owner_id == current_user.id,
            DatabaseConnection.status == "connected",
            DatabaseConnection.is_active == True
        )\
        .all()
    
    if not connections:
        return {
            "message": "No connected databases found",
            "triggered_jobs": 0
        }
    
    triggered_jobs = []
    
    for connection in connections:
        # Check if already running
        existing_job = db.query(ETLJob)\
            .filter(
                ETLJob.connection_id == connection.id,
                ETLJob.status.in_(["pending", "running"])
            )\
            .first()
        
        if not existing_job:
            # Create and trigger job
            job = ETLJob(
                connection_id=connection.id,
                job_type="full_sync",
                status="pending"
            )
            
            db.add(job)
            db.commit()
            db.refresh(job)
            
            background_tasks.add_task(run_etl_job_async, job.id)
            triggered_jobs.append({
                "connection_id": connection.id,
                "connection_name": connection.name,
                "job_id": job.id
            })
    
    return {
        "message": f"Triggered {len(triggered_jobs)} ETL jobs",
        "triggered_jobs": triggered_jobs
    }

# TODO - Remove this llater - for now its testing
@router.get("/connection/{connection_id}/superset-status")
async def get_superset_sync_status(connection_id: int):
    """Check if connection is properly synced to Superset"""
    
    # Check if analytics tables exist
    etl_service = ETLService()
    analytics_tables = etl_service.get_analytics_tables(connection_id)
    
    # Check Superset integration status
    superset_integration = SupersetIntegration()
    superset_status = superset_integration.get_superset_connection_status(connection_id)
    
    return {
        "connection_id": connection_id,
        "analytics_tables_count": len(analytics_tables),
        "analytics_tables": analytics_tables,
        "superset_status": superset_status,
        "last_sync": "2024-01-15T10:30:00Z"
    }
    
# TODO - Remove this llater - for now its testing
@router.post("/sync-superset/{connection_id}")
async def sync_connection_to_superset(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually sync a connection to Superset"""
    # Verify ownership
    connection = db.query(DatabaseConnection).filter(
        DatabaseConnection.id == connection_id,
        DatabaseConnection.owner_id == current_user.id
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    superset_integration = SupersetIntegration()
    
    try:
        # Create datasets first
        datasets = superset_integration.create_superset_datasets(connection_id)
        
        if not datasets:
            return {
                "success": False, 
                "connection_id": connection_id,
                "error": "No datasets created"
            }
        
        # Create sample charts
        chart_ids = superset_integration.create_sample_charts(connection_id, datasets)
        
        return {
            "success": True, 
            "connection_id": connection_id,
            "datasets_created": len(datasets),
            "charts_created": len(chart_ids),
            "datasets": datasets,
            "chart_ids": chart_ids
        }
        
    except Exception as e:
        logger.error(f"Error syncing to Superset: {str(e)}")
        return {
            "success": False, 
            "connection_id": connection_id,
            "error": str(e)
        }


@router.post("/connection/{connection_id}/create-sample-charts")
async def create_sample_charts_and_dashboard(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create meaningful business charts and dashboard for a connection"""
    try:
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
                detail="Connection not found or access denied"
            )
        
        # Verify connection is active and connected
        if not connection.is_active or connection.status != "connected":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Connection must be active and connected. Current status: {connection.status}"
            )
        
        # Check if analytics tables exist
        etl_service = ETLService()
        analytics_tables = etl_service.get_analytics_tables(connection_id)
        
        if not analytics_tables:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No analytics tables found. Please run ETL first using /jobs/trigger"
            )
        
        superset_integration = SupersetIntegration()
        
        # Test Superset connection first
        superset_status = superset_integration.test_superset_connection()
        if superset_status['status'] != 'connected':
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Superset service unavailable: {superset_status.get('error', 'Connection failed')}"
            )
        
        # Create or find the Superset database connection
        superset_db_id = superset_integration._create_or_find_analytics_database_connection(connection)
        if not superset_db_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create/find Superset database connection"
            )
        
        # Create datasets in Superset for each analytics table
        table_names = [table for table in analytics_tables]
        print(f"Creating datasets for tables: {table_names}")
        print(f"Analytics tables: {analytics_tables}")
        created_datasets = superset_integration.create_superset_datasets(connection_id, table_names)
        
        if not created_datasets:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create any datasets. Check Superset configuration and logs."
            )
        
        # Create business charts from the datasets
        chart_ids = superset_integration.create_sample_charts(connection_id, created_datasets)
        
        if not chart_ids:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create any charts. Check Superset configuration and logs."
            )
        
        # Create dashboard with charts (you'll need to implement this method)
        dashboard_id = None
        try:
            # This method would need to be implemented in SupersetIntegration
            dashboard_id = superset_integration.create_dashboard_with_charts(connection, chart_ids)
        except Exception as e:
            logger.warning(f"Dashboard creation failed: {str(e)}")
        
        # Build response with useful information
        response_data = {
            "success": True,
            "connection_id": connection_id,
            "connection_name": connection.name,
            "created_charts": len(chart_ids),
            "chart_ids": chart_ids,
            "dashboard_id": dashboard_id,
            "analytics_tables_processed": len(analytics_tables),
            "analytics_tables": analytics_tables,
            "created_datasets": len(created_datasets),
            "datasets": created_datasets
        }
        
        # Add dashboard URL if created successfully
        if dashboard_id:
            response_data["dashboard_url"] = f"{superset_integration.url}/superset/dashboard/{dashboard_id}/"
            response_data["message"] = f"Created {len(chart_ids)} business charts and dashboard successfully"
        else:
            response_data["message"] = f"Created {len(chart_ids)} charts but dashboard creation failed"
            response_data["warning"] = "Charts were created but could not be assembled into dashboard"
        
        return response_data
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating charts for connection {connection_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/connection/{connection_id}/schedule")
async def get_etl_schedule(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get ETL schedule for a connection"""
    
    connection = db.query(DatabaseConnection)\
        .filter(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.owner_id == current_user.id
        )\
        .first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    # Get recent jobs to show schedule effectiveness
    recent_jobs = db.query(ETLJob)\
        .filter(ETLJob.connection_id == connection_id)\
        .order_by(ETLJob.created_at.desc())\
        .limit(10)\
        .all()
    
    return {
        "connection_id": connection_id,
        "sync_frequency": connection.sync_frequency,
        "last_sync": connection.last_sync,
        "next_scheduled_sync": calculate_next_sync(connection),
        "recent_jobs": [
            {
                "id": job.id,
                "status": job.status,
                "records_processed": job.records_processed,
                "started_at": job.started_at,
                "completed_at": job.completed_at
            } for job in recent_jobs
        ]
    }

def calculate_next_sync(connection: DatabaseConnection) -> Optional[datetime]:
    """Calculate when the next sync should happen"""
    if not connection.last_sync:
        return None
    
    frequency_map = {
        "hourly": timedelta(hours=1),
        "daily": timedelta(days=1),
        "weekly": timedelta(weeks=1),
        "monthly": timedelta(days=30)
    }
    
    interval = frequency_map.get(connection.sync_frequency, timedelta(days=1))
    return connection.last_sync + interval

# Background task function (enhanced)
async def run_etl_job_async(job_id: int):
    """Run ETL job asynchronously with better error handling and notifications"""
    from ...db.database import SessionLocal
    from ...services.superset_integration import SupersetIntegration
    
    db = SessionLocal()
    try:
        job = db.query(ETLJob).filter(ETLJob.id == job_id).first()
        if not job:
            return
        
        connection = db.query(DatabaseConnection).filter(
            DatabaseConnection.id == job.connection_id
        ).first()
        
        if not connection:
            job.status = "failed"
            job.error_message = "Connection not found"
            job.completed_at = datetime.utcnow()
            db.commit()
            return
        
        # Update job status
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()
        
        try:
            # Run ETL process
            etl_service = ETLService()
            records_processed = etl_service.run_etl(job.connection_id, job.job_type)
            
            # Update success status
            job.status = "completed"
            job.records_processed = records_processed
            job.completed_at = datetime.utcnow()
            
            # Update connection last_sync
            connection.last_sync = datetime.utcnow()
            
            # Sync new datasets to Superset
            superset_integration = SupersetIntegration()
            try:
                # Create datasets for the connection
                created_datasets = superset_integration.create_superset_datasets(job.connection_id)
                print(f"✅ Synced {len(created_datasets)} datasets to Superset for connection {job.connection_id}")
            except Exception as e:
                print(f"⚠️ Failed to sync datasets to Superset: {e}")
                logger.error(f"Superset sync error: {str(e)}")  # Add proper logging
            
        except Exception as e:
            # Update error status
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            print(f"❌ ETL job {job_id} failed: {e}")
        
        db.commit()
        
        # Send notification (you could implement email/webhook here)
        print(f"📧 ETL job {job_id} completed with status: {job.status}")
        
    except Exception as e:
        print(f"❌ Critical error in ETL job {job_id}: {e}")
    finally:
        db.close()