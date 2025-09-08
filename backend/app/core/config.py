from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl
from typing import List, Union
from typing import Optional, List
import os

class Settings(BaseSettings):
    # App Configuration
    APP_NAME: str = "Analytics Connector"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-this")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/analytics_connector")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379")
    
    # CORS
    # BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8080"]
    BACKEND_CORS_ORIGINS: Union[str, List[AnyHttpUrl]] = [
        "http://localhost:3000",
        "http://localhost:1111",
        "http://localhost:8080"
    ]
    
    # Analytics Database (separate from app database)
    ANALYTICS_DATABASE_URL: str = os.getenv("ANALYTICS_DATABASE_URL", "postgresql://postgres:admin@localhost:5432/analytics_data")
    
    # Superset Configuration
    SUPERSET_URL: str = os.getenv("SUPERSET_URL", "http://localhost:8088")
    SUPERSET_USERNAME: str = os.getenv("SUPERSET_USERNAME", "admin")
    SUPERSET_PASSWORD: str = os.getenv("SUPERSET_PASSWORD", "admin")

    class Config:
        env_file = ".env"

settings = Settings()