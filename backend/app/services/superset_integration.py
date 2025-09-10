import requests
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from ..db.database import SessionLocal
from ..models.connection import DatabaseConnection
from .superset_service import SupersetService
from .etl_service import ETLService
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class SupersetIntegration:
    """High-level service for managing Superset integration"""
    
    def __init__(self):
        self.superset_service = SupersetService()
        self.url = settings.SUPERSET_URL
        self.username = settings.SUPERSET_USERNAME
        self.password = settings.SUPERSET_PASSWORD
        logger.info(f"[{datetime.utcnow()}] SupersetIntegration initialized with URL: {self.url}")
    
    def sync_connection_to_superset(self, connection_id: int) -> bool:
        """Sync a database connection to Superset"""
        logger.info(f"[{datetime.utcnow()}] Starting sync for connection {connection_id} to Superset")
        
        db = SessionLocal()
        try:
            # Get the connection
            connection = db.query(DatabaseConnection).filter(
                DatabaseConnection.id == connection_id,
                DatabaseConnection.is_active == True
            ).first()
            
            if not connection:
                logger.error(f"[{datetime.utcnow()}] Connection {connection_id} not found or inactive")
                return False
            
            if connection.status != 'connected':
                logger.warning(f"[{datetime.utcnow()}] Connection {connection_id} is not in connected state: {connection.status}")
                return False
            
            logger.info(f"[{datetime.utcnow()}] Creating Superset database connection for '{connection.name}'")
            
            # Create database connection in Superset
            superset_db_id = self.superset_service.create_database_connection(connection)
            
            if superset_db_id:
                logger.info(f"[{datetime.utcnow()}] Successfully created Superset database connection {superset_db_id}")
                
                # Sync datasets immediately
                dataset_ids = self.superset_service.sync_datasets_for_connection(superset_db_id, connection_id)
                logger.info(f"[{datetime.utcnow()}] Created {len(dataset_ids)} datasets for connection {connection_id}")
                
                # Create a basic dashboard
                if dataset_ids:
                    dashboard_id = self.superset_service.create_basic_dashboard(connection.name, dataset_ids)
                    if dashboard_id:
                        logger.info(f"[{datetime.utcnow()}] Created dashboard {dashboard_id} for connection {connection_id}")
                
                logger.info(f"[{datetime.utcnow()}] Successfully synced connection {connection_id} to Superset (DB ID: {superset_db_id})")
                return True
            else:
                logger.error(f"[{datetime.utcnow()}] Failed to create Superset database for connection {connection_id}")
                return False
                
        except Exception as e:
            logger.error(f"[{datetime.utcnow()}] Error syncing connection {connection_id} to Superset: {str(e)}")
            import traceback
            logger.error(f"[{datetime.utcnow()}] Traceback: {traceback.format_exc()}")
            return False
        finally:
            db.close()
    
    def sync_datasets_after_etl(self, connection_id: int) -> bool:
        """Sync datasets to Superset after ETL completion"""
        logger.info(f"[{datetime.utcnow()}] Starting dataset sync for connection {connection_id} after ETL")
        
        try:
            db = SessionLocal()
            
            connection = db.query(DatabaseConnection).filter(
                DatabaseConnection.id == connection_id
            ).first()
            
            if not connection:
                logger.error(f"[{datetime.utcnow()}] Connection {connection_id} not found")
                return False
            
            logger.info(f"[{datetime.utcnow()}] Processing connection: {connection.name}")
            
            # Get the analytics tables for this connection
            etl_service = ETLService()
            analytics_tables = etl_service.get_analytics_tables(connection_id)
            
            if not analytics_tables:
                logger.warning(f"[{datetime.utcnow()}] No analytics tables found for connection {connection_id}")
                return True  # Not an error, just no data yet
            
            logger.info(f"[{datetime.utcnow()}] Found {len(analytics_tables)} analytics tables to sync: {analytics_tables}")
            
            # Step 1: Create or find Superset database connection for analytics database
            superset_db_id = self._create_or_find_analytics_database_connection(connection)
            
            if not superset_db_id:
                logger.error(f"[{datetime.utcnow()}] Failed to create/find Superset database connection for connection {connection_id}")
                return False
            
            logger.info(f"[{datetime.utcnow()}] Using Superset database ID: {superset_db_id}")
            
            # Step 2: Create datasets for each analytics table
            created_datasets = []
            for table_name in analytics_tables:
                logger.info(f"[{datetime.utcnow()}] Creating dataset for table: {table_name}")
                dataset_id = self._create_superset_dataset(superset_db_id, table_name, connection)
                if dataset_id:
                    created_datasets.append({
                        'table_name': table_name,
                        'dataset_id': dataset_id
                    })
                    logger.info(f"[{datetime.utcnow()}] Successfully created Superset dataset {dataset_id} for table {table_name}")
                else:
                    logger.warning(f"[{datetime.utcnow()}] Failed to create dataset for table {table_name}")
            
            # Step 3: Create a basic dashboard
            if created_datasets:
                logger.info(f"[{datetime.utcnow()}] Creating dashboard for {len(created_datasets)} datasets")
                dashboard_id = self._create_basic_dashboard(connection, created_datasets)
                if dashboard_id:
                    logger.info(f"[{datetime.utcnow()}] Created dashboard {dashboard_id} for connection {connection_id}")
            
            logger.info(f"[{datetime.utcnow()}] Dataset sync completed: {len(created_datasets)} datasets created for connection {connection_id}")
            return len(created_datasets) > 0
            
        except Exception as e:
            logger.error(f"[{datetime.utcnow()}] Error syncing datasets after ETL for connection {connection_id}: {str(e)}")
            import traceback
            logger.error(f"[{datetime.utcnow()}] Traceback: {traceback.format_exc()}")
            return False
        finally:
            if 'db' in locals():
                db.close()

    def _create_or_find_analytics_database_connection(self, connection: DatabaseConnection) -> Optional[int]:
        """Create or find the analytics database connection in Superset"""
        logger.info(f"[{datetime.utcnow()}] Creating or finding analytics database connection for {connection.name}")
        
        try:
            # Build connection to analytics database (not source database)
            analytics_db_name = f"{connection.name} - Analytics"
            analytics_uri = settings.ANALYTICS_DATABASE_URL
            
            logger.info(f"[{datetime.utcnow()}] Analytics DB name: {analytics_db_name}")
            logger.info(f"[{datetime.utcnow()}] Analytics URI: {analytics_uri}")
            
            # Use SupersetService to create database connection
            database_data = {
                "database_name": analytics_db_name,
                "sqlalchemy_uri": analytics_uri,
                "expose_in_sqllab": True,
                "allow_ctas": True,
                "allow_cvas": True,
                "allow_dml": False,  # Analytics is read-only
                "allow_run_async": True,
                "cache_timeout": 3600,
                "extra": json.dumps({
                    "metadata_params": {},
                    "engine_params": {
                        "connect_args": {
                            "sslmode": "disable"
                        },
                        "pool_recycle": 3600
                    },
                    "metadata_cache_timeout": {},
                    "schemas_allowed_for_file_upload": []
                })
            }
            
            # Try to create the database connection
            session = self.superset_service._authenticate()
            if not session:
                logger.error(f"[{datetime.utcnow()}] Failed to authenticate with Superset")
                return None
            
            # First, check if database already exists
            existing_db_id = self._find_existing_database(session, analytics_db_name)
            if existing_db_id:
                logger.info(f"[{datetime.utcnow()}] Found existing Superset database: {existing_db_id}")
                return existing_db_id
            
            # Create new database connection
            logger.info(f"[{datetime.utcnow()}] Creating new Superset database connection")
            response = session.post(f"{self.superset_service.base_url}/api/v1/database/", json=database_data)
            
            if response.status_code in [200, 201]:
                result = response.json()
                database_id = result.get('id')
                logger.info(f"[{datetime.utcnow()}] Created Superset analytics database connection with ID: {database_id}")
                return database_id
            else:
                logger.error(f"[{datetime.utcnow()}] Failed to create analytics database connection: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"[{datetime.utcnow()}] Error creating analytics database connection: {str(e)}")
            import traceback
            logger.error(f"[{datetime.utcnow()}] Traceback: {traceback.format_exc()}")
            return None

    def _find_existing_database(self, session: requests.Session, database_name: str) -> Optional[int]:
        """Find existing database connection by name"""
        logger.info(f"[{datetime.utcnow()}] Searching for existing database: {database_name}")
        
        try:
            response = session.get(f"{self.superset_service.base_url}/api/v1/database/")
            if response.status_code == 200:
                databases = response.json().get('result', [])
                logger.info(f"[{datetime.utcnow()}] Found {len(databases)} existing databases in Superset")
                
                for db in databases:
                    if db.get('database_name') == database_name:
                        logger.info(f"[{datetime.utcnow()}] Found matching database: {database_name} with ID {db.get('id')}")
                        return db.get('id')
                
                logger.info(f"[{datetime.utcnow()}] No existing database found with name: {database_name}")
                return None
            else:
                logger.error(f"[{datetime.utcnow()}] Failed to fetch databases: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"[{datetime.utcnow()}] Error finding existing database: {str(e)}")
            return None

    def _create_superset_dataset(self, database_id: int, table_name: str, connection: DatabaseConnection) -> Optional[int]:
        """Create a dataset in Superset for an analytics table"""
        logger.info(f"[{datetime.utcnow()}] Creating Superset dataset for table: {table_name}")
        
        try:
            session = self.superset_service._authenticate()
            if not session:
                logger.error(f"[{datetime.utcnow()}] Failed to authenticate for dataset creation")
                return None
            
            # Extract original table name from analytics table name (conn_1_users -> users)
            original_table = table_name.replace(f"conn_{connection.id}_", "")
            
            dataset_data = {
                "database": database_id,
                "schema": "public",  # Assuming public schema
                "table_name": table_name,
                "sql": None,  # Using table directly, not custom SQL
                "owners": [],
                # "description": f"Analytics dataset for {original_table} from {connection.name}",
                "external_url": None
            }
            
            logger.info(f"[{datetime.utcnow()}] Sending dataset creation request for {table_name}")
            response = session.post(
                f"{self.superset_service.base_url}/api/v1/dataset/",
                json=dataset_data
            )
            
            if response.status_code in [200, 201]:
                dataset_id = response.json().get('id')
                logger.info(f"[{datetime.utcnow()}] Created dataset {dataset_id} for table {table_name}")
                
                # Refresh dataset columns to ensure Superset knows about the schema
                self._refresh_dataset_columns(session, dataset_id)
                
                return dataset_id
            else:
                logger.error(f"[{datetime.utcnow()}] Failed to create dataset for {table_name}: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"[{datetime.utcnow()}] Error creating dataset for {table_name}: {str(e)}")
            import traceback
            logger.error(f"[{datetime.utcnow()}] Traceback: {traceback.format_exc()}")
            return None

    def _refresh_dataset_columns(self, session: requests.Session, dataset_id: int):
        """Refresh dataset columns to ensure Superset has the latest schema"""
        logger.info(f"[{datetime.utcnow()}] Refreshing columns for dataset {dataset_id}")
        
        try:
            response = session.put(f"{self.superset_service.base_url}/api/v1/dataset/{dataset_id}/refresh")
            if response.status_code == 200:
                logger.info(f"[{datetime.utcnow()}] Successfully refreshed columns for dataset {dataset_id}")
            else:
                logger.warning(f"[{datetime.utcnow()}] Failed to refresh dataset {dataset_id}: {response.status_code} - {response.text}")
        except Exception as e:
            logger.warning(f"[{datetime.utcnow()}] Error refreshing dataset columns: {str(e)}")

    def _create_basic_dashboard(self, connection: DatabaseConnection, datasets: List[Dict]) -> Optional[int]:
        """Create a basic dashboard with simple charts for the datasets"""
        logger.info(f"[{datetime.utcnow()}] Creating basic dashboard for connection {connection.name}")
        
        try:
            session = self.superset_service._authenticate()
            if not session:
                logger.error(f"[{datetime.utcnow()}] Failed to authenticate for dashboard creation")
                return None
            
            dashboard_title = f"{connection.name} - Analytics Dashboard"
            dashboard_slug = f"analytics-{connection.name.lower().replace(' ', '-')}-{connection.id}"
            
            dashboard_data = {
                "dashboard_title": dashboard_title,
                "slug": dashboard_slug,
                "published": True,
                "json_metadata": json.dumps({
                    "timed_refresh_immune_slices": [],
                    "expanded_slices": {},
                    "refresh_frequency": 0,
                    "default_filters": "{}",
                    "color_scheme": "supersetColors",
                    "label_colors": {}
                }),
                "position_json": json.dumps({
                    "DASHBOARD_VERSION_KEY": "v2",
                    "ROOT_ID": {
                        "children": [],
                        "id": "ROOT_ID",
                        "type": "ROOT"
                    }
                })
            }
            
            logger.info(f"[{datetime.utcnow()}] Sending dashboard creation request: {dashboard_title}")
            response = session.post(
                f"{self.superset_service.base_url}/api/v1/dashboard/",
                json=dashboard_data
            )
            
            if response.status_code in [200, 201]:
                dashboard_id = response.json().get('id')
                logger.info(f"[{datetime.utcnow()}] Successfully created dashboard {dashboard_id}: {dashboard_title}")
                return dashboard_id
            else:
                logger.error(f"[{datetime.utcnow()}] Failed to create dashboard: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"[{datetime.utcnow()}] Error creating dashboard: {str(e)}")
            import traceback
            logger.error(f"[{datetime.utcnow()}] Traceback: {traceback.format_exc()}")
            return None

    def sync_all_connections(self) -> Dict[str, Any]:
        """Sync all active, connected database connections to Superset"""
        logger.info(f"[{datetime.utcnow()}] Starting bulk sync of all connections to Superset")
        
        db = SessionLocal()
        results = {
            'synced': 0,
            'failed': 0,
            'skipped': 0,
            'details': [],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            connections = db.query(DatabaseConnection).filter(
                DatabaseConnection.is_active == True,
                DatabaseConnection.status == 'connected'
            ).all()
            
            logger.info(f"[{datetime.utcnow()}] Found {len(connections)} active connections to sync")
            
            for connection in connections:
                logger.info(f"[{datetime.utcnow()}] Processing connection {connection.id}: {connection.name}")
                
                try:
                    success = self.sync_connection_to_superset(connection.id)
                    if success:
                        results['synced'] += 1
                        results['details'].append({
                            'connection_id': connection.id,
                            'name': connection.name,
                            'status': 'synced',
                            'timestamp': datetime.utcnow().isoformat()
                        })
                        logger.info(f"[{datetime.utcnow()}] Successfully synced connection {connection.id}")
                    else:
                        results['failed'] += 1
                        results['details'].append({
                            'connection_id': connection.id,
                            'name': connection.name,
                            'status': 'failed',
                            'timestamp': datetime.utcnow().isoformat()
                        })
                        logger.error(f"[{datetime.utcnow()}] Failed to sync connection {connection.id}")
                        
                except Exception as e:
                    results['failed'] += 1
                    results['details'].append({
                        'connection_id': connection.id,
                        'name': connection.name,
                        'status': 'error',
                        'error': str(e),
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    logger.error(f"[{datetime.utcnow()}] Error syncing connection {connection.id}: {str(e)}")
            
            logger.info(f"[{datetime.utcnow()}] Bulk sync completed: {results['synced']} synced, {results['failed']} failed")
            return results
            
        except Exception as e:
            logger.error(f"[{datetime.utcnow()}] Error during bulk sync: {str(e)}")
            results['details'].append({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
            import traceback
            logger.error(f"[{datetime.utcnow()}] Traceback: {traceback.format_exc()}")
            return results
        finally:
            db.close()

    def get_superset_connection_status(self, connection_id: int) -> Dict[str, Any]:
        """Get the status of Superset integration for a connection"""
        logger.info(f"[{datetime.utcnow()}] Checking Superset status for connection {connection_id}")
        
        try:
            db = SessionLocal()
            connection = db.query(DatabaseConnection).filter(
                DatabaseConnection.id == connection_id
            ).first()
            
            if not connection:
                return {
                    'connection_id': connection_id,
                    'status': 'not_found',
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            # Get analytics tables
            etl_service = ETLService()
            analytics_tables = etl_service.get_analytics_tables(connection_id)
            
            # Check if Superset database exists
            analytics_db_name = f"{connection.name} - Analytics"
            session = self.superset_service._authenticate()
            superset_db_id = None
            if session:
                superset_db_id = self._find_existing_database(session, analytics_db_name)
            
            status = {
                'connection_id': connection_id,
                'connection_name': connection.name,
                'analytics_tables_count': len(analytics_tables),
                'analytics_tables': analytics_tables,
                'superset_database_id': superset_db_id,
                'superset_database_exists': superset_db_id is not None,
                'status': 'synced' if superset_db_id else 'not_synced',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"[{datetime.utcnow()}] Connection {connection_id} status: {status['status']}")
            return status
            
        except Exception as e:
            logger.error(f"[{datetime.utcnow()}] Error checking Superset status for connection {connection_id}: {str(e)}")
            return {
                'connection_id': connection_id,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
        finally:
            if 'db' in locals():
                db.close()

    def test_superset_connection(self) -> Dict[str, Any]:
        """Test connection to Superset"""
        logger.info(f"[{datetime.utcnow()}] Testing Superset connection")
        
        try:
            session = self.superset_service._authenticate()
            if session:
                # Test by getting database list
                response = session.get(f"{self.superset_service.base_url}/api/v1/database/")
                if response.status_code == 200:
                    db_count = len(response.json().get('result', []))
                    logger.info(f"[{datetime.utcnow()}] Superset connection successful - found {db_count} databases")
                    return {
                        'status': 'connected',
                        'database_count': db_count,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                else:
                    logger.error(f"[{datetime.utcnow()}] Superset API error: {response.status_code}")
                    return {
                        'status': 'api_error',
                        'error': f"API returned {response.status_code}",
                        'timestamp': datetime.utcnow().isoformat()
                    }
            else:
                logger.error(f"[{datetime.utcnow()}] Superset authentication failed")
                return {
                    'status': 'auth_failed',
                    'timestamp': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"[{datetime.utcnow()}] Superset connection test failed: {str(e)}")
            return {
                'status': 'connection_error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }