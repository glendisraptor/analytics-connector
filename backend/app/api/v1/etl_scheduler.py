import schedule
import time
import threading
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ...db.database import SessionLocal
from ...models.connection import DatabaseConnection, ETLJob

class ETLScheduler:
    """Service to automatically schedule and run ETL jobs"""
    
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the ETL scheduler"""
        if self.running:
            return
        
        self.running = True
        
        # Schedule checks
        schedule.every(1).hours.do(self._check_hourly_jobs)
        schedule.every().day.at("02:00").do(self._check_daily_jobs)
        schedule.every().sunday.at("03:00").do(self._check_weekly_jobs)
        schedule.every(30).days.do(self._check_monthly_jobs)
        
        # Start scheduler in background thread
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        
        print("✅ ETL Scheduler started")
    
    def stop(self):
        """Stop the ETL scheduler"""
        self.running = False
        schedule.clear()
        print("🛑 ETL Scheduler stopped")
    
    def _run_scheduler(self):
        """Run the schedule checker"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def _check_hourly_jobs(self):
        """Check for connections that need hourly sync"""
        self._trigger_jobs_by_frequency("hourly", timedelta(hours=1))
    
    def _check_daily_jobs(self):
        """Check for connections that need daily sync"""
        self._trigger_jobs_by_frequency("daily", timedelta(days=1))
    
    def _check_weekly_jobs(self):
        """Check for connections that need weekly sync"""
        self._trigger_jobs_by_frequency("weekly", timedelta(weeks=1))
    
    def _check_monthly_jobs(self):
        """Check for connections that need monthly sync"""
        self._trigger_jobs_by_frequency("monthly", timedelta(days=30))
    
    def _trigger_jobs_by_frequency(self, frequency: str, interval: timedelta):
        """Trigger ETL jobs for connections with specified frequency"""
        db = SessionLocal()
        try:
            # Find connections that need syncing
            cutoff_time = datetime.utcnow() - interval
            
            connections = db.query(DatabaseConnection)\
                .filter(
                    DatabaseConnection.sync_frequency == frequency,
                    DatabaseConnection.status == "connected",
                    DatabaseConnection.is_active == True
                )\
                .filter(
                    (DatabaseConnection.last_sync == None) |
                    (DatabaseConnection.last_sync < cutoff_time)
                )\
                .all()
            
            for connection in connections:
                # Check if there's already a running job
                existing_job = db.query(ETLJob)\
                    .filter(
                        ETLJob.connection_id == connection.id,
                        ETLJob.status.in_(["pending", "running"])
                    )\
                    .first()
                
                if not existing_job:
                    # Create scheduled job
                    job = ETLJob(
                        connection_id=connection.id,
                        job_type="scheduled_sync",
                        status="pending"
                    )
                    
                    db.add(job)
                    db.commit()
                    db.refresh(job)
                    
                    # Trigger job (you'd call your ETL service here)
                    print(f"🕐 Triggered scheduled {frequency} ETL job for connection {connection.id}")
                    
                    # In a real app, you'd use your background task system
                    # background_tasks.add_task(run_etl_job_async, job.id)
            
            if connections:
                print(f"📅 Triggered {len(connections)} {frequency} ETL jobs")
            
        except Exception as e:
            print(f"❌ Error in scheduled ETL check: {e}")
        finally:
            db.close()

# Global scheduler instance
etl_scheduler = ETLScheduler()