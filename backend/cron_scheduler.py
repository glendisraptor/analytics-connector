"""
Cron Scheduler for ETL Jobs
Runs scheduled ETL jobs based on ETLSchedule configuration
"""
import os
import time
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/cron_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create app context
from app import create_app, db
from models.models import ETLSchedule, ETLJob, DatabaseConnection
from routes.etl import extract_data_from_connection

app = create_app()

def calculate_next_run(schedule):
    """Calculate next run time for a schedule"""
    now = datetime.utcnow()
    hour, minute = map(int, schedule.scheduled_time.split(':'))
    next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    if next_run <= now:
        if schedule.frequency == 'hourly':
            next_run += timedelta(hours=1)
        elif schedule.frequency == 'daily':
            next_run += timedelta(days=1)
        elif schedule.frequency == 'weekly':
            next_run += timedelta(weeks=1)
        elif schedule.frequency == 'monthly':
            next_run += timedelta(days=30)  # Simplified monthly calculation
    
    return next_run

def should_run_schedule(schedule):
    """Check if a schedule should run now"""
    if not schedule.is_active:
        return False
    
    if not schedule.next_run:
        return True
    
    return datetime.utcnow() >= schedule.next_run

def run_etl_job(schedule):
    """Execute ETL job for a schedule"""
    logger.info(f"Starting ETL job for schedule {schedule.id}, connection {schedule.connection_id}")
    
    try:
        connection = DatabaseConnection.query.get(schedule.connection_id)
        
        if not connection:
            logger.error(f"Connection {schedule.connection_id} not found")
            return
        
        if connection.status != 'connected':
            logger.warning(f"Connection {schedule.connection_id} is not connected. Status: {connection.status}")
            return
        
        # Create job record
        job = ETLJob(
            connection_id=connection.id,
            status='running',
            job_type='scheduled_sync',
            started_at=datetime.utcnow()
        )
        db.session.add(job)
        db.session.flush()
        
        logger.info(f"Created ETL job {job.id}")
        
        # Extract data
        data, error = extract_data_from_connection(connection)
        
        if error:
            job.status = 'failed'
            job.error_message = error
            job.completed_at = datetime.utcnow()
            logger.error(f"ETL job {job.id} failed: {error}")
        else:
            job.status = 'completed'
            job.records_processed = data.get('total_records', 0)
            job.completed_at = datetime.utcnow()
            
            # Update connection last_sync
            connection.last_sync = datetime.utcnow()
            
            logger.info(f"ETL job {job.id} completed. Processed {job.records_processed} records")
        
        # Update schedule
        schedule.last_run = datetime.utcnow()
        schedule.next_run = calculate_next_run(schedule)
        
        db.session.commit()
        
        logger.info(f"Next run scheduled for {schedule.next_run}")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error running ETL job for schedule {schedule.id}: {str(e)}", exc_info=True)
        
        # Try to update job status
        try:
            if 'job' in locals():
                job.status = 'failed'
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()
                db.session.commit()
        except:
            pass

def process_schedules():
    """Process all active schedules"""
    with app.app_context():
        try:
            # Get all active schedules
            schedules = ETLSchedule.query.filter_by(is_active=True).all()
            
            logger.info(f"Processing {len(schedules)} active schedules")
            
            for schedule in schedules:
                try:
                    if should_run_schedule(schedule):
                        logger.info(f"Running schedule {schedule.id}")
                        run_etl_job(schedule)
                    else:
                        logger.debug(f"Schedule {schedule.id} not due yet. Next run: {schedule.next_run}")
                        
                except Exception as e:
                    logger.error(f"Error processing schedule {schedule.id}: {str(e)}", exc_info=True)
                    continue
                    
        except Exception as e:
            logger.error(f"Error in process_schedules: {str(e)}", exc_info=True)

def initialize_schedules():
    """Initialize next_run for schedules that don't have it"""
    with app.app_context():
        try:
            schedules = ETLSchedule.query.filter(
                ETLSchedule.next_run.is_(None),
                ETLSchedule.is_active == True
            ).all()
            
            for schedule in schedules:
                schedule.next_run = calculate_next_run(schedule)
            
            db.session.commit()
            
            logger.info(f"Initialized {len(schedules)} schedules")
            
        except Exception as e:
            logger.error(f"Error initializing schedules: {str(e)}", exc_info=True)
            db.session.rollback()

def main():
    """Main scheduler loop"""
    logger.info("="*60)
    logger.info("ETL Cron Scheduler Started")
    logger.info("="*60)
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Initialize schedules
    initialize_schedules()
    
    # Check interval in seconds (default: 60 seconds = 1 minute)
    check_interval = int(os.getenv('SCHEDULER_CHECK_INTERVAL', '60'))
    
    logger.info(f"Checking schedules every {check_interval} seconds")
    
    while True:
        try:
            logger.info("Checking for scheduled jobs...")
            process_schedules()
            
            logger.info(f"Sleeping for {check_interval} seconds")
            time.sleep(check_interval)
            
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            break
            
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {str(e)}", exc_info=True)
            time.sleep(check_interval)

if __name__ == '__main__':
    main()