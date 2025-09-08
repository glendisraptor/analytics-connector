import requests
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from ..core.config import settings
from ..utils.encryption import encryption_service
from ..models.connection import DatabaseConnection, DatabaseType

logger = logging.getLogger(__name__)

class SupersetService:
    """
    Service for integrating with Apache Superset.
    Each method now handles its own authentication to ensure robustness
    in short-lived execution environments.
    """
    
    def __init__(self):
        self.base_url = settings.SUPERSET_URL.rstrip('/')
        self.username = settings.SUPERSET_USERNAME
        self.password = settings.SUPERSET_PASSWORD

    def _authenticate(self) -> Optional[requests.Session]:
        """
        Handles the full authentication flow and returns a session object
        with all necessary headers.
        """
        session = requests.Session()
        
        try:
            login_payload = {
                "username": self.username,
                "password": self.password,
                "provider": "db",
                "refresh": True
            }

            # Step 1: Login to get access token
            login_response = session.post(
                f"{self.base_url}/api/v1/security/login",
                json=login_payload,
                headers={"Content-Type": "application/json"}
            )

            if login_response.status_code != 200:
                logger.error(f"Login failed: {login_response.text}")
                return None

            token_data = login_response.json()
            access_token = token_data.get("access_token")
            if not access_token:
                logger.error("No access_token in login response")
                return None

            # Attach Bearer token to session headers
            session.headers.update({
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            })

            # Step 2: Get CSRF token
            csrf_response = session.get(f"{self.base_url}/api/v1/security/csrf_token/")
            if csrf_response.status_code != 200:
                logger.error(f"Failed to fetch CSRF token: {csrf_response.text}")
                return None

            csrf_token = csrf_response.json().get("result")
            if not csrf_token:
                logger.error("No CSRF token in response")
                return None

            # Attach CSRF header to session headers
            session.headers.update({
                "X-CSRFToken": csrf_token
            })

            logger.info("✅ Successfully authenticated with Superset API")
            return session

        except Exception as e:
            logger.error(f"Error authenticating with Superset: {str(e)}")
            return None

    def create_database_connection(self, connection: DatabaseConnection) -> Optional[int]:
        """Create a database connection in Superset"""
        session = self._authenticate()
        if not session:
            return None
        
        try:
            # Decrypt credentials
            credentials = encryption_service.decrypt_credentials(connection.encrypted_credentials)
            
            # Build SQLAlchemy URI
            sqlalchemy_uri = self._build_sqlalchemy_uri(connection.database_type, credentials)
            if not sqlalchemy_uri:
                logger.error(f"Could not build SQLAlchemy URI for {connection.database_type}")
                return None
            
            print("***********************************************")
            print(connection.name)
            print("SQLAlchemy URI:", sqlalchemy_uri)
            print("***********************************************")
            
            # Prepare database payload
            database_data = {
                "database_name": f"{connection.name} (Analytics Connector)",
                "sqlalchemy_uri": sqlalchemy_uri,
                "expose_in_sqllab": True,
                "allow_ctas": True,
                "allow_cvas": True,
                "allow_dml": True,
                "allow_run_async": True,
                "cache_timeout": 3600,
                "extra": json.dumps({
                "metadata_params": {},
                "engine_params": {
                    "connect_args": {
                        "sslmode": "disable"  # instead of ssl_disabled
                    },
                    "pool_recycle": 3600
                },
                "metadata_cache_timeout": {},
                "schemas_allowed_for_file_upload": []
                })
            }
            
            # Try API endpoint first
            try:
                response = session.post(f"{self.base_url}/api/v1/database/", json=database_data)
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    database_id = result.get('id')
                    logger.info(f"Created Superset database connection with ID: {database_id}")
                    return database_id
                else:
                    logger.warning(f"API creation failed: {response.status_code} - {response.text}")
            except Exception as e:
                logger.warning(f"API creation failed: {e}")
            
            # Fallback to web form submission
            return self._create_database_via_form(database_data)
            
        except Exception as e:
            logger.error(f"Error creating database connection in Superset: {str(e)}")
            return None
    
    def _create_database_via_form(self, database_data: Dict[str, Any]) -> Optional[int]:
        """Fallback method to create database via web form"""
        session = self._authenticate()
        if not session:
            return None
            
        try:
            from bs4 import BeautifulSoup
            # Get the database creation form
            form_response = session.get(f"{self.base_url}/databaseview/add")
            if form_response.status_code != 200:
                logger.error("Could not access database creation form")
                return None
            
            # Extract CSRF token from form
            soup = BeautifulSoup(form_response.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            if csrf_input:
                csrf_token = csrf_input.get('value')
                database_data['csrf_token'] = csrf_token
            
            # Submit form
            form_response = session.post(f"{self.base_url}/databaseview/add", data=database_data)
            
            if form_response.status_code == 200 and "success" in form_response.text.lower():
                logger.info("Successfully created database connection via form")
                return 1  # We can't get the actual ID this way
            else:
                logger.error("Failed to create database via form")
                return None
                
        except Exception as e:
            logger.error(f"Error creating database via form: {str(e)}")
            return None
    
    def _build_sqlalchemy_uri(self, db_type: DatabaseType, credentials: Dict[str, Any]) -> Optional[str]:
        """Build SQLAlchemy URI from database type and credentials"""
        try:
            host = credentials.get('host')
            port = credentials.get('port')
            username = credentials.get('username')
            password = credentials.get('password')
            database_name = credentials.get('database_name')
            
            if db_type == DatabaseType.POSTGRESQL:
                return f"postgresql://{username}:{password}@{host}:{port}/{database_name}"
            
            elif db_type == DatabaseType.MYSQL:
                return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database_name}"
            
            elif db_type == DatabaseType.MONGODB:
                # Check if connection string is provided
                conn_string = credentials.get('connection_string')
                if conn_string:
                    return f"mongodb://{conn_string}"
                else:
                    return f"mongodb://{username}:{password}@{host}:{port}/{database_name}"
            
            elif db_type == DatabaseType.SQLITE:
                return f"sqlite:///{database_name}"
            
            elif db_type == DatabaseType.ORACLE:
                return f"oracle+cx_oracle://{username}:{password}@{host}:{port}/?service_name={database_name}"
            
            elif db_type == DatabaseType.MSSQL:
                return f"mssql+pyodbc://{username}:{password}@{host}:{port}/{database_name}?driver=ODBC+Driver+17+for+SQL+Server"
            
            else:
                logger.error(f"Unsupported database type: {db_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error building SQLAlchemy URI: {str(e)}")
            return None
    
    def test_database_connection(self, database_id: int) -> bool:
        """Test a database connection in Superset"""
        session = self._authenticate()
        if not session:
            return False
        
        try:
            response = session.post(f"{self.base_url}/api/v1/database/{database_id}/test_connection")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error testing database connection: {str(e)}")
            return False
    
    def delete_database_connection(self, database_id: int) -> bool:
        """Delete a database connection from Superset"""
        session = self._authenticate()
        if not session:
            return False
        
        try:
            response = session.delete(f"{self.base_url}/api/v1/database/{database_id}")
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Error deleting database connection: {str(e)}")
            return False
    
    def sync_datasets_for_connection(self, database_id: int, connection_id: int) -> List[int]:
        """Sync datasets (tables) for a database connection"""
        session = self._authenticate()
        if not session:
            return []
        
        try:
            # Get available tables from the database
            response = session.get(f"{self.base_url}/api/v1/database/{database_id}/schemas")
            if response.status_code != 200:
                return []
            
            schemas = response.json().get('result', [])
            dataset_ids = []
            
            for schema in schemas:
                
                print("***********************************************")
                print("Schema:", schema)
                print("***********************************************")
                
                # Get tables for each schema
                tables_response = session.get(
                    f"{self.base_url}/api/v1/database/{database_id}/tables",
                    params={'schema_name': schema}
                )
                
                if tables_response.status_code == 200:
                    tables = tables_response.json().get('result', [])
                    
                    for table in tables:
                        print("***********************************************")
                        print("Table:", table)
                        print("***********************************************")
                        # Create dataset for each table
                        dataset_data = {
                            "database": database_id,
                            "schema": schema,
                            "table_name": table,
                            "owners": []
                        }
                        
                        dataset_response = session.post(
                            f"{self.base_url}/api/v1/dataset/",
                            json=dataset_data
                        )
                        
                        if dataset_response.status_code in [200, 201]:
                            dataset_id = dataset_response.json().get('id')
                            if dataset_id:
                                dataset_ids.append(dataset_id)
                                logger.info(f"Created dataset for table {schema}.{table}")
            
            return dataset_ids
            
        except Exception as e:
            logger.error(f"Error syncing datasets: {str(e)}")
            return []
    
    def create_basic_dashboard(self, connection_name: str, dataset_ids: List[int]) -> Optional[int]:
        """Create a basic dashboard for a connection"""
        session = self._authenticate()
        if not session or not dataset_ids:
            return None
        
        try:
            dashboard_data = {
                "dashboard_title": f"{connection_name} - Analytics Dashboard",
                "slug": f"analytics-{connection_name.lower().replace(' ', '-')}",
                "published": True,
                "json_metadata": json.dumps({
                    "timed_refresh_immune_slices": [],
                    "expanded_slices": {},
                    "refresh_frequency": 300,
                    "default_filters": "{}"
                }),
                "position_json": json.dumps({
                    "DASHBOARD_VERSION_KEY": "v2"
                })
            }
            
            response = session.post(f"{self.base_url}/api/v1/dashboard/", json=dashboard_data)
            
            if response.status_code in [200, 201]:
                dashboard_id = response.json().get('id')
                logger.info(f"Created dashboard with ID: {dashboard_id}")
                return dashboard_id
            else:
                logger.error(f"Failed to create dashboard: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating dashboard: {str(e)}")
            return None
