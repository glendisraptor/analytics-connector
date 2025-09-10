import os
from flask_caching.backends.rediscache import RedisCache
from celery.schedules import crontab
import logging

# Superset logging level
LOG_LEVEL = "DEBUG"

# Make Flask / Werkzeug more verbose
logging.getLogger("flask_appbuilder").setLevel(logging.DEBUG)
logging.getLogger("werkzeug").setLevel(logging.DEBUG)
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

# Basic configuration
SECRET_KEY = os.environ.get('SUPERSET_SECRET_KEY', 'your-superset-secret-key')
SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:admin@postgres:5432/analytics_data'

# Security
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = None

# Feature flags
FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
    "DASHBOARD_CROSS_FILTERS": True,
    "DASHBOARD_NATIVE_FILTERS": True,
}

# Cache configuration - Use different Redis DB than Celery
CACHE_CONFIG = {
    'CACHE_TYPE': 'RedisCache',
    'CACHE_DEFAULT_TIMEOUT': 300,
    'CACHE_KEY_PREFIX': 'superset_',
    'CACHE_REDIS_HOST': 'redis',
    'CACHE_REDIS_PORT': 6379,
    'CACHE_REDIS_DB': 2,  # Different from Celery DBs
}

# SQL Lab Configuration
SQLLAB_ASYNC_TIME_LIMIT_SEC = 300
SQLLAB_TIMEOUT = 300

# Celery configuration
CELERY_CONFIG = {
    'broker_url': 'redis://redis:6379/0',
    'result_backend': 'redis://redis:6379/0',
    'include': ['superset.sql_lab'],
    'result_expires': 3600,
    'task_serializer': 'json',
    'result_serializer': 'json',
    'accept_content': ['json'],
    'worker_prefetch_multiplier': 1,
    'task_acks_late': True,
    'task_routes': {
        'sql_lab.get_sql_results': {'queue': 'superset_queue'},
        'email_reports.*': {'queue': 'superset_queue'},
        'reports.*': {'queue': 'superset_queue'},
    },
    'task_annotations': {
        'sql_lab.get_sql_results': {
            'rate_limit': '100/s',
            'time_limit': 600,
            'soft_time_limit': 580,
        },
        'email_reports.send': {
            'rate_limit': '1/s',
            'time_limit': 120,
            'soft_time_limit': 150,
            'ignore_result': True,
        },
    },
    'beat_schedule': {
        'email_reports.schedule_hourly': {
            'task': 'email_reports.schedule_hourly',
            'schedule': crontab(minute=1, hour='*'),
        },
    },
}

# ❗ Correct RESULTS_BACKEND configuration ❗
RESULTS_BACKEND = RedisCache(
    host='redis',
    port=6379,
    db=3,
    key_prefix='superset_results'
)


# Row limit for SQL Lab
DEFAULT_SQLLAB_LIMIT = 1000
SQL_MAX_ROW = 100000

# Enable data upload functionality
FEATURE_FLAGS.update({
    "ENABLE_UPLOAD_TO_SUPERSET": True,
})

# Database connection pool settings
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'connect_args': {"sslmode": "disable"}
}