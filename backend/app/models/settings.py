from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .user import Base

class UserSettings(Base):
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Connection Settings
    auto_sync_to_superset = Column(Boolean, default=True)
    default_sync_frequency = Column(String(50), default="daily")
    connection_timeout = Column(Integer, default=30)
    max_retry_attempts = Column(Integer, default=3)
    
    # Analytics Settings
    superset_auto_create_datasets = Column(Boolean, default=True)
    superset_auto_create_dashboards = Column(Boolean, default=False)
    data_retention_days = Column(Integer, default=365)
    enable_data_profiling = Column(Boolean, default=True)
    
    # Notification Settings
    email_notifications = Column(Boolean, default=True)
    etl_success_notifications = Column(Boolean, default=False)
    etl_failure_notifications = Column(Boolean, default=True)
    weekly_reports = Column(Boolean, default=False)
    
    # UI Settings
    theme = Column(String(20), default="light")
    timezone = Column(String(50), default="UTC")
    date_format = Column(String(20), default="YYYY-MM-DD")
    
    # Additional settings as JSON
    additional_settings = Column(JSON, default={})
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    user = relationship("User", back_populates="settings")

# Add to User model (in user.py)
# settings = relationship("UserSettings", back_populates="user", uselist=False)

class ETLSchedule(Base):
    __tablename__ = "etl_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Schedule Configuration
    frequency = Column(String(20), nullable=False)  # hourly, daily, weekly, monthly
    scheduled_time = Column(String(8), default="02:00")  # HH:MM format
    timezone = Column(String(50), default="UTC")
    is_active = Column(Boolean, default=True)
    
    # Advanced Options
    days_of_week = Column(String(20))  # For weekly: "1,3,5" (Mon, Wed, Fri)
    day_of_month = Column(Integer)  # For monthly: 1-31
    
    # Last execution tracking
    last_run = Column(DateTime(timezone=True))
    next_run = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())