from sqlalchemy import create_engine, text

# conn_str = "mysql+pymysql://admin:gKGDw5NVN%7DuY%5DI5@lms-database-dev.cc7jdytilrfh.af-south-1.rds.amazonaws.com:3306/lms_database"
# engine = create_engine(conn_str)

# try:
#     with engine.connect() as conn:
#         result = conn.execute(text("SELECT 1"))  # <-- use text()
#         print("Connection successful, result:", result.scalar())
# except Exception as e:
#     print("Connection failed:", e)

# The revised create_database_connection method
def create_database_connection(self, connection: DatabaseConnection) -> Optional[int]:
    """Create a database connection in Superset, ensuring authentication is handled."""

    # Explicitly authenticate before every call, unless already authenticated.
    # This prevents state loss between separate calls.
    if not self._access_token or not self._csrf_token:
        if not self.authenticate():
            logger.error("Failed to authenticate with Superset.")
            return None

    try:
        credentials = encryption_service.decrypt_credentials(connection.encrypted_credentials)
        sqlalchemy_uri = self._build_sqlalchemy_uri(connection.database_type, credentials)
        
        if not sqlalchemy_uri:
            logger.error(f"Could not build SQLAlchemy URI for {connection.database_type}")
            return None
        
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
                        "ssl_disabled": True
                    },
                    "pool_size": 5,
                    "pool_timeout": 30,
                    "pool_recycle": 3600
                },
                "metadata_cache_timeout": {},
                "schemas_allowed_for_file_upload": []
            })
        }
        
        # Make the API call using the properly configured session object.
        # Note: Do not pass the headers argument here. The session has them.
        response = self.session.post(f"{self.base_url}/api/v1/database/", json=database_data)

        if response.status_code in [200, 201]:
            result = response.json()
            database_id = result.get('id')
            logger.info(f"Created Superset database connection with ID: {database_id}")
            return database_id
        else:
            logger.warning(f"API creation failed: {response.status_code} - {response.text}")
            # Fallback to form submission
            return self._create_database_via_form(database_data)
            
    except Exception as e:
        logger.error(f"Error creating database connection in Superset: {str(e)}")
        return None