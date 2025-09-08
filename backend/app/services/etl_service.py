import pandas as pd
from sqlalchemy import create_engine, text
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
from ..core.config import settings
from ..utils.encryption import encryption_service
from ..models.connection import DatabaseConnection, DatabaseType
from .database_service import DatabaseService

logger = logging.getLogger(__name__)

class ETLService:
    """Service for handling ETL operations"""
    
    def __init__(self):
        self.db_service = DatabaseService()
        self.analytics_engine = create_engine(settings.ANALYTICS_DATABASE_URL)
    
    def run_etl(self, connection_id: int, job_type: str = "full_sync") -> int:
        """Run ETL process for a database connection"""
        from ..db.database import SessionLocal
        
        db = SessionLocal()
        try:
            # Get connection details
            connection = db.query(DatabaseConnection)\
                .filter(DatabaseConnection.id == connection_id)\
                .first()
            
            if not connection:
                raise ValueError(f"Connection {connection_id} not found")
            
            # Decrypt credentials
            credentials = encryption_service.decrypt_credentials(
                connection.encrypted_credentials
            )
            
            # Get list of tables to process
            tables = self.db_service.get_table_list(
                connection.database_type, 
                credentials
            )
            
            total_records = 0
            
            for table_name in tables:
                try:
                    # Extract data
                    logger.info(f"Processing table: {table_name}")
                    
                    if job_type == "full_sync":
                        df = self.db_service.extract_data(
                            connection.database_type,
                            credentials,
                            table_name
                        )
                    else:
                        # For incremental sync, limit to recent data
                        df = self.db_service.extract_data(
                            connection.database_type,
                            credentials,
                            table_name,
                            limit=1000
                        )
                    
                    if df.empty:
                        logger.info(f"No data found in table: {table_name}")
                        continue
                    
                    # Transform data
                    transformed_df = self.transform_data(df, connection_id, table_name)
                    
                    # Load data to analytics database
                    self.load_data(transformed_df, connection_id, table_name)
                    
                    total_records += len(transformed_df)
                    logger.info(f"Processed {len(transformed_df)} records from {table_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to process table {table_name}: {str(e)}")
                    # Continue with other tables
                    continue
            
            # Update connection sync timestamp
            connection.last_sync = datetime.utcnow()
            db.commit()
            
            return total_records
            
        finally:
            db.close()
    
    def transform_data(self, df: pd.DataFrame, connection_id: int, table_name: str) -> pd.DataFrame:
        """Apply transformations to the data"""
        
        # Add metadata columns
        df['_source_connection_id'] = connection_id
        df['_source_table'] = table_name
        df['_extracted_at'] = datetime.utcnow()
        
        # Handle data type conversions
        df = self._standardize_data_types(df)
        
        # Clean data
        df = self._clean_data(df)
        
        return df
    
    def _standardize_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize data types for consistency"""
        
        for col in df.columns:
            # Convert object columns that might be dates
            if df[col].dtype == 'object':
                # Try to convert to datetime if it looks like a date
                if df[col].astype(str).str.match(r'\d{4}-\d{2}-\d{2}').any():
                    try:
                        df[col] = pd.to_datetime(df[col], errors='ignore')
                    except:
                        pass
            
            # Handle numeric columns
            elif df[col].dtype == 'int64':
                # Convert large integers to avoid overflow issues
                if df[col].max() > 2147483647:  # Max 32-bit int
                    df[col] = df[col].astype('int64')
                else:
                    df[col] = df[col].astype('int32')
        
        return df
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and prepare data"""
        
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Handle infinite values
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        df[numeric_columns] = df[numeric_columns].replace([np.inf, -np.inf], np.nan)
        
        # Trim whitespace from string columns
        string_columns = df.select_dtypes(include=['object']).columns
        for col in string_columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()
                df[col] = df[col].replace('nan', np.nan)  # Convert 'nan' strings back to NaN
        
        return df
    
    def load_data(self, df: pd.DataFrame, connection_id: int, table_name: str):
        """Load data into analytics database"""
        
        # Create table name for analytics database
        analytics_table_name = f"conn_{connection_id}_{table_name}"
        
        try:
            # Load data to analytics database
            df.to_sql(
                analytics_table_name,
                self.analytics_engine,
                if_exists='replace',  # For full sync, replace data
                index=False,
                method='multi'
            )
            
            logger.info(f"Successfully loaded {len(df)} records to {analytics_table_name}")
            
        except Exception as e:
            logger.error(f"Failed to load data to {analytics_table_name}: {str(e)}")
            raise
    
    def get_analytics_tables(self, connection_id: int) -> List[str]:
        """Get list of analytics tables for a connection"""
        try:
            query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE :pattern
            """)
            
            with self.analytics_engine.connect() as conn:
                result = conn.execute(query, {"pattern": f"conn_{connection_id}_%"})
                tables = [row[0] for row in result]
            
            return tables
            
        except Exception as e:
            logger.error(f"Failed to get analytics tables for connection {connection_id}: {str(e)}")
            return []
