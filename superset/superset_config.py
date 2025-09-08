import os
from celery.schedules import crontab
import logging

# Superset logging level
LOG_LEVEL = "DEBUG"

# Make Flask / Werkzeug more verbose
logging.getLogger("flask_appbuilder").setLevel(logging.DEBUG)
logging.getLogger("werkzeug").setLevel(logging.DEBUG)

# Optional: SQLAlchemy debug (will log SQL queries)
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)


# Basic configuration
SECRET_KEY = os.environ.get('SUPERSET_SECRET_KEY', 'your-superset-secret-key')
# SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:admin@postgres:5432/analytics_data'
SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:admin@postgres:5432/analytics_data'


# postgresql+psycopg2://postgres:mysecretpassword@postgres:5432/superset

# Security
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = None

# Feature flags
FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
    "DASHBOARD_CROSS_FILTERS": True,
    "DASHBOARD_NATIVE_FILTERS": True,
}

# Cache configuration
CACHE_CONFIG = {
    'CACHE_TYPE': 'RedisCache',
    'CACHE_DEFAULT_TIMEOUT': 300,
    'CACHE_KEY_PREFIX': 'superset_',
    'CACHE_REDIS_HOST': 'redis',
    'CACHE_REDIS_PORT': 6379,
    'CACHE_REDIS_DB': 0,
}

# Async queries via Celery
class CeleryConfig:
    BROKER_URL = 'redis://redis:6379/0'
    CELERY_IMPORTS = ('superset.sql_lab', )
    CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
    CELERY_BROKER_URL = 'redis://redis:6379/0'
    CELERYD_LOG_LEVEL = 'DEBUG'
    CELERYD_PREFETCH_MULTIPLIER = 1
    CELERY_ACKS_LATE = True
    CELERY_ANNOTATIONS = {
        'sql_lab.get_sql_results': {
            'rate_limit': '100/s',
        },
        'email_reports.send': {
            'rate_limit': '1/s',
            'time_limit': 120,
            'soft_time_limit': 150,
            'ignore_result': True,
        },
    }
    CELERYBEAT_SCHEDULE = {
        'email_reports.schedule_hourly': {
            'task': 'email_reports.schedule_hourly',
            'schedule': crontab(minute=1, hour='*'),
        },
    }

# Replace your existing CeleryConfig class with:
CELERY_CONFIG = {
    'broker_url': 'redis://redis:6379/0',
    'result_backend': 'redis://redis:6379/0',
    'task_routes': {
        'sql_lab.get_sql_results': {'queue': 'superset_queue'},
        'email_reports.*': {'queue': 'superset_queue'},
    },
    'task_annotations': {
        'sql_lab.get_sql_results': {
            'rate_limit': '100/s',
            'time_limit': 600,
            'soft_time_limit': 600,
        },
    },
}