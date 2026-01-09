from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy.pool import StaticPool
from typing import Generator
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Determine which database to use
if settings.USE_POSTGRES:
    DATABASE_URL = settings.DATABASE_URL
    connect_args = {}
    poolclass = None
    logger.info(f"Using PostgreSQL database")
else:
    DATABASE_URL = settings.SQLITE_URL
    connect_args = {"check_same_thread": False}
    poolclass = StaticPool
    logger.info(f"Using SQLite database")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    poolclass=poolclass,
    echo=settings.DEBUG,
)


def init_db():
    """Initialize database tables"""
    logger.info("Initializing database tables")
    SQLModel.metadata.create_all(engine)
    logger.info("Database tables created successfully")


def get_session() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI.
    Ensures proper session management and cleanup.
    """
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception as e:
            logger.error(f"Database session error: {str(e)}")
            session.rollback()
            raise
