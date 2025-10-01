"""
ETL (Extract, Transform, Load) Routes
Handles data extraction jobs and scheduling
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import DatabaseConnection, ETLJob, ETLSchedule, AuditLog
from app import db
from datetime import datetime, timedelta
import sqlalchemy as sa

etl_bp = Blueprint('etl', __name__)


def extract_data_from_connection(connection):
    """Extract data from a database connection"""
    from routes.database_connections import decrypt_credentials
    
    try:
        credentials = decrypt_credentials(connection.encrypted_credentials)
        
        if connection.database_type == 'postgresql':
            conn_string = f"postgresql://{credentials['username']}:{credentials['password']}@{credentials['host']}:{credentials.get('port', 5432)}/{credentials['database']}"
        elif connection.database_type == 'mysql':
            conn_string = f"mysql+pymysql://{credentials['username']}:{credentials['password']}@{credentials['host']}:{credentials.get('port', 3306)}/{credentials['database']}"
        else:
            return None, f"Unsupported database type: {connection.database_type}"
        
        engine = sa.create_engine(conn_string)
        inspector = sa.inspect(engine)
        
        # Get all tables
        tables_data = {}
        total_records = 0
        
        for table_name in inspector.get_table_names():
            with engine.connect() as conn:
                # Get row count
                result = conn.execute(sa.text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.scalar()
                
                # Get sample data (first 100 rows)
                result = conn.execute(sa.text(f"SELECT * FROM {table_name} LIMIT 100"))
                rows = [dict(row._mapping) for row in result]
                
                tables_data[table_name] = {
                    'row_count': count,
                    'sample_data': rows
                }
                
                total_records += count
        
        return {'tables': tables_data, 'total_records': total_records}, None
        
    except Exception as e:
        return None, str(e)


@etl_bp.route('/jobs', methods=['GET'])
@jwt_required()
def list_jobs():
    """List all ETL jobs for user's connections"""
    try:
        current_user_id = get_jwt_identity()
        
        # Get user's connections
        connections = DatabaseConnection.query.filter_by(owner_id=current_user_id).all()
        connection_ids = [c.id for c in connections]
        
        # Get jobs for these connections
        limit = int(request.args.get('limit', '50'))
        status = request.args.get('status')
        
        query = ETLJob.query.filter(ETLJob.connection_id.in_(connection_ids))
        
        if status:
            query = query.filter_by(status=status)
        
        jobs = query.order_by(ETLJob.created_at.desc()).limit(limit).all()
        
        return jsonify([job.to_dict() for job in jobs]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@etl_bp.route('/jobs/<int:job_id>', methods=['GET'])
@jwt_required()
def get_job(job_id):
    """Get specific ETL job details"""
    try:
        current_user_id = get_jwt_identity()
        
        job = ETLJob.query.get(job_id)
        
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        # Verify ownership through connection
        connection = DatabaseConnection.query.filter_by(
            id=job.connection_id,
            owner_id=current_user_id
        ).first()
        
        if not connection:
            return jsonify({'error': 'Unauthorized'}), 403
        
        return jsonify(job.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@etl_bp.route('/jobs/run/<int:connection_id>', methods=['POST'])
@jwt_required()
def run_etl_job(connection_id):
    """Manually trigger ETL job for a connection"""
    try:
        current_user_id = get_jwt_identity()
        
        connection = DatabaseConnection.query.filter_by(
            id=connection_id,
            owner_id=current_user_id
        ).first()
        
        if not connection:
            return jsonify({'error': 'Connection not found'}), 404
        
        if connection.status != 'connected':
            return jsonify({'error': 'Connection must be tested and connected first'}), 400
        
        # Create job
        job = ETLJob(
            connection_id=connection.id,
            status='pending',
            job_type='manual_sync'
        )
        
        db.session.add(job)
        db.session.flush()
        
        # Start job execution
        job.status = 'running'
        job.started_at = datetime.utcnow()
        
        db.session.commit()
        
        # Extract data
        data, error = extract_data_from_connection(connection)
        
        if error:
            job.status = 'failed'
            job.error_message = error
            job.completed_at = datetime.utcnow()
        else:
            job.status = 'completed'
            job.records_processed = data['total_records']
            job.completed_at = datetime.utcnow()
            
            # Update connection last_sync
            connection.last_sync = datetime.utcnow()
        
        # Log job execution
        audit_log = AuditLog(
            user_id=current_user_id,
            action='etl_job_executed',
            resource_type='etl_job',
            resource_id=job.id,
            details={
                'connection_id': connection.id,
                'status': job.status,
                'records_processed': job.records_processed
            }
        )
        db.session.add(audit_log)
        
        db.session.commit()
        
        return jsonify({
            'message': 'ETL job completed',
            'job': job.to_dict(),
            'data_summary': {
                'tables': len(data['tables']) if data else 0,
                'total_records': data['total_records'] if data else 0
            } if data else None
        }), 200
        
    except Exception as e:
        if 'job' in locals():
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
        
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@etl_bp.route('/schedules', methods=['GET'])
@jwt_required()
def list_schedules():
    """List all ETL schedules for user's connections"""
    try:
        current_user_id = get_jwt_identity()
        
        # Get user's connections
        connections = DatabaseConnection.query.filter_by(owner_id=current_user_id).all()
        connection_ids = [c.id for c in connections]
        
        schedules = ETLSchedule.query.filter(ETLSchedule.connection_id.in_(connection_ids)).all()
        
        return jsonify([schedule.to_dict() for schedule in schedules]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@etl_bp.route('/schedules', methods=['POST'])
@jwt_required()
def create_schedule():
    """Create ETL schedule for a connection"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        connection_id = data.get('connection_id')
        
        if not connection_id:
            return jsonify({'error': 'connection_id is required'}), 400
        
        connection = DatabaseConnection.query.filter_by(
            id=connection_id,
            owner_id=current_user_id
        ).first()
        
        if not connection:
            return jsonify({'error': 'Connection not found'}), 404
        
        # Check if schedule already exists
        existing_schedule = ETLSchedule.query.filter_by(connection_id=connection_id).first()
        
        if existing_schedule:
            return jsonify({'error': 'Schedule already exists for this connection'}), 409
        
        # Calculate next run time
        frequency = data.get('frequency', 'daily')
        scheduled_time = data.get('scheduled_time', '02:00')
        
        now = datetime.utcnow()
        hour, minute = map(int, scheduled_time.split(':'))
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if next_run <= now:
            if frequency == 'hourly':
                next_run += timedelta(hours=1)
            elif frequency == 'daily':
                next_run += timedelta(days=1)
            elif frequency == 'weekly':
                next_run += timedelta(weeks=1)
            elif frequency == 'monthly':
                next_run += timedelta(days=30)
        
        schedule = ETLSchedule(
            connection_id=connection_id,
            user_id=current_user_id,
            frequency=frequency,
            scheduled_time=scheduled_time,
            timezone=data.get('timezone', 'UTC'),
            is_active=data.get('is_active', True),
            days_of_week=data.get('days_of_week'),
            day_of_month=data.get('day_of_month'),
            next_run=next_run
        )
        
        db.session.add(schedule)
        
        # Log creation
        audit_log = AuditLog(
            user_id=current_user_id,
            action='etl_schedule_created',
            resource_type='etl_schedule',
            resource_id=schedule.id,
            details={'connection_id': connection_id, 'frequency': frequency}
        )
        db.session.add(audit_log)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Schedule created successfully',
            'schedule': schedule.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@etl_bp.route('/schedules/<int:schedule_id>', methods=['PUT'])
@jwt_required()
def update_schedule(schedule_id):
    """Update ETL schedule"""
    try:
        current_user_id = get_jwt_identity()
        
        schedule = ETLSchedule.query.filter_by(id=schedule_id, user_id=current_user_id).first()
        
        if not schedule:
            return jsonify({'error': 'Schedule not found'}), 404
        
        data = request.get_json()
        
        # Update allowed fields
        if 'frequency' in data:
            schedule.frequency = data['frequency']
        
        if 'scheduled_time' in data:
            schedule.scheduled_time = data['scheduled_time']
        
        if 'timezone' in data:
            schedule.timezone = data['timezone']
        
        if 'is_active' in data:
            schedule.is_active = data['is_active']
        
        if 'days_of_week' in data:
            schedule.days_of_week = data['days_of_week']
        
        if 'day_of_month' in data:
            schedule.day_of_month = data['day_of_month']
        
        schedule.updated_at = datetime.utcnow()
        
        # Recalculate next run if schedule changed
        if 'frequency' in data or 'scheduled_time' in data:
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
                    next_run += timedelta(days=30)
            
            schedule.next_run = next_run
        
        db.session.commit()
        
        return jsonify({
            'message': 'Schedule updated successfully',
            'schedule': schedule.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@etl_bp.route('/schedules/<int:schedule_id>', methods=['DELETE'])
@jwt_required()
def delete_schedule(schedule_id):
    """Delete ETL schedule"""
    try:
        current_user_id = get_jwt_identity()
        
        schedule = ETLSchedule.query.filter_by(id=schedule_id, user_id=current_user_id).first()
        
        if not schedule:
            return jsonify({'error': 'Schedule not found'}), 404
        
        db.session.delete(schedule)
        
        # Log deletion
        audit_log = AuditLog(
            user_id=current_user_id,
            action='etl_schedule_deleted',
            resource_type='etl_schedule',
            resource_id=schedule_id
        )
        db.session.add(audit_log)
        
        db.session.commit()
        
        return jsonify({'message': 'Schedule deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500