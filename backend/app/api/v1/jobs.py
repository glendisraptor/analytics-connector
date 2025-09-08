from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from enum import Enum

from ...db.database import get_db
from ...models.connection import ETLJob, DatabaseConnection
from ...models.user import User
from ...services.etl_service import ETLService
from ...core.security import get_current_user

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
async def list_etl_jobs(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List ETL jobs for the current user"""
    
    # Get connections owned by the user
    connections = db.query(DatabaseConnection.id).filter(
        DatabaseConnection.owner_id == current_user.id
    ).subquery()
    
    jobs = db.query(ETLJob).filter(
        ETLJob.connection_id.in_(connections)
    ).order_by(ETLJob.created_at.desc()).offset(skip).limit(limit).all()
    
    return jobs

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
                # This will create/update datasets in Superset
                superset_integration.sync_datasets_after_etl(job.connection_id)
                print(f"✅ Synced datasets to Superset for connection {job.connection_id}")
            except Exception as e:
                print(f"⚠️ Failed to sync datasets to Superset: {e}")
            
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