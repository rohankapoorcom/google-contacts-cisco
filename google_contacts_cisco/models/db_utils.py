"""Database utility functions."""
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from . import engine, Base


def create_tables() -> None:
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def drop_tables() -> None:
    """Drop all tables (use with caution)."""
    Base.metadata.drop_all(bind=engine)


def check_connection() -> bool:
    """Check if database connection is available.
    
    Returns:
        True if connection is successful, False otherwise.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False

