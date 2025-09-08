from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from ...db.database import get_db
from ...models.user import User
from ...models.settings import UserSettings, ETLSchedule
from ...models.connection import DatabaseConnection
from ...core.security import get_current_user
from ...core.config import settings as app_settings

router = APIRouter()

# Pydantic models
class UserSettingsUpdate(BaseModel):
    auto_sync_to_superset: Optional[bool] = None
    default_sync_frequency: Optional[str] = None
    connection_timeout: Optional[int] = None
    max_retry_attempts: Optional[int] = None
    superset_auto_create_datasets: Optional[bool] = None
    superset_auto_create_dashboards: Optional[bool] = None
    data_retention_days: Optional[int] = None
    enable_data_profiling: Optional[bool] = None
    email_notifications: Optional[bool] = None
    etl_success_notifications: Optional[bool] = None
    etl_failure_notifications: Optional[bool] = None
    weekly_reports: Optional[bool] = None
    theme: Optional[str] = None
    timezone: Optional[str] = None
    date_format: Optional[str] = None

class UserSettingsResponse(BaseModel):
    auto_sync_to_superset: bool
    default_sync_frequency: str
    connection_timeout: int
    max_retry_attempts: int
    superset_auto_create_datasets: bool
    superset_auto_create_dashboards: bool
    data_retention_days: int
    enable_data_profiling: bool
    email_notifications: bool
    etl_success_notifications: bool
    etl_failure_notifications: bool
    weekly_reports: bool
    theme: str
    timezone: str
    date_format: str

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None

class ETLScheduleUpdate(BaseModel):
    frequency: str
    scheduled_time: str = "02:00"
    timezone: str = "UTC"
    is_active: bool = True
    days_of_week: Optional[str] = None
    day_of_month: Optional[int] = None

class SystemInfoResponse(BaseModel):
    app_version: str
    database_status: str
    superset_status: str
    total_connections: int
    total_users: int
    uptime: str

# Profile endpoints
@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at
    }

@router.put("/profile")
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    # Check if email or username already exists
    if profile_data.email and profile_data.email != current_user.email:
        existing_email = db.query(User).filter(
            User.email == profile_data.email,
            User.id != current_user.id
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    if profile_data.username and profile_data.username != current_user.username:
        existing_username = db.query(User).filter(
            User.username == profile_data.username,
            User.id != current_user.id
        ).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Update fields
    update_data = profile_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return {"message": "Profile updated successfully", "user": current_user}

# User settings endpoints
@router.get("/user-settings", response_model=UserSettingsResponse)
async def get_user_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user settings"""
    user_settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()
    
    if not user_settings:
        # Create default settings
        user_settings = UserSettings(user_id=current_user.id)
        db.add(user_settings)
        db.commit()
        db.refresh(user_settings)
    
    return user_settings

@router.put("/user-settings")
async def update_user_settings(
    settings_data: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user settings"""
    user_settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()
    
    if not user_settings:
        user_settings = UserSettings(user_id=current_user.id)
        db.add(user_settings)
    
    # Update settings
    update_data = settings_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user_settings, field, value)
    
    db.commit()
    db.refresh(user_settings)
    
    return {"message": "Settings updated successfully", "settings": user_settings}

# Connection settings (alias for user settings)
@router.get("/connection-settings")
async def get_connection_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get connection-related settings"""
    user_settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()
    
    if not user_settings:
        user_settings = UserSettings(user_id=current_user.id)
        db.add(user_settings)
        db.commit()
        db.refresh(user_settings)
    
    return {
        "data": {
            "auto_sync_to_superset": user_settings.auto_sync_to_superset,
            "default_sync_frequency": user_settings.default_sync_frequency,
            "connection_timeout": user_settings.connection_timeout,
            "max_retry_attempts": user_settings.max_retry_attempts,
            "encrypt_credentials": True  # Always true for security
        }
    }

@router.put("/connection-settings")
async def update_connection_settings(
    settings_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update connection-related settings"""
    user_settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()
    
    if not user_settings:
        user_settings = UserSettings(user_id=current_user.id)
        db.add(user_settings)
    
    # Update only connection-related fields
    if "auto_sync_to_superset" in settings_data:
        user_settings.auto_sync_to_superset = settings_data["auto_sync_to_superset"]
    if "default_sync_frequency" in settings_data:
        user_settings.default_sync_frequency = settings_data["default_sync_frequency"]
    if "connection_timeout" in settings_data:
        user_settings.connection_timeout = settings_data["connection_timeout"]
    if "max_retry_attempts" in settings_data:
        user_settings.max_retry_attempts = settings_data["max_retry_attempts"]
    
    db.commit()
    db.refresh(user_settings)
    
    return {"message": "Connection settings updated successfully"}

