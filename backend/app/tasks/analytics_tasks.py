# app/tasks/analytics_tasks.py
from typing import List
from ..services.superset_integration import SupersetIntegration
from ..services.analytics_automation import AnalyticsAutomation
from ..celery_app import celery_app  # Use the main Celery instance

@celery_app.task(name="analytics.sync_connection_to_superset")
def sync_connection_to_superset_task(connection_id: int):
    """Celery task to sync connection to Superset"""
    superset_integration = SupersetIntegration()
    return superset_integration.sync_connection_to_superset(connection_id)

@celery_app.task(name="analytics.create_analytics_for_connection")
def create_analytics_for_connection_task(connection_id: int, table_names: List[str]):
    """Celery task to create analytics for new data"""
    analytics_automation = AnalyticsAutomation()
    return analytics_automation.create_analytics_for_new_data(connection_id, table_names)
