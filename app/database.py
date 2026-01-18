from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy.pool import StaticPool
from collections.abc import Generator
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Determine which database to use
if settings.USE_POSTGRES:
    DATABASE_URL = settings.DATABASE_URL
    connect_args = {}
    poolclass = None
    logger.info("Using PostgreSQL database")
else:
    DATABASE_URL = settings.SQLITE_URL
    connect_args = {"check_same_thread": False}
    poolclass = StaticPool
    logger.info("Using SQLite database")

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

    This implements the Unit of Work pattern:
    - Session is created at request start
    - All operations share the same session
    - Commit happens only if request succeeds
    - Rollback happens on any exception
    - Session is always closed (via context manager)
    """
    session = Session(engine)
    try:
        yield session
        # Commit only if no exception occurred
        session.commit()
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        # Rollback on any exception
        session.rollback()
        raise
    finally:
        # Always close the session to return connection to pool
        session.close()
