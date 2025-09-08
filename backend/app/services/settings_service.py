from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from ..models.settings import UserSettings, ETLSchedule
from ..models.connection import DatabaseConnection
from ..models.user import User

logger = logging.getLogger(__name__)

class SettingsService:
    @staticmethod
    def get_or_create_user_settings(db: Session, user_id: int) -> UserSettings:
        """Get user settings or create default ones"""
        settings = db.query(UserSettings).filter(
            UserSettings.user_id == user_id
        ).first()
        
        if not settings:
            settings = UserSettings(user_id=user_id)
            db.add(settings)
            db.commit()
            db.refresh(settings)
        
        return settings
    
    @staticmethod
    def update_user_settings(
        db: Session, 
        user_id: int, 
        settings_data: Dict[str, Any]
    ) -> UserSettings:
        """Update user settings"""
        settings = SettingsService.get_or_create_user_settings(db, user_id)
        
        for field, value in settings_data.items():
            if hasattr(settings, field):
                setattr(settings, field, value)
        
        db.commit()
        db.refresh(settings)
        return settings
    
    @staticmethod
    def get_or_create_etl_schedule(
        db: Session, 
        connection_id: int, 
        user_id: int
    ) -> ETLSchedule:
        """Get ETL schedule or create default one"""
        schedule = db.query(ETLSchedule).filter(
            ETLSchedule.connection_id == connection_id
        ).first()
        
        if not schedule:
            schedule = ETLSchedule(
                connection_id=connection_id,
                user_id=user_id,
                frequency="daily",
                scheduled_time="02:00",
                is_active=True
            )
            db.add(schedule)
            db.commit()
            db.refresh(schedule)
        
        return schedule
    
    @staticmethod
    def calculate_next_run(schedule: ETLSchedule) -> datetime:
        """Calculate next run time for a schedule"""
        now = datetime.utcnow()
        
        if schedule.frequency == "hourly":
            return now + timedelta(hours=1)
        elif schedule.frequency == "daily":
            # Parse scheduled_time (HH:MM format)
            time_parts = schedule.scheduled_time.split(":")
            hour = int(time_parts[0])
            minute = int(time_parts[1]) if len(time_parts) > 1 else 0
            
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run
        elif schedule.frequency == "weekly":
            # Default to Sunday if no days_of_week specified
            days = schedule.days_of_week or "0"  # Sunday
            target_day = int(days.split(",")[0])
            
            days_ahead = target_day - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            
            return now + timedelta(days=days_ahead)
        elif schedule.frequency == "monthly":
            # Default to 1st of month if no day_of_month specified
            target_day = schedule.day_of_month or 1
            
            if now.day < target_day:
                return now.replace(day=target_day)
            else:
                # Next month
                if now.month == 12:
                    return now.replace(year=now.year + 1, month=1, day=target_day)
                else:
                    return now.replace(month=now.month + 1, day=target_day)
        
        return now + timedelta(days=1)  # Default fallback
    
    @staticmethod
    def get_active_schedules(db: Session) -> List[ETLSchedule]:
        """Get all active ETL schedules"""
        return db.query(ETLSchedule).filter(
            ETLSchedule.is_active == True
        ).all()
    
    @staticmethod
    def should_run_schedule(schedule: ETLSchedule) -> bool:
        """Check if schedule should run now"""
        if not schedule.is_active:
            return False
        
        now = datetime.utcnow()
        
        # If next_run is not set or is in the past, it should run
        if not schedule.next_run or schedule.next_run <= now:
            return True
        
        return False