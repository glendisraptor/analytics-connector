from sqlalchemy.orm import Session
from ..db.database import SessionLocal
from ..models.connection import DatabaseConnection, ETLJob
from .superset_service import SupersetService
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class AnalyticsAutomation:
    """Automate analytics creation when new data arrives"""
    
    def __init__(self):
        self.superset_service = SupersetService()
    
    def create_analytics_for_new_data(self, connection_id: int, table_names: List[str]) -> Dict[str, Any]:
        """Create basic analytics when new data tables are detected"""
        
        db = SessionLocal()
        try:
            connection = db.query(DatabaseConnection).filter(
                DatabaseConnection.id == connection_id
            ).first()
            
            if not connection:
                return {"error": "Connection not found"}
            
            results = {
                "connection_id": connection_id,
                "connection_name": connection.name,
                "datasets_created": [],
                "charts_created": [],
                "dashboard_created": None
            }
            
            # 1. Create datasets in Superset for each table
            dataset_ids = []
            for table_name in table_names:
                try:
                    # In a real implementation, you'd call Superset API to create datasets
                    dataset_id = self._create_dataset_for_table(connection_id, table_name)
                    if dataset_id:
                        dataset_ids.append(dataset_id)
                        results["datasets_created"].append({
                            "table_name": table_name,
                            "dataset_id": dataset_id
                        })
                except Exception as e:
                    logger.error(f"Failed to create dataset for {table_name}: {e}")
            
            # 2. Create basic charts for interesting tables
            chart_ids = []
            for table_name in table_names:
                if self._is_interesting_table(table_name):
                    chart_id = self._create_basic_chart(table_name, connection_id)
                    if chart_id:
                        chart_ids.append(chart_id)
                        results["charts_created"].append({
                            "table_name": table_name,
                            "chart_id": chart_id,
                            "chart_type": "auto_generated"
                        })
            
            # 3. Create a dashboard if we have charts
            if chart_ids:
                dashboard_id = self._create_overview_dashboard(connection.name, chart_ids)
                results["dashboard_created"] = dashboard_id
            
            logger.info(f"Created analytics for connection {connection_id}: {len(dataset_ids)} datasets, {len(chart_ids)} charts")
            return results
            
        except Exception as e:
            logger.error(f"Error creating analytics automation: {e}")
            return {"error": str(e)}
        finally:
            db.close()
    
    def _create_dataset_for_table(self, connection_id: int, table_name: str) -> int:
        """Create a Superset dataset for a table"""
        # This would integrate with Superset API to create datasets
        # For now, return a mock ID
        return hash(f"{connection_id}_{table_name}") % 10000
    
    def _is_interesting_table(self, table_name: str) -> bool:
        """Determine if a table is worth creating automatic charts for"""
        interesting_patterns = [
            'customer', 'user', 'order', 'sale', 'transaction', 
            'product', 'event', 'log', 'metric', 'analytics'
        ]
        
        table_lower = table_name.lower()
        return any(pattern in table_lower for pattern in interesting_patterns)
    
    def _create_basic_chart(self, table_name: str, connection_id: int) -> int:
        """Create a basic chart for a table"""
        # This would create actual charts in Superset
        # For now, return a mock ID
        return hash(f"chart_{connection_id}_{table_name}") % 10000
    
    def _create_overview_dashboard(self, connection_name: str, chart_ids: List[int]) -> int:
        """Create an overview dashboard with the generated charts"""
        # This would create an actual dashboard in Superset
        # For now, return a mock ID
        return hash(f"dashboard_{connection_name}") % 10000