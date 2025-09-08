# app/celery_app.py
from celery import Celery
from .core.config import settings

celery_app = Celery(
    "analytics_connector",
    broker=settings.CELERY_BROKER_URL,  # e.g. redis://localhost:6379/0
    backend=settings.CELERY_RESULT_BACKEND  # e.g. redis://localhost:6379/1
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)
