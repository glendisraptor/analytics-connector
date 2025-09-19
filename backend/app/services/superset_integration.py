import requests
import json
import uuid
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

    # --------------------------
    # Helpers
    # --------------------------

    def _build_chart_params(self, viz_type: str, custom_params: Dict[str, Any]) -> str:
        """
        Build safe params for chart creation with required Superset defaults.
        Prevents frontend crashes like .includes() on undefined.
        """
        base_params = {
            "time_range": "No filter",
            "adhoc_filters": [],
        }
        
        #    if viz_type == "big_number_total":
        #     base_params.update({
        #         "metric": ["sum_amount"],
        #         "adhoc_filters": [],
        #         "time_range": "No filter",
        #         "subheader": "",
        #         "y_axis_format": "SMART_NUMBER"
        #     })
        # el

        if viz_type == "table":
            base_params.update({
                "metrics": ["count"],
                "all_columns": ["id"],
                "adhoc_filters": [],
                "row_limit": 100,
                "time_range": "No filter"
            })


        # merge user config
        base_params.update(custom_params or {})
        return json.dumps(base_params)

    # --------------------------
    # Dataset Creation
    # --------------------------

    def create_superset_dataset(self, connection_id: int, table_name: str, database_id: Optional[int] = None) -> Optional[int]:
        """Create a single Superset dataset for a specific table"""
        logger.info(f"[{datetime.utcnow()}] Creating Superset dataset for table {table_name}, connection {connection_id}")
        
        try:
            session = self.superset_service._authenticate()
            if not session:
                logger.error("Failed to authenticate with Superset")
                return None

            # Get or create database connection if not provided
            if not database_id:
                db = SessionLocal()
                connection = db.query(DatabaseConnection).filter(DatabaseConnection.id == connection_id).first()
                db.close()
                if not connection:
                    logger.error(f"Connection {connection_id} not found")
                    return None
                
                database_id = self._create_or_find_analytics_database_connection(connection)
                if not database_id:
                    logger.error("Failed to create/find analytics database connection")
                    return None

            # Check if dataset already exists
            existing_dataset_id = self._find_dataset_by_table_name(session, table_name, database_id)
            if existing_dataset_id:
                logger.info(f"Dataset for table {table_name} already exists with ID {existing_dataset_id}")
                return existing_dataset_id

            # Create new dataset
            dataset_data = {
                "database": database_id,
                "table_name": table_name,
                "schema": "public",
                "owners": [],
                "is_managed_externally": False,
                "external_url": None
            }


            response = session.post(f"{self.superset_service.base_url}/api/v1/dataset/", json=dataset_data)
            
            if response.status_code in [200, 201]:
                dataset_id = response.json().get("id")
                logger.info(f"Successfully created dataset {dataset_id} for table {table_name}")
                return dataset_id
            else:
                logger.error(f"Failed to create dataset: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating dataset for table {table_name}: {str(e)}")
            return None

    def create_superset_datasets(self, connection_id: int, table_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Create multiple Superset datasets for a connection's analytics tables"""
        logger.info(f"[{datetime.utcnow()}] Creating Superset datasets for connection {connection_id}")
        
        try:
            # Get connection details
            db = SessionLocal()
            connection = db.query(DatabaseConnection).filter(DatabaseConnection.id == connection_id).first()
            db.close()
            if not connection:
                logger.error(f"Connection {connection_id} not found")
                return []

            # Get analytics database connection
            database_id = self._create_or_find_analytics_database_connection(connection)
            if not database_id:
                logger.error("Failed to create/find analytics database connection")
                return []

            # Get table names if not provided
            if not table_names:
                etl_service = ETLService()
                analytics_tables = etl_service.get_analytics_tables(connection_id)
                table_names = [table for table in analytics_tables]

            created_datasets = []
            
            for table_name in table_names:
                dataset_id = self.create_superset_dataset(connection_id, table_name, database_id)
                if dataset_id:
                    self.refresh_dataset_metadata(dataset_id)
                    created_datasets.append({"table_name": table_name, "dataset_id": dataset_id})
                else:
                    print(f"Failed to create dataset for table: {table_name}")

            logger.info(f"Successfully created {len(created_datasets)} datasets for connection {connection_id}")
            return created_datasets

        except Exception as e:
            logger.error(f"Error creating datasets for connection {connection_id}: {str(e)}")
            return []

    def _find_dataset_by_table_name(self, session: requests.Session, table_name: str, database_id: int) -> Optional[int]:
        """Find dataset ID by table name and database ID"""
        try:
            response = session.get(f"{self.superset_service.base_url}/api/v1/dataset/")
            if response.status_code == 200:
                datasets = response.json().get("result", [])
                for dataset in datasets:
                    if (dataset.get("table_name") == table_name and 
                        dataset.get("database", {}).get("id") == database_id):
                        return dataset.get("id")
        except Exception as e:
            logger.error(f"Error finding dataset: {str(e)}")
        return None

    def refresh_dataset_metadata(self, dataset_id: int) -> bool:
        """Refresh metadata for a specific dataset"""
        logger.info(f"[{datetime.utcnow()}] Refreshing metadata for dataset {dataset_id}")
        
        try:
            session = self.superset_service._authenticate()
            if not session:
                return False

            # Trigger metadata refresh
            response = session.put(f"{self.superset_service.base_url}/api/v1/dataset/{dataset_id}/refresh")
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully refreshed metadata for dataset {dataset_id}")
                return True
            else:
                logger.error(f"Failed to refresh dataset metadata: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error refreshing dataset metadata: {str(e)}")
            return False

    def get_dataset_columns(self, dataset_id: int) -> List[Dict[str, Any]]:
        """Get column information for a dataset"""
        logger.info(f"[{datetime.utcnow()}] Getting columns for dataset {dataset_id}")
        
        try:
            session = self.superset_service._authenticate()
            if not session:
                return []

            response = session.get(f"{self.superset_service.base_url}/api/v1/dataset/{dataset_id}")
            
            if response.status_code == 200:
                dataset_data = response.json().get("result", {})
                columns = dataset_data.get("columns", [])
                logger.info(f"Found {len(columns)} columns for dataset {dataset_id}")
                return columns
            else:
                logger.error(f"Failed to get dataset columns: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error getting dataset columns: {str(e)}")
            return []

    # --------------------------
    # Chart Creation
    # --------------------------

    def create_sample_charts(self, connection_id: int, datasets: Optional[List[Dict[str, Any]]] = None) -> List[int]:
        """Create business charts for a connection's datasets, handling duplicates"""
        logger.info(f"[{datetime.utcnow()}] Creating business charts for connection {connection_id}")

        try:
            session = self.superset_service._authenticate()
            if not session:
                return []

            connection_datasets = []
            if datasets and isinstance(datasets, list):
                connection_datasets = [
                    ds for ds in datasets
                    if isinstance(ds, dict) and 'table_name' in ds and 'dataset_id' in ds
                ]
            if not connection_datasets:
                datasets_response = session.get(f"{self.superset_service.base_url}/api/v1/dataset/")
                if datasets_response.status_code == 200:
                    all_datasets = datasets_response.json().get('result', [])
                    table_prefix = f"conn_{connection_id}_"
                    for dataset in all_datasets:
                        if dataset.get('table_name', '').startswith(table_prefix):
                            connection_datasets.append({
                                "table_name": dataset["table_name"],
                                "dataset_id": dataset["id"]
                            })

            if not connection_datasets:
                return []

            created_charts = []

            chart_configs = [
                # {
                #     "table_suffix": "financial_records",
                #     "viz_type": "big_number_total",
                #     "name": f"Total Revenue - Connection {connection_id}",
                #     "params": {
                #         "metric": "sum_amount",
                #         "adhoc_filters": [{
                #             "clause": "WHERE",
                #             "subject": "transaction_type",
                #             "operator": "==",
                #             "comparator": "Income"
                #         }]
                #     }
                # },
                {
                    "table_suffix": "financial_records",
                    "viz_type": "table",
                    "name": f"Transactions Table - Connection {connection_id}",
                    "params": {
                        "all_columns": ["id", "transaction_type", "amount", "created_at"]
                    }
                }
            ]

            for config in chart_configs:
                expected_table_name = f"conn_{connection_id}_{config['table_suffix']}"
                dataset_info = next(
                    (ds for ds in connection_datasets if ds['table_name'] == expected_table_name),
                    None
                )
                if not dataset_info:
                    continue

                chart_id = self._create_or_update_chart(session, config, dataset_info)
                if chart_id:
                    created_charts.append(chart_id)

            return created_charts

        except Exception as e:
            logger.error(f"Error creating charts: {str(e)}")
            return []

    def _create_or_update_chart(self, session: requests.Session,
                                chart_config: Dict[str, Any],
                                dataset_info: Dict[str, Any]) -> Optional[int]:
        """Create or update a chart safely"""
        chart_name = chart_config["name"]

        try:
            existing_chart_id = self._find_chart_by_name(session, chart_name)
            chart_data = {
                "datasource_id": dataset_info['dataset_id'],
                "datasource_type": "table",
                "viz_type": chart_config["viz_type"],
                "slice_name": chart_name,
                "params": self._build_chart_params(chart_config["viz_type"], chart_config.get("params", {})),
            }

            if existing_chart_id:
                response = session.put(
                    f"{self.superset_service.base_url}/api/v1/chart/{existing_chart_id}",
                    json=chart_data
                )
                if response.status_code in [200, 201]:
                    return existing_chart_id
                return existing_chart_id

            response = session.post(
                f"{self.superset_service.base_url}/api/v1/chart/",
                json=chart_data
            )
            if response.status_code in [200, 201]:
                return response.json().get("id")
            return None

        except Exception as e:
            logger.error(f"Error creating/updating chart {chart_name}: {str(e)}")
            return None

    def _find_chart_by_name(self, session: requests.Session, chart_name: str) -> Optional[int]:
        """Find chart ID by name"""
        try:
            response = session.get(f"{self.superset_service.base_url}/api/v1/chart/")
            if response.status_code == 200:
                for chart in response.json().get("result", []):
                    if chart.get("slice_name") == chart_name:
                        return chart.get("id")
        except Exception:
            pass
        return None

    # --------------------------
    # Dashboards
    # --------------------------

    def _assign_charts_to_dashboard(self, session: requests.Session, dashboard_id: int, chart_ids: List[int]) -> bool:
        """Assign charts to a dashboard with valid position_json"""
        try:
            response = session.get(f"{self.superset_service.base_url}/api/v1/dashboard/{dashboard_id}")
            if response.status_code != 200:
                return False

            dashboard_data = response.json().get("result", {})
            current_position_json = json.loads(
                dashboard_data.get("position_json", '{"ROOT_ID": {"children": [], "id": "ROOT_ID", "type": "ROOT"}}')
            )

            row_id = f"ROW_{len(current_position_json.get('ROOT_ID', {}).get('children', [])) + 1}"
            current_position_json[row_id] = {"type": "ROW", "id": row_id, "children": []}

            y_pos = 0
            for chart_id in chart_ids:
                print(f"Assigning chart ID {chart_id} to dashboard {dashboard_id}")
                slice_id = f"CHART_{chart_id}_{y_pos}"
                current_position_json[slice_id] = {
                    "type": "CHART",
                    "id": slice_id,
                    "meta": {
                        "chartId": chart_id,
                        "height": 50,
                        "width": 4,
                    },
                    "children": []
                }
                current_position_json[row_id]["children"].append(slice_id)
                y_pos += 1

            current_position_json["ROOT_ID"]["children"].append(row_id)

            update_data = {"position_json": json.dumps(current_position_json), "published": True}
            update_response = session.put(
                f"{self.superset_service.base_url}/api/v1/dashboard/{dashboard_id}",
                json=update_data
            )
            return update_response.status_code in [200, 201]

        except Exception as e:
            logger.error(f"Error assigning charts: {str(e)}")
            return False

    def _update_dashboard_charts(self, session: requests.Session, dashboard_id: int, chart_ids: List[int]) -> bool:
        """Update dashboard with new charts safely and full metadata"""
        try:
            # Fetch current dashboard
            response = session.get(f"{self.superset_service.base_url}/api/v1/dashboard/{dashboard_id}")
            if response.status_code != 200:
                logger.error(f"Failed to fetch dashboard {dashboard_id}: {response.status_code}")
                return False

            dashboard_data = response.json().get("result", {})

            # Parse existing position_json and json_metadata
            current_position_json = json.loads(
                dashboard_data.get("position_json", '{"ROOT_ID": {"children": [], "id": "ROOT_ID", "type": "ROOT"}}')
            )
            current_json_metadata = json.loads(
                dashboard_data.get("json_metadata", "{}")
            )

            # Ensure required json_metadata keys exist
            current_json_metadata.setdefault("chart_configuration", {})
            current_json_metadata.setdefault("global_chart_configuration", {"scope": {"rootPath": ["ROOT_ID"], "excluded": []}, "chartsInScope": []})
            current_json_metadata.setdefault("map_label_colors", {})
            current_json_metadata.setdefault("color_scheme", "")
            current_json_metadata.setdefault("refresh_frequency", 0)
            current_json_metadata.setdefault("color_scheme_domain", [])
            current_json_metadata.setdefault("expanded_slices", {})
            current_json_metadata.setdefault("label_colors", {})
            current_json_metadata.setdefault("shared_label_colors", [])
            current_json_metadata.setdefault("timed_refresh_immune_slices", [])
            current_json_metadata.setdefault("cross_filters_enabled", True)
            current_json_metadata.setdefault("default_filters", "{}")
            current_json_metadata.setdefault("filter_scopes", {})

            # Get last row or create one
            root_children = current_position_json.get("ROOT_ID", {}).get("children", [])
            if not root_children:
                row_id = f"ROW-{uuid.uuid4().hex[:12]}"
                current_position_json[row_id] = {
                    "type": "ROW",
                    "id": row_id,
                    "children": [],
                    "parents": ["ROOT_ID", "GRID_ID"] if "GRID_ID" in current_position_json else ["ROOT_ID"],
                    "meta": {"background": "BACKGROUND_TRANSPARENT"}
                }
                current_position_json["ROOT_ID"]["children"] = [row_id]
            else:
                row_id = root_children[-1]
                if current_position_json.get(row_id, {}).get("type") != "ROW":
                    row_id = f"ROW-{uuid.uuid4().hex[:12]}"
                    current_position_json[row_id] = {
                        "type": "ROW",
                        "id": row_id,
                        "children": [],
                        "parents": ["ROOT_ID", "GRID_ID"] if "GRID_ID" in current_position_json else ["ROOT_ID"],
                        "meta": {"background": "BACKGROUND_TRANSPARENT"}
                    }
                    current_position_json["ROOT_ID"]["children"].append(row_id)

            # Track position in row
            y_pos = len(current_position_json.get(row_id, {}).get("children", []))

            for chart_id in chart_ids:
                chart_uuid = f"CHART-{uuid.uuid4().hex[:12]}"

                # Fetch chart details for sliceName
                chart_resp = session.get(f"{self.superset_service.base_url}/api/v1/chart/{chart_id}")
                if chart_resp.status_code == 200:
                    slice_name = chart_resp.json().get("result", {}).get("slice_name", f"Chart {chart_id}")
                else:
                    slice_name = f"Chart {chart_id}"

                # Add chart block
                current_position_json[chart_uuid] = {
                    "type": "CHART",
                    "id": chart_uuid,
                    "children": [],
                    "parents": ["ROOT_ID", row_id],
                    "meta": {
                        "chartId": chart_id,
                        "height": 50,
                        "width": 12,
                        "sliceName": slice_name
                    }
                }
                current_position_json[row_id]["children"].append(chart_uuid)

                # Update json_metadata.chart_configuration
                current_json_metadata["chart_configuration"][str(chart_id)] = {
                    "id": chart_id,
                    "crossFilters": {"scope": "global", "chartsInScope": []}
                }

                # Add to global chartsInScope if not present
                if chart_id not in current_json_metadata["global_chart_configuration"]["chartsInScope"]:
                    current_json_metadata["global_chart_configuration"]["chartsInScope"].append(chart_id)

                y_pos += 1

            # Final update payload
            update_data = {
                "position_json": json.dumps(current_position_json),
                "json_metadata": json.dumps(current_json_metadata),
                "published": True
            }

            update_response = session.put(
                f"{self.superset_service.base_url}/api/v1/dashboard/{dashboard_id}",
                json=update_data
            )
            if update_response.status_code in [200, 201]:
                logger.info(f"Updated dashboard {dashboard_id} with {len(chart_ids)} charts")
                return True
            else:
                logger.error(f"Failed to update dashboard {dashboard_id}: {update_response.status_code} - {update_response.text}")
                return False

        except Exception as e:
            logger.error(f"Error updating dashboard: {str(e)}")
            return False
        
    def _create_or_find_analytics_database_connection(self, connection: DatabaseConnection) -> Optional[int]:
        """Create or find the analytics database connection in Superset"""
        logger.info(f"[{datetime.utcnow()}] Creating or finding analytics database connection for {connection.name}")

        try:
            analytics_db_name = f"{connection.name} - Analytics"
            analytics_uri = settings.ANALYTICS_DATABASE_URL

            database_data = {
                "database_name": analytics_db_name,
                "sqlalchemy_uri": analytics_uri,
                "expose_in_sqllab": True,
                "allow_ctas": True,
                "allow_cvas": True,
                "allow_dml": False,
                "allow_run_async": True,
                "cache_timeout": 3600,
                "extra": json.dumps({
                    "metadata_params": {},
                    "engine_params": {
                        "connect_args": {"sslmode": "disable"},
                        "pool_recycle": 3600
                    },
                    "metadata_cache_timeout": {},
                    "schemas_allowed_for_file_upload": []
                })
            }

            session = self.superset_service._authenticate()
            if not session:
                logger.error("Failed to authenticate with Superset")
                return None

            existing_db_id = self._find_existing_database(session, analytics_db_name)
            if existing_db_id:
                return existing_db_id

            response = session.post(f"{self.superset_service.base_url}/api/v1/database/", json=database_data)
            if response.status_code in [200, 201]:
                return response.json().get("id")
            else:
                logger.error(f"Failed to create analytics DB: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating analytics DB: {str(e)}")
            return None

    def _find_existing_database(self, session: requests.Session, database_name: str) -> Optional[int]:
        """Find existing database connection by name"""
        try:
            response = session.get(f"{self.superset_service.base_url}/api/v1/database/")
            if response.status_code == 200:
                for db in response.json().get("result", []):
                    if db.get("database_name") == database_name:
                        return db.get("id")
        except Exception as e:
            logger.error(f"Error finding existing database: {str(e)}")
        return None

    def _link_charts_to_dashboard(self, session: requests.Session, dashboard_id: int, chart_ids: List[int]) -> bool:
        """Alternative method to link charts to dashboard (alias for assign)"""
        logger.info(f"[{datetime.utcnow()}] Linking charts to dashboard using alternative method")
        return self._assign_charts_to_dashboard(session, dashboard_id, chart_ids)

    def _link_charts_directly(self, session: requests.Session, dashboard_id: int, chart_ids: List[int]) -> bool:
        """Fallback method for direct chart linking (simplified assign)"""
        logger.info(f"[{datetime.utcnow()}] Linking charts directly as fallback")
        # Simplified version: just update metadata with chart list if supported
        try:
            response = session.get(f"{self.superset_service.base_url}/api/v1/dashboard/{dashboard_id}")
            if response.status_code != 200:
                return False
            
            dashboard_data = response.json().get('result', {})
            json_metadata = json.loads(dashboard_data.get('json_metadata', '{}'))
            json_metadata['native_filter_configuration'] = []  # Ensure no conflicts
            
            update_data = {
                "json_metadata": json.dumps(json_metadata),
                "published": True
            }
            
            # Note: Direct chart linking via metadata may not be standard; fallback to positions
            return self._assign_charts_to_dashboard(session, dashboard_id, chart_ids)
            
        except Exception as e:
            logger.error(f"[{datetime.utcnow()}] Error in direct linking: {str(e)}")
            return False

    def delete_connection_resources(self, connection_id: int) -> bool:
        """Remove all Superset resources for a connection"""
        logger.info(f"[{datetime.utcnow()}] Deleting all resources for connection {connection_id}")
        
        try:
            # Delete dashboards
            deleted_dashboards = self._delete_connection_dashboards(connection_id)
            logger.info(f"[{datetime.utcnow()}] Deleted {len(deleted_dashboards)} dashboards")
            
            # Delete charts
            deleted_charts = self._delete_connection_charts(connection_id)
            logger.info(f"[{datetime.utcnow()}] Deleted {len(deleted_charts)} charts")
            
            # Delete datasets
            deleted_datasets = self._delete_connection_datasets(connection_id)
            logger.info(f"[{datetime.utcnow()}] Deleted {len(deleted_datasets)} datasets")
            
            # Optionally delete database if no other connections use it
            # For now, skip to avoid affecting shared analytics DB
            
            success = len(deleted_dashboards) + len(deleted_charts) + len(deleted_datasets) > 0
            logger.info(f"[{datetime.utcnow()}] Resource deletion completed successfully: {success}")
            return success
            
        except Exception as e:
            logger.error(f"[{datetime.utcnow()}] Error deleting connection resources: {str(e)}")
            import traceback
            logger.error(f"[{datetime.utcnow()}] Traceback: {traceback.format_exc()}")
            return False

    def _delete_connection_charts(self, connection_id: int) -> List[int]:
        """Delete charts associated with a connection"""
        logger.info(f"[{datetime.utcnow()}] Deleting charts for connection {connection_id}")
        
        deleted = []
        try:
            session = self.superset_service._authenticate()
            if not session:
                return deleted
            
            response = session.get(f"{self.superset_service.base_url}/api/v1/chart/")
            if response.status_code != 200:
                return deleted
            
            charts = response.json().get('result', [])
            for chart in charts:
                chart_name = chart.get('slice_name', '')
                if f"Connection {connection_id}" in chart_name:
                    chart_id = chart.get('id')
                    del_response = session.delete(f"{self.superset_service.base_url}/api/v1/chart/{chart_id}")
                    if del_response.status_code in [200, 204]:
                        deleted.append(chart_id)
                        logger.info(f"[{datetime.utcnow()}] Deleted chart {chart_id}")
                    else:
                        logger.warning(f"[{datetime.utcnow()}] Failed to delete chart {chart_id}: {del_response.status_code}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"[{datetime.utcnow()}] Error deleting charts: {str(e)}")
            return deleted

    def _delete_connection_datasets(self, connection_id: int) -> List[int]:
        """Delete datasets associated with a connection"""
        logger.info(f"[{datetime.utcnow()}] Deleting datasets for connection {connection_id}")
        
        deleted = []
        try:
            session = self.superset_service._authenticate()
            if not session:
                return deleted
            
            # Get analytics tables to match
            db = SessionLocal()
            connection = db.query(DatabaseConnection).filter(DatabaseConnection.id == connection_id).first()
            db.close()
            if not connection:
                return deleted
            
            etl_service = ETLService()
            analytics_tables = etl_service.get_analytics_tables(connection_id)
            # analytics_tables should already contain the full table names
            table_names = analytics_tables
            
            response = session.get(f"{self.superset_service.base_url}/api/v1/dataset/")
            if response.status_code != 200:
                return deleted
            
            datasets = response.json().get('result', [])
            for dataset in datasets:
                table_name = dataset.get('table_name', '')
                if table_name in table_names:
                    dataset_id = dataset.get('id')
                    del_response = session.delete(f"{self.superset_service.base_url}/api/v1/dataset/{dataset_id}")
                    if del_response.status_code in [200, 204]:
                        deleted.append(dataset_id)
                        logger.info(f"[{datetime.utcnow()}] Deleted dataset {dataset_id} for table {table_name}")
                    else:
                        logger.warning(f"[{datetime.utcnow()}] Failed to delete dataset {dataset_id}: {del_response.status_code}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"[{datetime.utcnow()}] Error deleting datasets: {str(e)}")
            return deleted

    def _delete_connection_dashboards(self, connection_id: int) -> List[int]:
        """Delete dashboards associated with a connection"""
        logger.info(f"[{datetime.utcnow()}] Deleting dashboards for connection {connection_id}")
        
        deleted = []
        try:
            session = self.superset_service._authenticate()
            if not session:
                return deleted
            
            db = SessionLocal()
            connection = db.query(DatabaseConnection).filter(DatabaseConnection.id == connection_id).first()
            db.close()
            if not connection:
                return deleted
            
            dashboard_title_prefix = f"{connection.name} -"
            
            response = session.get(f"{self.superset_service.base_url}/api/v1/dashboard/")
            if response.status_code != 200:
                return deleted
            
            dashboards = response.json().get('result', [])
            for dashboard in dashboards:
                dashboard_title = dashboard.get('dashboard_title', '')
                if dashboard_title.startswith(dashboard_title_prefix):
                    dashboard_id = dashboard.get('id')
                    del_response = session.delete(f"{self.superset_service.base_url}/api/v1/dashboard/{dashboard_id}")
                    if del_response.status_code in [200, 204]:
                        deleted.append(dashboard_id)
                        logger.info(f"[{datetime.utcnow()}] Deleted dashboard {dashboard_id}: {dashboard_title}")
                    else:
                        logger.warning(f"[{datetime.utcnow()}] Failed to delete dashboard {dashboard_id}: {del_response.status_code}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"[{datetime.utcnow()}] Error deleting dashboards: {str(e)}")
            return deleted

    def test_superset_connection(self) -> Dict[str, Any]:
        """Test connection to Superset - returns status dictionary"""
        logger.info(f"[{datetime.utcnow()}] Testing Superset connection")
        
        try:
            session = self.superset_service._authenticate()
            if not session:
                logger.error(f"[{datetime.utcnow()}] Failed to authenticate with Superset")
                return {
                    "status": "failed",
                    "error": "Authentication failed",
                    "connected": False
                }
            
            response = session.get(f"{self.superset_service.base_url}/api/v1/database/")
            success = response.status_code == 200
            
            if success:
                logger.info(f"[{datetime.utcnow()}] Superset connection test: successful")
                return {
                    "status": "connected",
                    "connected": True,
                    "message": "Superset connection successful"
                }
            else:
                logger.error(f"[{datetime.utcnow()}] Superset connection test failed: {response.status_code}")
                return {
                    "status": "failed",
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "connected": False
                }
                
        except Exception as e:
            logger.error(f"[{datetime.utcnow()}] Error testing Superset connection: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "connected": False
            }

    def get_superset_connection_status(self, connection_id: int) -> Dict[str, Any]:
        """Check status of Superset resources for a connection"""
        logger.info(f"[{datetime.utcnow()}] Checking Superset status for connection {connection_id}")
        
        status = {
            "connection_id": connection_id,
            "charts_count": 0,
            "datasets_count": 0,
            "dashboards_count": 0,
            "database_exists": False
        }
        
        try:
            session = self.superset_service._authenticate()
            if not session:
                status["error"] = "Authentication failed"
                return status
            
            # Check charts
            chart_response = session.get(f"{self.superset_service.base_url}/api/v1/chart/")
            if chart_response.status_code == 200:
                charts = chart_response.json().get('result', [])
                status["charts_count"] = sum(1 for chart in charts if f"Connection {connection_id}" in chart.get('slice_name', ''))
            
            # Check datasets
            dataset_response = session.get(f"{self.superset_service.base_url}/api/v1/dataset/")
            if dataset_response.status_code == 200:
                datasets = dataset_response.json().get('result', [])
                status["datasets_count"] = sum(1 for dataset in datasets if dataset.get('table_name', '').startswith(f"conn_{connection_id}_"))
            
            # Check dashboards
            dashboard_response = session.get(f"{self.superset_service.base_url}/api/v1/dashboard/")
            if dashboard_response.status_code == 200:
                dashboards = dashboard_response.json().get('result', [])
                db = SessionLocal()
                connection = db.query(DatabaseConnection).filter(DatabaseConnection.id == connection_id).first()
                db.close()
                if connection:
                    prefix = f"{connection.name} -"
                    status["dashboards_count"] = sum(1 for dashboard in dashboards if dashboard.get('dashboard_title', '').startswith(prefix))
            
            # Check database (analytics)
            db = SessionLocal()
            connection = db.query(DatabaseConnection).filter(DatabaseConnection.id == connection_id).first()
            db.close()
            if connection:
                analytics_db_name = f"{connection.name} - Analytics"
                db_response = session.get(f"{self.superset_service.base_url}/api/v1/database/")
                if db_response.status_code == 200:
                    databases = db_response.json().get('result', [])
                    status["database_exists"] = any(db.get('database_name') == analytics_db_name for db in databases)
            
            logger.info(f"[{datetime.utcnow()}] Superset status for {connection_id}: {status}")
            return status
            
        except Exception as e:
            logger.error(f"[{datetime.utcnow()}] Error getting Superset status: {str(e)}")
            status["error"] = str(e)
            return status

    def create_dashboard_with_charts(self, connection: DatabaseConnection, chart_ids: List[int]) -> Optional[int]:
        """Create a dashboard and add charts to it with full Superset metadata"""
        logger.info(f"[{datetime.utcnow()}] Creating dashboard for connection {connection.name}")
        
        try:
            session = self.superset_service._authenticate()
            if not session:
                return None
            
            dashboard_title = f"{connection.name} - Analytics Dashboard"

            # ---------------------------
            # Build json_metadata
            # ---------------------------
            chart_config = {
                str(chart_id): {
                    "id": chart_id,
                    "crossFilters": {
                        "scope": "global",
                        "chartsInScope": []
                    }
                } for chart_id in chart_ids
            }

            global_chart_config = {
                "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
                "chartsInScope": chart_ids
            }

            json_metadata = {
                "chart_configuration": chart_config,
                "global_chart_configuration": global_chart_config,
                "map_label_colors": {},
                "color_scheme": "",
                "positions": {},  # Superset will expect this inside position_json, not here
                "refresh_frequency": 0,
                "color_scheme_domain": [],
                "expanded_slices": {},
                "label_colors": {},
                "shared_label_colors": [],
                "timed_refresh_immune_slices": [],
                "cross_filters_enabled": True,
                "default_filters": "{}",
                "filter_scopes": {}
            }

            # ---------------------------
            # Build position_json
            # ---------------------------
            position_json = {
                "DASHBOARD_VERSION_KEY": "v2",
                "ROOT_ID": {
                    "type": "ROOT",
                    "id": "ROOT_ID",
                    "children": ["GRID_ID"]
                },
                "GRID_ID": {
                    "type": "GRID",
                    "id": "GRID_ID",
                    "children": [],
                    "parents": ["ROOT_ID"]
                },
                "HEADER_ID": {
                    "type": "HEADER",
                    "id": "HEADER_ID",
                    "meta": {"text": dashboard_title}
                }
            }

            # Add rows & chart positions dynamically
            for idx, chart_id in enumerate(chart_ids, start=1):
                row_id = f"ROW-{uuid.uuid4().hex[:12]}"
                chart_uuid = f"CHART-{uuid.uuid4().hex[:12]}"

                # Row container
                position_json[row_id] = {
                    "type": "ROW",
                    "id": row_id,
                    "children": [chart_uuid],
                    "parents": ["ROOT_ID", "GRID_ID"],
                    "meta": {"background": "BACKGROUND_TRANSPARENT"}
                }

                # Chart block
                position_json[chart_uuid] = {
                    "type": "CHART",
                    "id": chart_uuid,
                    "children": [],
                    "parents": ["ROOT_ID", "GRID_ID", row_id],
                    "meta": {
                        "width": 12,  # full width per row (adjust as needed)
                        "height": 50,
                        "chartId": chart_id,
                        "sliceName": f"Chart {chart_id}"
                    }
                }

                # Attach row to grid
                position_json["GRID_ID"]["children"].append(row_id)

            # ---------------------------
            # Final payload
            # ---------------------------
            dashboard_data = {
                "dashboard_title": dashboard_title,
                "slug": f"connection-{connection.id}-analytics",
                "published": True,
                "json_metadata": json.dumps(json_metadata),
                "position_json": json.dumps(position_json)
            }

            # API call
            response = session.post(
                f"{self.superset_service.base_url}/api/v1/dashboard/",
                json=dashboard_data
            )
            
            if response.status_code in [200, 201]:
                dashboard_id = response.json().get("id")
                logger.info(f"Created dashboard {dashboard_id}: {dashboard_title}")
                
                # Assign charts to dashboard
                if chart_ids and self._assign_charts_to_dashboard(session, dashboard_id, chart_ids):
                    logger.info(f"Successfully assigned {len(chart_ids)} charts to dashboard {dashboard_id}")
                    return dashboard_id
                else:
                    logger.warning(f"Dashboard created but failed to assign charts")
                    return dashboard_id
            else:
                logger.error(f"Failed to create dashboard: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating dashboard: {str(e)}")
            return None

    def get_connection_superset_resources(self, connection_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """Get inventory of Superset resources for a connection"""
        logger.info(f"[{datetime.utcnow()}] Getting resource inventory for connection {connection_id}")
        
        resources = {
            "charts": [],
            "datasets": [],
            "dashboards": []
        }
        
        try:
            session = self.superset_service._authenticate()
            if not session:
                return resources
            
            # Get charts
            chart_response = session.get(f"{self.superset_service.base_url}/api/v1/chart/")
            if chart_response.status_code == 200:
                charts = chart_response.json().get('result', [])
                resources["charts"] = [chart for chart in charts if f"Connection {connection_id}" in chart.get('slice_name', '')]
            
            # Get datasets
            dataset_response = session.get(f"{self.superset_service.base_url}/api/v1/dataset/")
            if dataset_response.status_code == 200:
                datasets = dataset_response.json().get('result', [])
                resources["datasets"] = [ds for ds in datasets if ds.get('table_name', '').startswith(f"conn_{connection_id}_")]
            
            # Get dashboards
            dashboard_response = session.get(f"{self.superset_service.base_url}/api/v1/dashboard/")
            if dashboard_response.status_code == 200:
                dashboards = dashboard_response.json().get('result', [])
                db = SessionLocal()
                connection = db.query(DatabaseConnection).filter(DatabaseConnection.id == connection_id).first()
                db.close()
                if connection:
                    prefix = f"{connection.name} -"
                    resources["dashboards"] = [db for db in dashboards if db.get('dashboard_title', '').startswith(prefix)]
            
            logger.info(f"[{datetime.utcnow()}] Resource inventory: {dict((k, len(v)) for k, v in resources.items())}")
            return resources
            
        except Exception as e:
            logger.error(f"[{datetime.utcnow()}] Error getting resources: {str(e)}")
            return resources