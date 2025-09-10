from celery import current_app as celery_app
from celery.schedules import crontab
from datetime import datetime, timedelta
from .etl_tasks import run_etl_job_async  # Import the task
from ..models.settings import ETLSchedule
from ..models.connection import DatabaseConnection
from ..db.database import get_db

@celery_app.task
def check_scheduled_etl_jobs():
    """Check for ETL jobs that should run now"""
    db = next(get_db())
    
    try:
        now = datetime.utcnow()
        
        # Get schedules that are due
        due_schedules = db.query(ETLSchedule).filter(
            ETLSchedule.is_active == True,
            ETLSchedule.next_run <= now
        ).all()
        
        triggered_count = 0
        
        for schedule in due_schedules:
            # Check if connection is still active
            connection = db.query(DatabaseConnection).filter(
                DatabaseConnection.id == schedule.connection_id,
                DatabaseConnection.status == 'connected',
                DatabaseConnection.is_active == True
            ).first()
            
            if connection:
                # Trigger ETL job
                run_etl_job_async.delay(
                    connection_id=schedule.connection_id,
                    job_type='scheduled_sync',
                    trigger_type='scheduled'
                )
                
                # Update next run time
                schedule.next_run = calculate_next_run(schedule)
                schedule.last_run = now
                triggered_count += 1
        
        db.commit()
        return f"Processed {triggered_count} scheduled jobs"
        
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def calculate_next_run(schedule: ETLSchedule) -> datetime:
    """Calculate next run time based on schedule frequency"""
    now = datetime.utcnow()
    
    if schedule.frequency == 'hourly':
        return now + timedelta(hours=1)
    elif schedule.frequency == 'daily':
        hour, minute = map(int, schedule.scheduled_time.split(':'))
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        return next_run
    elif schedule.frequency == 'weekly':
        return now + timedelta(weeks=1)
    elif schedule.frequency == 'monthly':
        return now + timedelta(days=30)
    
    return now + timedelta(days=1)