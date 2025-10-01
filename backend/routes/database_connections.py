"""
Database Connections Routes
Handles CRUD operations for database connections
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import DatabaseConnection, User, AuditLog
from app import db
from datetime import datetime
import json
from cryptography.fernet import Fernet
import sqlalchemy as sa

db_connections_bp = Blueprint('db_connections', __name__)

def get_encryption_key():
    """Get or create encryption key for credentials"""
    key = current_app.config.get('ENCRYPTION_KEY')
    if not key:
        key = Fernet.generate_key()
        current_app.config['ENCRYPTION_KEY'] = key
    return key

def encrypt_credentials(credentials):
    """Encrypt database credentials"""
    f = Fernet(get_encryption_key())
    credentials_json = json.dumps(credentials)
    return f.encrypt(credentials_json.encode()).decode()

def decrypt_credentials(encrypted_credentials):
    """Decrypt database credentials"""
    f = Fernet(get_encryption_key())
    decrypted = f.decrypt(encrypted_credentials.encode())
    return json.loads(decrypted.decode())

def test_database_connection(db_type, credentials):
    """Test if database connection is valid"""
    try:
        if db_type == 'postgresql':
            conn_string = f"postgresql://{credentials['username']}:{credentials['password']}@{credentials['host']}:{credentials.get('port', 5432)}/{credentials['database']}"
            engine = sa.create_engine(conn_string)
            with engine.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
            return True, "Connection successful"
        
        elif db_type == 'mysql':
            conn_string = f"mysql+pymysql://{credentials['username']}:{credentials['password']}@{credentials['host']}:{credentials.get('port', 3306)}/{credentials['database']}"
            engine = sa.create_engine(conn_string)
            with engine.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
            return True, "Connection successful"
        
        # Add other database types as needed
        else:
            return False, f"Database type {db_type} not yet supported"
            
    except Exception as e:
        return False, str(e)


@db_connections_bp.route('/', methods=['GET'])
@jwt_required()
def list_connections():
    """List all database connections for current user"""
    try:
        current_user_id = get_jwt_identity()
        
        connections = DatabaseConnection.query.filter_by(
            owner_id=current_user_id,
            is_active=True
        ).all()
        
        return jsonify([conn.to_dict() for conn in connections]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@db_connections_bp.route('/<int:connection_id>', methods=['GET'])
@jwt_required()
def get_connection(connection_id):
    """Get specific database connection"""
    try:
        current_user_id = get_jwt_identity()
        
        connection = DatabaseConnection.query.filter_by(
            id=connection_id,
            owner_id=current_user_id
        ).first()
        
        if not connection:
            return jsonify({'error': 'Connection not found'}), 404
        
        return jsonify(connection.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@db_connections_bp.route('/', methods=['POST'])
@jwt_required()
def create_connection():
    """Create new database connection"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'database_type', 'credentials']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Encrypt credentials
        encrypted_creds = encrypt_credentials(data['credentials'])
        
        # Create connection
        connection = DatabaseConnection(
            name=data['name'],
            database_type=data['database_type'],
            encrypted_credentials=encrypted_creds,
            sync_frequency=data.get('sync_frequency', 'daily'),
            owner_id=current_user_id,
            status='pending'
        )
        
        db.session.add(connection)
        db.session.flush()
        
        # Log creation
        audit_log = AuditLog(
            user_id=current_user_id,
            action='connection_created',
            resource_type='database_connection',
            resource_id=connection.id,
            details={'name': connection.name, 'type': connection.database_type}
        )
        db.session.add(audit_log)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Connection created successfully',
            'connection': connection.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@db_connections_bp.route('/<int:connection_id>/test', methods=['POST'])
