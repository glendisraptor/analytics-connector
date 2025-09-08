# app/celery_app.py
from celery import Celery
from .core.config import settings

celery_app = Celery(
    "analytics_connector",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Optional: auto-discover tasks in the tasks/ folder
celery_app.autodiscover_tasks(["app.tasks"])

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)
