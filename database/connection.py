"""
Database connection and session management.
"""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from config.settings import settings
from database.models import Base
from utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, database_url: str = None):
        """
        Initialize database manager.

        Args:
            database_url: PostgreSQL connection URL
        """
        self.database_url = database_url or settings.DATABASE_URL
        self.engine = None
        self.SessionLocal = None

    def connect(self) -> None:
        """Establish database connection and create engine."""
        try:
            self.engine = create_engine(
                self.database_url,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,  # Recycle connections after 30 minutes
                echo=settings.LOG_LEVEL == "DEBUG"
            )
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def disconnect(self) -> None:
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")

    def create_tables(self) -> None:
        """Create all database tables."""
        if self.engine is None:
            self.connect()
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created")

    def drop_tables(self) -> None:
        """Drop all database tables (use with caution)."""
        if self.engine is None:
            self.connect()
        Base.metadata.drop_all(bind=self.engine)
        logger.warning("Database tables dropped")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session with automatic cleanup.

        Yields:
            SQLAlchemy Session

        Example:
            with db.get_session() as session:
                session.add(model)
                session.commit()
        """
        if self.SessionLocal is None:
            self.connect()

        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def get_session_direct(self) -> Session:
        """
        Get a database session directly (caller responsible for cleanup).

        Returns:
            SQLAlchemy Session
        """
        if self.SessionLocal is None:
            self.connect()
        return self.SessionLocal()


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> DatabaseManager:
    """Get the global database manager instance."""
    return db_manager


def init_db() -> None:
    """Initialize database connection and create tables."""
    db_manager.connect()
    db_manager.create_tables()