@jwt_required()
def test_connection(connection_id):
    """Test database connection"""
    try:
        current_user_id = get_jwt_identity()
        
        connection = DatabaseConnection.query.filter_by(
            id=connection_id,
            owner_id=current_user_id
        ).first()
        
        if not connection:
            return jsonify({'error': 'Connection not found'}), 404
        
        # Decrypt credentials
        credentials = decrypt_credentials(connection.encrypted_credentials)
        
        # Test connection
        success, message = test_database_connection(connection.database_type, credentials)
        
        # Update status
        connection.status = 'connected' if success else 'failed'
        connection.last_tested = datetime.utcnow()
        
        # Log test
        audit_log = AuditLog(
            user_id=current_user_id,
            action='connection_tested',
            resource_type='database_connection',
            resource_id=connection.id,
            details={'success': success, 'message': message}
        )
        db.session.add(audit_log)
        
        db.session.commit()
        
        return jsonify({
            'success': success,
            'message': message,
            'connection': connection.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@db_connections_bp.route('/<int:connection_id>', methods=['PUT'])
@jwt_required()
def update_connection(connection_id):
    """Update database connection"""
    try:
        current_user_id = get_jwt_identity()
        
        connection = DatabaseConnection.query.filter_by(
            id=connection_id,
            owner_id=current_user_id
        ).first()
        
        if not connection:
            return jsonify({'error': 'Connection not found'}), 404
        
        data = request.get_json()
        
        # Update allowed fields
        if 'name' in data:
            connection.name = data['name']
        
        if 'credentials' in data:
            connection.encrypted_credentials = encrypt_credentials(data['credentials'])
            connection.status = 'pending'  # Needs re-testing
        
        if 'sync_frequency' in data:
            connection.sync_frequency = data['sync_frequency']
        
        connection.updated_at = datetime.utcnow()
        
        # Log update
        audit_log = AuditLog(
            user_id=current_user_id,
            action='connection_updated',
            resource_type='database_connection',
            resource_id=connection.id,
            details={'updated_fields': list(data.keys())}
        )
        db.session.add(audit_log)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Connection updated successfully',
            'connection': connection.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@db_connections_bp.route('/<int:connection_id>', methods=['DELETE'])
@jwt_required()
def delete_connection(connection_id):
    """Delete database connection (soft delete)"""
    try:
        current_user_id = get_jwt_identity()
        
        connection = DatabaseConnection.query.filter_by(
            id=connection_id,
            owner_id=current_user_id
        ).first()
        
        if not connection:
            return jsonify({'error': 'Connection not found'}), 404
        
        # Soft delete
        connection.is_active = False
        connection.updated_at = datetime.utcnow()
        
        # Log deletion
        audit_log = AuditLog(
            user_id=current_user_id,
            action='connection_deleted',
            resource_type='database_connection',
            resource_id=connection.id,
            details={'name': connection.name}
        )
        db.session.add(audit_log)
        
        db.session.commit()
        
        return jsonify({'message': 'Connection deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@db_connections_bp.route('/<int:connection_id>/schema', methods=['GET'])
@jwt_required()
def get_connection_schema(connection_id):
    """Get database schema (tables and columns)"""
    try:
        current_user_id = get_jwt_identity()
        
        connection = DatabaseConnection.query.filter_by(
            id=connection_id,
            owner_id=current_user_id
        ).first()
        
        if not connection:
            return jsonify({'error': 'Connection not found'}), 404
        
        if connection.status != 'connected':
            return jsonify({'error': 'Connection not tested or failed'}), 400
        
        # Decrypt credentials
        credentials = decrypt_credentials(connection.encrypted_credentials)
        
        # Get schema information
        if connection.database_type == 'postgresql':
            conn_string = f"postgresql://{credentials['username']}:{credentials['password']}@{credentials['host']}:{credentials.get('port', 5432)}/{credentials['database']}"
            engine = sa.create_engine(conn_string)
            inspector = sa.inspect(engine)
            
            tables = []
            for table_name in inspector.get_table_names():
                columns = []
                for column in inspector.get_columns(table_name):
                    columns.append({
                        'name': column['name'],
                        'type': str(column['type']),
                        'nullable': column['nullable']
                    })
                tables.append({
                    'name': table_name,
                    'columns': columns
                })
            
            return jsonify({'tables': tables}), 200
        
        return jsonify({'error': 'Schema inspection not supported for this database type'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500