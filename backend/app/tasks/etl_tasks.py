from celery import current_app as celery_app
from ..services.etl_service import ETLService
from ..db.database import get_db
from ..models.connection import ETLJob
import logging

logger = logging.getLogger(__name__)

@celery_app.task
def run_etl_job_async(connection_id: int, job_type: str = "full_sync", trigger_type: str = "manual"):
    """
    Celery task to run ETL job asynchronously
    """
    db = next(get_db())
    
    try:
        # Create ETL job record
        job = ETLJob(
            connection_id=connection_id,
            job_type=job_type,
            status="running"
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Run the ETL process
        etl_service = ETLService()
        result = etl_service.run_etl_job(job.id)
        
        logger.info(f"ETL job {job.id} completed successfully")
        return {"job_id": job.id, "status": "completed", "result": result}
        
    except Exception as e:
        logger.error(f"ETL job failed: {str(e)}")
        
        # Update job status to failed
        if 'job' in locals():
            job.status = "failed"
            job.error_message = str(e)
            db.commit()
        
        raise e
    finally:
        db.close()