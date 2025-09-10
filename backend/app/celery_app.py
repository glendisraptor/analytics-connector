from celery import Celery
from .core.config import settings
from celery.schedules import crontab

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


celery_app.conf.beat_schedule = {
    'check-scheduled-jobs': {
        'task': 'app.tasks.scheduler.check_scheduled_etl_jobs',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
}

celery_app.conf.timezone = "Africa/Johannesburg"
celery_app.conf.enable_utc = False  