# Analytics settings
@router.get("/analytics-settings")
async def get_analytics_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analytics-related settings"""
    user_settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()
    
    if not user_settings:
        user_settings = UserSettings(user_id=current_user.id)
        db.add(user_settings)
        db.commit()
        db.refresh(user_settings)
    
    return {
        "data": {
            "superset_auto_create_datasets": user_settings.superset_auto_create_datasets,
            "superset_auto_create_dashboards": user_settings.superset_auto_create_dashboards,
            "data_retention_days": user_settings.data_retention_days,
            "enable_data_profiling": user_settings.enable_data_profiling
        }
    }

@router.put("/analytics-settings")
async def update_analytics_settings(
    settings_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update analytics-related settings"""
    user_settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()
    
    if not user_settings:
        user_settings = UserSettings(user_id=current_user.id)
        db.add(user_settings)
    
    # Update analytics fields
    if "superset_auto_create_datasets" in settings_data:
        user_settings.superset_auto_create_datasets = settings_data["superset_auto_create_datasets"]
    if "superset_auto_create_dashboards" in settings_data:
        user_settings.superset_auto_create_dashboards = settings_data["superset_auto_create_dashboards"]
    if "data_retention_days" in settings_data:
        user_settings.data_retention_days = settings_data["data_retention_days"]
    if "enable_data_profiling" in settings_data:
        user_settings.enable_data_profiling = settings_data["enable_data_profiling"]
    
    db.commit()
    db.refresh(user_settings)
    
    return {"message": "Analytics settings updated successfully"}

# ETL Schedules
@router.get("/etl-schedules")
async def get_etl_schedules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get ETL schedules for user's connections"""
    # Get user's connections with their schedules
    connections = db.query(DatabaseConnection).filter(
        DatabaseConnection.user_id == current_user.id
    ).all()
    
    schedules_data = []
    for conn in connections:
        schedule = db.query(ETLSchedule).filter(
            ETLSchedule.connection_id == conn.id
        ).first()
        
        if not schedule:
            # Create default schedule
            schedule = ETLSchedule(
                connection_id=conn.id,
                user_id=current_user.id,
                frequency="daily",
                scheduled_time="02:00",
                is_active=True
            )
            db.add(schedule)
            db.commit()
            db.refresh(schedule)
        
        schedules_data.append({
            "connection_id": conn.id,
            "connection_name": conn.name,
            "database_type": conn.database_type,
            "sync_frequency": schedule.frequency,
            "scheduled_time": schedule.scheduled_time,
            "is_active": schedule.is_active,
            "last_run": schedule.last_run,
            "next_run": schedule.next_run
        })
    
    return {"data": schedules_data}

@router.put("/etl-schedules/{connection_id}")
async def update_etl_schedule(
    connection_id: int,
    schedule_data: ETLScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update ETL schedule for a connection"""
    # Verify connection belongs to user
    connection = db.query(DatabaseConnection).filter(
        DatabaseConnection.id == connection_id,
        DatabaseConnection.user_id == current_user.id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    schedule = db.query(ETLSchedule).filter(
        ETLSchedule.connection_id == connection_id
    ).first()
    
    if not schedule:
        schedule = ETLSchedule(
            connection_id=connection_id,
            user_id=current_user.id
        )
        db.add(schedule)
    
    # Update schedule fields
    update_data = schedule_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(schedule, field, value)
    
    db.commit()
    db.refresh(schedule)
    
    return {"message": "Schedule updated successfully", "schedule": schedule}

# System information
@router.get("/system-info", response_model=SystemInfoResponse)
async def get_system_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get system information"""
    try:
        # Count total connections and users
        total_connections = db.query(DatabaseConnection).count()
        total_users = db.query(User).count()
        
        # Check database status
        db.execute("SELECT 1")
        database_status = "Connected"
        
        # Check Superset status (simplified)
        superset_status = "Available"  # You might want to implement actual health check
        
        return SystemInfoResponse(
            app_version=app_settings.VERSION if hasattr(app_settings, 'VERSION') else "1.0.0",
            database_status=database_status,
            superset_status=superset_status,
            total_connections=total_connections,
            total_users=total_users,
            uptime="System running"  # You might want to implement actual uptime tracking
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system information"
        )

# Notification settings
@router.get("/notification-settings")
async def get_notification_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get notification settings"""
    user_settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()
    
    if not user_settings:
        user_settings = UserSettings(user_id=current_user.id)
        db.add(user_settings)
        db.commit()
        db.refresh(user_settings)
    
    return {
        "data": {
            "email_notifications": user_settings.email_notifications,
            "etl_success_notifications": user_settings.etl_success_notifications,
            "etl_failure_notifications": user_settings.etl_failure_notifications,
            "weekly_reports": user_settings.weekly_reports
        }
    }

@router.put("/notification-settings")
async def update_notification_settings(
    settings_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update notification settings"""
    user_settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()
    
    if not user_settings:
        user_settings = UserSettings(user_id=current_user.id)
        db.add(user_settings)
    
    # Update notification fields
    if "email_notifications" in settings_data:
        user_settings.email_notifications = settings_data["email_notifications"]
    if "etl_success_notifications" in settings_data:
        user_settings.etl_success_notifications = settings_data["etl_success_notifications"]
    if "etl_failure_notifications" in settings_data:
        user_settings.etl_failure_notifications = settings_data["etl_failure_notifications"]
    if "weekly_reports" in settings_data:
        user_settings.weekly_reports = settings_data["weekly_reports"]
    
    db.commit()
    db.refresh(user_settings)
    
    return {"message": "Notification settings updated successfully"}

# Security settings placeholder
@router.get("/security-settings")
async def get_security_settings(
    current_user: User = Depends(get_current_user)
):
    """Get security settings (placeholder)"""
    return {
        "data": {
            "two_factor_enabled": False,
            "login_notifications": True,
            "session_timeout": 24,  # hours
            "password_strength": "strong"
        }
    }

@router.put("/security-settings")
async def update_security_settings(
    settings_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Update security settings (placeholder)"""
    return {"message": "Security settings will be implemented in future update"}