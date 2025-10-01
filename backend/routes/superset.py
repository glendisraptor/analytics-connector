"""
Superset Integration Routes - Complete Version
Handles connection to Apache Superset for analytics visualization
Auto-authenticates with admin/admin credentials
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import DatabaseConnection, AuditLog
from app import db
import requests
import json
from functools import wraps
from datetime import datetime, timedelta

superset_bp = Blueprint('superset', __name__)


class SupersetClient:
    """Client for interacting with Apache Superset API with automatic authentication"""
    
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.username = 'admin'  # Hardcoded username
        self.password = 'admin'  # Hardcoded password
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
    
    def login(self):
        """Authenticate with Superset and get access token"""
        try:
            url = f"{self.base_url}/api/v1/security/login"
            payload = {
                "username": 'admin',
                "password": 'admin',
                "provider": "db",
                "refresh": True
            }
            
            print(f"[Superset] Authenticating to {url} with username: {self.username}")
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token')
                self.refresh_token = data.get('refresh_token')
                
                # Set token expiry (typically 15 minutes for Superset)
                self.token_expiry = datetime.now() + timedelta(minutes=14)
                
                print(f"[Superset] Authentication successful")
                return True
            else:
                print(f"[Superset] Authentication failed: {response.status_code}")
                print(f"[Superset] Response: {response.text}")
                return False
            
        except requests.exceptions.Timeout:
            print(f"[Superset] Timeout connecting to {self.base_url}")
            return False
        except requests.exceptions.ConnectionError:
            print(f"[Superset] Cannot connect to {self.base_url}")
            return False
        except Exception as e:
            print(f"[Superset] Login error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def refresh_access_token(self):
        """Refresh the access token using refresh token"""
        if not self.refresh_token:
            return self.login()
        
        try:
            url = f"{self.base_url}/api/v1/security/refresh"
            headers = {
                "Authorization": f"Bearer {self.refresh_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token')
                self.token_expiry = datetime.now() + timedelta(minutes=14)
                print(f"[Superset] Token refreshed successfully")
                return True
            else:
                # If refresh fails, try full login
                print(f"[Superset] Token refresh failed, attempting re-login")
                return self.login()
                
        except Exception as e:
            print(f"[Superset] Token refresh error: {e}")
            return self.login()
    
    def is_token_valid(self):
        """Check if current token is valid and not expired"""
        if not self.access_token:
            return False
        
        if not self.token_expiry:
            return True  # Assume valid if no expiry set
        
        # Refresh if token expires in less than 1 minute
        return datetime.now() < (self.token_expiry - timedelta(minutes=1))
    
    def ensure_authenticated(self):
        """Ensure we have a valid authentication token"""
        if not self.is_token_valid():
            print(f"[Superset] Token expired or missing, authenticating...")
            return self.login()
        return True
    
    def get_headers(self):
        """Get authentication headers, automatically logging in if needed"""
        self.ensure_authenticated()
        
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def create_database(self, database_name, connection_uri, extra=None):
        """Create database connection in Superset"""
        self.ensure_authenticated()
        
        try:
            url = f"{self.base_url}/api/v1/database/"
            
            payload = {
                "database_name": database_name,
                "sqlalchemy_uri": connection_uri,
                "expose_in_sqllab": True,
                "allow_run_async": True,
                "allow_ctas": True,
                "allow_cvas": True,
                "allow_dml": False,
                "force_ctas_schema": "",
                "extra": json.dumps(extra or {})
            }
            
            response = requests.post(
                url, 
                headers=self.get_headers(), 
                json=payload, 
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                print(f"[Superset] Database '{database_name}' created successfully")
                return response.json()
            
            print(f"[Superset] Database creation failed: {response.status_code}")
            print(f"[Superset] Response: {response.text}")
            return None
            
        except Exception as e:
            print(f"[Superset] Error creating database: {e}")
            return None
    
    def list_databases(self):
        """List all databases in Superset"""
        self.ensure_authenticated()
        
        try:
            url = f"{self.base_url}/api/v1/database/"
            response = requests.get(
                url, 
                headers=self.get_headers(), 
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json().get('result', [])
            
            return []
            
        except Exception as e:
            print(f"[Superset] Error listing databases: {e}")
            return []
    
    def get_database(self, database_id):
        """Get specific database details"""
        self.ensure_authenticated()
        
        try:
            url = f"{self.base_url}/api/v1/database/{database_id}"
            response = requests.get(
                url, 
                headers=self.get_headers(), 
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json().get('result')
            
            return None
            
        except Exception as e:
            print(f"[Superset] Error getting database: {e}")
            return None
    
    def create_dataset(self, database_id, schema, table_name):
        """Create dataset in Superset"""
        self.ensure_authenticated()
        
        try:
            url = f"{self.base_url}/api/v1/dataset/"
            
            payload = {
                "database": database_id,
                "schema": schema,
                "table_name": table_name
            }
            
            response = requests.post(
                url, 
                headers=self.get_headers(), 
                json=payload, 
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                print(f"[Superset] Dataset '{table_name}' created successfully")
                return response.json()
            
            print(f"[Superset] Dataset creation failed: {response.status_code}")
            return None
            
        except Exception as e:
            print(f"[Superset] Error creating dataset: {e}")
            return None
    
    def list_datasets(self):
        """List all datasets in Superset"""
        self.ensure_authenticated()
        
        try:
            url = f"{self.base_url}/api/v1/dataset/"
            response = requests.get(
                url, 
                headers=self.get_headers(), 
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json().get('result', [])
            
            return []
            
        except Exception as e:
            print(f"[Superset] Error listing datasets: {e}")
            return []
    
    def test_connection(self, database_id):
        """Test database connection in Superset"""
        self.ensure_authenticated()
        
        try:
            url = f"{self.base_url}/api/v1/database/test_connection"
            
            payload = {
                "id": database_id
            }
            
            response = requests.post(
                url, 
                headers=self.get_headers(), 
                json=payload, 
                timeout=10
            )
            
            if response.status_code == 200:
                return True, "Connection successful"
            
            return False, response.text
            
        except Exception as e:
            return False, str(e)
    
    def health_check(self):
        """Check if Superset is accessible and can authenticate"""
        try:
            # Try to authenticate
            if not self.login():
                return False, "Authentication failed"
            
            # Try a simple API call
            databases = self.list_databases()
            
            return True, f"Connected successfully, {len(databases)} databases found"
            
        except Exception as e:
            return False, str(e)


def get_superset_client():
    """Get configured Superset client with auto-authentication"""
    return SupersetClient(current_app.config['SUPERSET_URL'])


@superset_bp.route('/sync-all', methods=['POST'])
@jwt_required()
def sync_all_connections():
    """Sync all active database connections to Superset"""
    try:
        current_user_id = int(get_jwt_identity())
        
        # Get all active connections for the user
        connections = DatabaseConnection.query.filter_by(
            owner_id=current_user_id,
            is_active=True
        ).all()
        
        if not connections:
            return jsonify({
                'message': 'No active connections to sync',
                'synced': 0,
                'failed': 0,
                'results': []
            }), 200
        
        # Get Superset client (will auto-authenticate on first API call)
        client = get_superset_client()
        
        results = []
        synced_count = 0
        failed_count = 0
        
        from routes.database_connections import decrypt_credentials
        
        for connection in connections:
            try:
                # Skip if not connected
                if connection.status != 'connected':
                    results.append({
                        'connection_id': connection.id,
                        'connection_name': connection.name,
                        'status': 'skipped',
                        'message': 'Connection not tested or failed'
                    })
                    failed_count += 1
                    continue
                
                # Decrypt credentials and build connection URI
                credentials = decrypt_credentials(connection.encrypted_credentials)
                
                if connection.database_type == 'postgresql':
                    conn_uri = f"postgresql://{credentials['username']}:{credentials['password']}@{credentials['host']}:{credentials.get('port', 5432)}/{credentials['database']}"
                elif connection.database_type == 'mysql':
                    conn_uri = f"mysql+pymysql://{credentials['username']}:{credentials['password']}@{credentials['host']}:{credentials.get('port', 3306)}/{credentials['database']}"
                else:
                    results.append({
                        'connection_id': connection.id,
                        'connection_name': connection.name,
                        'status': 'failed',
                        'message': f'Database type {connection.database_type} not supported'
                    })
                    failed_count += 1
                    continue
                
                # Create database in Superset (will auto-authenticate)
                superset_db = client.create_database(
                    database_name=f"analytics_connector_{connection.name}",
                    connection_uri=conn_uri
                )
                
                if superset_db:
                    connection.analytics_ready = True
                    
                    results.append({
                        'connection_id': connection.id,
                        'connection_name': connection.name,
                        'status': 'success',
                        'superset_database_id': superset_db.get('id'),
                        'message': 'Successfully synced to Superset'
                    })
                    synced_count += 1
                else:
                    results.append({
                        'connection_id': connection.id,
                        'connection_name': connection.name,
                        'status': 'failed',
                        'message': 'Failed to create database in Superset'
                    })
                    failed_count += 1
                    
            except Exception as conn_error:
                print(f"Error syncing connection {connection.id}: {conn_error}")
                results.append({
                    'connection_id': connection.id,
                    'connection_name': connection.name,
                    'status': 'failed',
                    'message': str(conn_error)
                })
                failed_count += 1
        
        # Save all changes
        db.session.commit()
        
        # Log sync all action
        audit_log = AuditLog(
            user_id=current_user_id,
            action='superset_sync_all',
            resource_type='superset',
            details={
                'total_connections': len(connections),
                'synced': synced_count,
                'failed': failed_count
            }
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({
            'message': f'Sync completed: {synced_count} successful, {failed_count} failed',
            'total_connections': len(connections),
            'synced': synced_count,
            'failed': failed_count,
            'results': results
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in sync_all_connections: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@superset_bp.route('/status', methods=['GET'])
@jwt_required()
def superset_status():
    """Check Superset connection status and return user's database connections"""
    try:
        current_user_id = int(get_jwt_identity())
        
        # Get user's database connections
        connections = DatabaseConnection.query.filter_by(
            owner_id=current_user_id,
            is_active=True
        ).all()
        
        # Convert connections to dict
        connections_data = [conn.to_dict() for conn in connections]
        
        client = get_superset_client()
        
        # health_check will automatically authenticate
        is_connected, message = client.health_check()
        
        if is_connected:
            databases = client.list_databases()
            return jsonify({
                'status': 'connected',
                'superset_url': current_app.config['SUPERSET_URL'],
                'database_count': len(databases),
                'message': message,
                'connections': connections_data,
                'connections_count': len(connections_data)
            }), 200
        
        return jsonify({
            'status': 'disconnected',
            'error': message,
            'connections': connections_data,
            'connections_count': len(connections_data)
        }), 500
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@superset_bp.route('/info', methods=['GET'])
@jwt_required()
def get_superset_info():
    """Get Superset configuration and connection status"""
    try:
        current_user_id = int(get_jwt_identity())
        
        # Get Superset configuration from app config
        superset_url = current_app.config.get('SUPERSET_URL')
        
        # Check if Superset is configured
        is_configured = bool(superset_url)
        
        response_data = {
            'superset_url': superset_url,
            'is_configured': is_configured,
            'connection_status': 'unknown',
            'username': 'admin'  # Hardcoded username
        }
        
        # Try to connect if configured
        if is_configured:
            try:
                client = get_superset_client()
                is_connected, message = client.health_check()
                
                if is_connected:
                    response_data['connection_status'] = 'connected'
                    
                    # Get additional info if connected
                    databases = client.list_databases()
                    datasets = client.list_datasets()
                    
                    response_data['database_count'] = len(databases)
                    response_data['dataset_count'] = len(datasets)
                    response_data['message'] = message
                else:
                    response_data['connection_status'] = 'authentication_failed'
                    response_data['error'] = message
            except Exception as e:
                response_data['connection_status'] = 'connection_failed'
                response_data['error'] = str(e)
        
        # Log access
        audit_log = AuditLog(
            user_id=current_user_id,
            action='superset_info_accessed',
            resource_type='superset',
            details={'status': response_data['connection_status']}
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"Error getting Superset info: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@superset_bp.route('/sync/<int:connection_id>', methods=['POST'])
@jwt_required()
def sync_to_superset(connection_id):
    """Sync single database connection to Superset"""
    try:
        current_user_id = get_jwt_identity()
        
        # Get database connection
        connection = DatabaseConnection.query.filter_by(
            id=connection_id,
            owner_id=current_user_id
        ).first()
        
        if not connection:
            return jsonify({'error': 'Connection not found'}), 404
        
        if connection.status != 'connected':
            return jsonify({'error': 'Database connection must be tested and connected first'}), 400
        
        # Get Superset client (will auto-authenticate)
        client = get_superset_client()
        
        # Decrypt credentials and build connection URI
        from routes.database_connections import decrypt_credentials
        credentials = decrypt_credentials(connection.encrypted_credentials)
        
        if connection.database_type == 'postgresql':
            conn_uri = f"postgresql://{credentials['username']}:{credentials['password']}@{credentials['host']}:{credentials.get('port', 5432)}/{credentials['database']}"
        elif connection.database_type == 'mysql':
            conn_uri = f"mysql+pymysql://{credentials['username']}:{credentials['password']}@{credentials['host']}:{credentials.get('port', 3306)}/{credentials['database']}"
        else:
            return jsonify({'error': f'Database type {connection.database_type} not supported'}), 400
        
        # Create database in Superset (will auto-authenticate)
        superset_db = client.create_database(
            database_name=f"analytics_connector_{connection.name}",
            connection_uri=conn_uri
        )
        
        if not superset_db:
            return jsonify({'error': 'Failed to create database in Superset'}), 500
        
        # Update connection
        connection.analytics_ready = True
        
        # Log sync
        audit_log = AuditLog(
            user_id=current_user_id,
            action='superset_sync',
            resource_type='database_connection',
            resource_id=connection.id,
            details={'superset_database_id': superset_db.get('id')}
        )
        db.session.add(audit_log)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Database synced to Superset successfully',
            'superset_database_id': superset_db.get('id'),
            'connection': connection.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@superset_bp.route('/databases', methods=['GET'])
@jwt_required()
def list_superset_databases():
    """List all databases in Superset"""
    try:
        client = get_superset_client()
        
        # Will auto-authenticate
        databases = client.list_databases()
        
        return jsonify({'databases': databases}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@superset_bp.route('/datasets', methods=['GET'])
@jwt_required()
def list_superset_datasets():
    """List all datasets in Superset"""
    try:
        client = get_superset_client()
        
        # Will auto-authenticate
        datasets = client.list_datasets()
        
        return jsonify({'datasets': datasets}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@superset_bp.route('/datasets/create', methods=['POST'])
@jwt_required()
def create_superset_dataset():
    """Create dataset in Superset from table"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        required_fields = ['database_id', 'schema', 'table_name']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        client = get_superset_client()
        
        # Will auto-authenticate
        dataset = client.create_dataset(
            database_id=data['database_id'],
            schema=data['schema'],
            table_name=data['table_name']
        )
        
        if not dataset:
            return jsonify({'error': 'Failed to create dataset in Superset'}), 500
        
        # Log creation
        audit_log = AuditLog(
            user_id=current_user_id,
            action='superset_dataset_created',
            resource_type='superset_dataset',
            details={
                'database_id': data['database_id'],
                'table_name': data['table_name'],
                'dataset_id': dataset.get('id')
            }
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({
            'message': 'Dataset created successfully',
            'dataset': dataset
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500