from sqlalchemy.orm import Session
from ..db.database import SessionLocal
from ..models.connection import DatabaseConnection
from .superset_service import SupersetService
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class SupersetIntegration:
    """High-level service for managing Superset integration"""
    
    def __init__(self):
        self.superset_service = SupersetService()
    
    def sync_connection_to_superset(self, connection_id: int) -> bool:
        """Sync a database connection to Superset"""
        db = SessionLocal()
        try:
            # Get the connection
            connection = db.query(DatabaseConnection).filter(
                DatabaseConnection.id == connection_id,
                DatabaseConnection.is_active == True
            ).first()
            
            if not connection:
                logger.error(f"Connection {connection_id} not found or inactive")
                return False
            
            if connection.status != 'connected':
                logger.warning(f"Connection {connection_id} is not in connected state")
                return False
            
            # Create database connection in Superset
            superset_db_id = self.superset_service.create_database_connection(connection)
            
            if superset_db_id:
                # Store the Superset database ID for future reference
                # You might want to add a superset_database_id field to your DatabaseConnection model
                logger.info(f"Successfully synced connection {connection_id} to Superset (DB ID: {superset_db_id})")
                
                # Optionally sync datasets immediately
                dataset_ids = self.superset_service.sync_datasets_for_connection(superset_db_id, connection_id)
                
                # Create a basic dashboard
                if dataset_ids:
                    dashboard_id = self.superset_service.create_basic_dashboard(connection.name, dataset_ids)
                    if dashboard_id:
                        logger.info(f"Created dashboard {dashboard_id} for connection {connection_id}")
                
                return True
            else:
                logger.error(f"Failed to create Superset database for connection {connection_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error syncing connection to Superset: {str(e)}")
            return False
        finally:
            db.close()
    
    def sync_all_connections(self) -> Dict[str, Any]:
        """Sync all active, connected database connections to Superset"""
        db = SessionLocal()
        results = {
            'synced': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }
        
        try:
            connections = db.query(DatabaseConnection).filter(
                DatabaseConnection.is_active == True,
                DatabaseConnection.status == 'connected'
            ).all()
            
            for connection in connections:
                try:
                    success = self.sync_connection_to_superset(connection.id)
                    if success:
                        results['synced'] += 1
                        results['details'].append({
                            'connection_id': connection.id,
                            'name': connection.name,
                            'status': 'synced'
                        })
                    else:
                        results['failed'] += 1
                        results['details'].append({
                            'connection_id': connection.id,
                            'name': connection.name,
                            'status': 'failed'
                        })
                except Exception as e:
                    results['failed'] += 1
                    results['details'].append({
                        'connection_id': connection.id,
                        'name': connection.name,
                        'status': 'error',
                        'error': str(e)
                    })
            
            logger.info(f"Sync completed: {results['synced']} synced, {results['failed']} failed")
            return results
            
        except Exception as e:
            logger.error(f"Error during bulk sync: {str(e)}")
            results['details'].append({'error': str(e)})
            return results
        finally:
            db.close()