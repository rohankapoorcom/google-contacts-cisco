"""Database models and connection."""
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.types import TypeDecorator, CHAR
from ..config import settings

# Create database directory if it doesn't exist
from pathlib import Path
Path("data").mkdir(exist_ok=True)

# Create engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # Needed for SQLite
    echo=settings.debug  # Log SQL queries in debug mode
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    
    Uses CHAR(36) on SQLite, stores as string.
    Compatible with PostgreSQL UUID type.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(uuid.UUID)
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value


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
from .sync_state import SyncState  # noqa: E402

__all__ = ["Base", "engine", "SessionLocal", "get_db", "GUID", "Contact", "PhoneNumber", "SyncState"]
