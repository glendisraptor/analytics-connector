"""
Database Models for Analytics Connector
Includes User, DatabaseConnection, DocumentTable, ETL, and related models
"""
from datetime import datetime
from app import db
from sqlalchemy.dialects.postgresql import JSONB, INET

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    hashed_password = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, index=True)
    is_superuser = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    settings = db.relationship('UserSettings', backref='user', uselist=False, cascade='all, delete-orphan')
    connections = db.relationship('DatabaseConnection', backref='owner', lazy=True, cascade='all, delete-orphan')
    document_tables = db.relationship('DocumentTable', backref='owner', lazy=True)
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'full_name': self.full_name,
            'is_active': self.is_active,
            'is_superuser': self.is_superuser,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class UserSettings(db.Model):
    __tablename__ = 'user_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Connection Settings
    auto_sync_to_superset = db.Column(db.Boolean, default=True)
    default_sync_frequency = db.Column(db.String(20), default='daily')
    connection_timeout = db.Column(db.Integer, default=30)
    max_retry_attempts = db.Column(db.Integer, default=3)
    
    # Analytics Settings
    superset_auto_create_datasets = db.Column(db.Boolean, default=True)
    superset_auto_create_dashboards = db.Column(db.Boolean, default=False)
    data_retention_days = db.Column(db.Integer, default=365)
    enable_data_profiling = db.Column(db.Boolean, default=True)
    
    # Notification Settings
    email_notifications = db.Column(db.Boolean, default=True)
    etl_success_notifications = db.Column(db.Boolean, default=False)
    etl_failure_notifications = db.Column(db.Boolean, default=True)
    weekly_reports = db.Column(db.Boolean, default=False)
    
    # UI Settings
    theme = db.Column(db.String(20), default='light')
    timezone = db.Column(db.String(50), default='UTC')
    date_format = db.Column(db.String(20), default='YYYY-MM-DD')
    
    additional_settings = db.Column(JSONB, default={})
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'auto_sync_to_superset': self.auto_sync_to_superset,
            'default_sync_frequency': self.default_sync_frequency,
            'connection_timeout': self.connection_timeout,
            'theme': self.theme,
            'timezone': self.timezone
        }


class DatabaseConnection(db.Model):
    __tablename__ = 'database_connections'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    database_type = db.Column(db.String(50), nullable=False)
    encrypted_credentials = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='pending')
    last_tested = db.Column(db.DateTime)
    analytics_ready = db.Column(db.Boolean, default=False)
    last_sync = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True, index=True)
    sync_frequency = db.Column(db.String(20), default='daily')
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    etl_jobs = db.relationship('ETLJob', backref='connection', lazy=True, cascade='all, delete-orphan')
    etl_schedule = db.relationship('ETLSchedule', backref='connection', uselist=False, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'database_type': self.database_type,
            'status': self.status,
            'last_tested': self.last_tested.isoformat() if self.last_tested else None,
            'analytics_ready': self.analytics_ready,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'is_active': self.is_active,
            'sync_frequency': self.sync_frequency,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ETLSchedule(db.Model):
    __tablename__ = 'etl_schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    connection_id = db.Column(db.Integer, db.ForeignKey('database_connections.id', ondelete='CASCADE'), 
                             nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    frequency = db.Column(db.String(20), nullable=False, default='daily')
    scheduled_time = db.Column(db.String(8), default='02:00')
    timezone = db.Column(db.String(50), default='UTC')
    is_active = db.Column(db.Boolean, default=True)
    days_of_week = db.Column(db.String(20))
    day_of_month = db.Column(db.Integer)
    last_run = db.Column(db.DateTime)
    next_run = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'connection_id': self.connection_id,
            'frequency': self.frequency,
            'scheduled_time': self.scheduled_time,
            'timezone': self.timezone,
            'is_active': self.is_active,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None
        }


class ETLJob(db.Model):
    __tablename__ = 'etl_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    connection_id = db.Column(db.Integer, db.ForeignKey('database_connections.id', ondelete='CASCADE'), 
                             nullable=False, index=True)
    status = db.Column(db.String(50), default='pending', index=True)
    job_type = db.Column(db.String(50), default='full_sync')
    records_processed = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'connection_id': self.connection_id,
            'status': self.status,
            'job_type': self.job_type,
            'records_processed': self.records_processed,
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class DocumentTable(db.Model):
    __tablename__ = 'document_tables'
    
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    is_configured = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True, index=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    fields = db.relationship('DocumentField', backref='document_table', lazy=True, cascade='all, delete-orphan')
    results = db.relationship('DocumentResult', backref='document_table', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'table_id': self.table_id,
            'name': self.name,
            'description': self.description,
            'is_configured': self.is_configured,
            'is_active': self.is_active,
            'fields': [f.to_dict() for f in self.fields],
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class DocumentField(db.Model):
    __tablename__ = 'document_fields'
    
    id = db.Column(db.Integer, primary_key=True)
    field_id = db.Column(db.String(100), nullable=False)
    document_table_id = db.Column(db.Integer, db.ForeignKey('document_tables.id', ondelete='CASCADE'), 
                                  nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    field_type = db.Column(db.String(50), nullable=False)
    is_required = db.Column(db.Boolean, default=False)
    validation_rules = db.Column(JSONB)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'field_id': self.field_id,
            'name': self.name,
            'field_type': self.field_type,
            'is_required': self.is_required,
            'display_order': self.display_order
        }


class DocumentResult(db.Model):
    __tablename__ = 'document_results'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(512), nullable=False, index=True)
    stored_path = db.Column(db.String(1024))
    file_hash = db.Column(db.String(64), index=True)
    file_size = db.Column(db.Integer)
    document_table_id = db.Column(db.Integer, db.ForeignKey('document_tables.id', ondelete='SET NULL'), index=True)
    table_id = db.Column(db.String(255))
    table_name = db.Column(db.String(255))
    fields_mapped = db.Column(JSONB)
    fields_by_name = db.Column(JSONB)
    extracted_text = db.Column(db.Text)
    model_id = db.Column(db.String(255))
    extraction_method = db.Column(db.String(50), default='groq')
    processing_time_ms = db.Column(db.Integer)
    confidence_score = db.Column(db.Numeric(3, 2))
    status = db.Column(db.String(50), default='completed', index=True)
    error_message = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'stored_path': self.stored_path,
            'document_table_id': self.document_table_id,
            'table_id': self.table_id,
            'table_name': self.table_name,
            'fields_mapped': self.fields_mapped,
            'fields_by_name': self.fields_by_name,
            'extracted_text': self.extracted_text[:200] if self.extracted_text else None,
            'model_id': self.model_id,
            'status': self.status,
            'processing_time_ms': self.processing_time_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), index=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    resource_type = db.Column(db.String(50), index=True)
    resource_id = db.Column(db.Integer)
    details = db.Column(JSONB)
    ip_address = db.Column(INET)
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }