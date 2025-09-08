import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import pymongo
from typing import Dict, Any, List, Optional
import logging
from ..models.connection import DatabaseType
from ..core.config import settings

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for handling database connections and operations"""
    
    def __init__(self):
        self.supported_databases = {
            DatabaseType.POSTGRESQL: self._connect_postgresql,
            DatabaseType.MYSQL: self._connect_mysql,
            DatabaseType.MONGODB: self._connect_mongodb,
            DatabaseType.SQLITE: self._connect_sqlite,
        }
    
    def test_connection(self, db_type: DatabaseType, credentials: Dict[str, Any]) -> bool:
        """Test database connection"""
        try:
            if db_type not in self.supported_databases:
                logger.error(f"Unsupported database type: {db_type}")
                return False
            
            connection_func = self.supported_databases[db_type]
            connection = connection_func(credentials)
            
            if db_type == DatabaseType.MONGODB:
                # Test MongoDB connection
                connection.admin.command('ping')
                connection.close()
            else:
                # Test SQL database connection
                with connection.connect() as conn:
                    conn.execute(text("SELECT 1"))
                connection.dispose()
            
            logger.info(f"Successfully tested {db_type} connection")
            return True
            
        except Exception as e:
            logger.error(f"Connection test failed for {db_type}: {str(e)}")
            return False
    
    def get_table_list(self, db_type: DatabaseType, credentials: Dict[str, Any]) -> List[str]:
        """Get list of tables/collections from database"""
        try:
            if db_type == DatabaseType.MONGODB:
                client = self._connect_mongodb(credentials)
                database = client[credentials['database_name']]
                tables = database.list_collection_names()
                client.close()
                return tables
            else:
                engine = self.supported_databases[db_type](credentials)
                
                if db_type == DatabaseType.POSTGRESQL:
                    query = """
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                    """
                elif db_type == DatabaseType.MYSQL:
                    query = "SHOW TABLES"
                elif db_type == DatabaseType.SQLITE:
                    query = "SELECT name FROM sqlite_master WHERE type='table'"
                else:
                    raise ValueError(f"Unsupported database type: {db_type}")
                
                with engine.connect() as conn:
                    result = conn.execute(text(query))
                    tables = [row[0] for row in result]
                
                engine.dispose()
                return tables
                
        except Exception as e:
            logger.error(f"Failed to get table list for {db_type}: {str(e)}")
            return []
    
    def extract_data(self, db_type: DatabaseType, credentials: Dict[str, Any], 
                    table_name: str, limit: Optional[int] = None) -> pd.DataFrame:
        """Extract data from database table"""
        try:
            if db_type == DatabaseType.MONGODB:
                return self._extract_mongodb_data(credentials, table_name, limit)
            else:
                return self._extract_sql_data(db_type, credentials, table_name, limit)
                
        except Exception as e:
            logger.error(f"Failed to extract data from {table_name}: {str(e)}")
            raise
    
    def _connect_postgresql(self, credentials: Dict[str, Any]):
        """Create PostgreSQL connection"""
        connection_string = (
            f"postgresql://{credentials['username']}:{credentials['password']}"
            f"@{credentials['host']}:{credentials['port']}/{credentials['database_name']}"
        )
        return create_engine(connection_string)
    
    def _connect_mysql(self, credentials: Dict[str, Any]):
        """Create MySQL connection"""
        connection_string = (
            f"mysql+pymysql://{credentials['username']}:{credentials['password']}"
            f"@{credentials['host']}:{credentials['port']}/{credentials['database_name']}"
        )
        return create_engine(connection_string)
    
    def _connect_sqlite(self, credentials: Dict[str, Any]):
        """Create SQLite connection"""
        return create_engine(f"sqlite:///{credentials['database_name']}")
    
    def _connect_mongodb(self, credentials: Dict[str, Any]):
        """Create MongoDB connection"""
        if 'connection_string' in credentials:
            return pymongo.MongoClient(credentials['connection_string'])
        else:
            return pymongo.MongoClient(
                host=credentials['host'],
                port=credentials['port'],
                username=credentials.get('username'),
                password=credentials.get('password')
            )
    
    def _extract_sql_data(self, db_type: DatabaseType, credentials: Dict[str, Any], 
                         table_name: str, limit: Optional[int] = None) -> pd.DataFrame:
        """Extract data from SQL database"""
        engine = self.supported_databases[db_type](credentials)
        
        query = f"SELECT * FROM {table_name}"
        if limit:
            if db_type == DatabaseType.POSTGRESQL:
                query += f" LIMIT {limit}"
            elif db_type == DatabaseType.MYSQL:
                query += f" LIMIT {limit}"
            elif db_type == DatabaseType.SQLITE:
                query += f" LIMIT {limit}"
        
        try:
            df = pd.read_sql(query, engine)
            engine.dispose()
            return df
        except Exception as e:
            engine.dispose()
            raise
    
    def _extract_mongodb_data(self, credentials: Dict[str, Any], 
                            collection_name: str, limit: Optional[int] = None) -> pd.DataFrame:
        """Extract data from MongoDB collection"""
        client = self._connect_mongodb(credentials)
        database = client[credentials['database_name']]
        collection = database[collection_name]
        
        try:
            cursor = collection.find()
            if limit:
                cursor = cursor.limit(limit)
            
            data = list(cursor)
            client.close()
            
            if not data:
                return pd.DataFrame()
            
            # Convert MongoDB documents to DataFrame
            df = pd.json_normalize(data)
            return df
            
        except Exception as e:
            client.close()
            raise