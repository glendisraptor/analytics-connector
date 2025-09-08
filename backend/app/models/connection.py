from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .user import Base
import enum

class DatabaseType(str, enum.Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"
    SQLITE = "sqlite"
    ORACLE = "oracle"
    MSSQL = "mssql"

class ConnectionStatus(str, enum.Enum):
    PENDING = "pending"
    CONNECTED = "connected"
    FAILED = "failed"
    TESTING = "testing"

class DatabaseConnection(Base):
    __tablename__ = "database_connections"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    database_type = Column(
        Enum(
            DatabaseType,
            name="database_type_enum",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False
    )
    encrypted_credentials = Column(Text, nullable=False)  # Encrypted connection details
    status = Column(
        Enum(
            ConnectionStatus,
            name="connection_status_enum",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        default=ConnectionStatus.PENDING.value,  # use the string value
        nullable=False
    )
    last_tested = Column(DateTime(timezone=True), nullable=True)
    last_sync = Column(DateTime(timezone=True), nullable=True)
    analytics_ready = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    sync_frequency = Column(String(50), default="daily")  # daily, hourly, weekly
    
    # Owner relationship
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="connections")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    jobs = relationship("ETLJob", back_populates="connection", cascade="all, delete-orphan")

class ETLJob(Base):
    __tablename__ = "etl_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=False)
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    job_type = Column(String(50), default="full_sync")  # full_sync, incremental, test
    records_processed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship
    connection = relationship("DatabaseConnection", back_populates="jobs")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())