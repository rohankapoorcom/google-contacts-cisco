"""Database models and connection."""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from ..config import settings

# Create database directory if it doesn't exist
from pathlib import Path
Path("data").mkdir(exist_ok=True)

# Create engine with error handling
try:
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},  # Needed for SQLite
        echo=settings.debug  # Log SQL queries in debug mode
    )
except Exception as e:
    raise RuntimeError(
        f"Failed to create database engine with URL: {settings.database_url}. "
        f"Please check your database configuration. Error: {e}"
    ) from e


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign key constraints for SQLite."""
    if "sqlite" in settings.database_url:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Import models to register them with Base
from .contact import Contact  # noqa: E402
from .phone_number import PhoneNumber  # noqa: E402
from .sync_state import SyncState, SyncStatus  # noqa: E402

__all__ = ["Base", "engine", "SessionLocal", "get_db", "Contact", "PhoneNumber", "SyncState", "SyncStatus"]
