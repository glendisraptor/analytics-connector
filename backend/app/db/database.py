from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from ..core.config import settings
from ..models.user import Base

# Create database engine
engine = create_engine(settings.DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """Database dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
