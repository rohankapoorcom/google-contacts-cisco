# Task 1.2: Database Setup

## Overview

Set up SQLite database with SQLAlchemy ORM and Alembic migrations. Define the database schema for contacts, phone numbers, and sync state.

## Priority

**P0 (Critical)** - Required for MVP

## Dependencies

- Task 1.1: Environment Setup (must be completed first)

## Objectives

1. Configure SQLAlchemy with SQLite
2. Define database models (Contact, PhoneNumber, SyncState)
3. Set up Alembic for database migrations
4. Create initial migration
5. Test database connectivity and basic operations

## Technical Context

### Database: SQLite
- File-based database: `data/contacts.db`
- No separate server required
- Sufficient for single-user application
- ACID compliant

### ORM: SQLAlchemy 2.0
- Modern async/sync support
- Declarative models
- Type hints support

### Migrations: Alembic
- Version control for database schema
- Up/down migrations
- Auto-generation from model changes

## Data Model

### Contact Entity
- `id`: UUID (primary key)
- `resource_name`: String (Google Contacts resource name)
- `etag`: String (for conflict detection)
- `given_name`: String (nullable)
- `family_name`: String (nullable)
- `display_name`: String (required, indexed)
- `organization`: String (nullable)
- `job_title`: String (nullable)
- `created_at`: DateTime
- `updated_at`: DateTime
- `deleted`: Boolean (soft delete)
- `synced_at`: DateTime (last sync timestamp)
- **Relationship**: one-to-many with PhoneNumber

### PhoneNumber Entity
- `id`: UUID (primary key)
- `contact_id`: UUID (foreign key to Contact)
- `value`: String (normalized phone number, indexed)
- `display_value`: String (original format)
- `type`: String (work, mobile, home, etc.)
- `primary`: Boolean (is primary phone number)

### SyncState Entity
- `id`: UUID (primary key)
- `sync_token`: String (nullable, for incremental sync)
- `last_sync_at`: DateTime
- `sync_status`: String (idle, syncing, error)
- `error_message`: String (nullable)

## Acceptance Criteria

- [ ] SQLAlchemy is configured with SQLite
- [ ] Database file location is configurable
- [ ] All three models are defined with proper types and relationships
- [ ] Alembic is initialized and configured
- [ ] Initial migration is created and applied
- [ ] Database tables are created successfully
- [ ] Indexes are created on display_name and phone number value
- [ ] Basic CRUD operations work for all models
- [ ] Tests verify database operations

## Implementation Steps

### 1. Create Database Configuration

Create `google_contacts_cisco/config.py`:

```python
"""Application configuration."""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = "sqlite:///./data/contacts.db"
    
    # Application
    app_name: str = "Google Contacts Cisco Directory"
    debug: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
```

### 2. Create Database Connection

Create `google_contacts_cisco/models/__init__.py`:

```python
"""Database models and connection."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 3. Define Contact Model

Create `google_contacts_cisco/models/contact.py`:

```python
"""Contact model."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from . import Base


class Contact(Base):
    """Contact model."""
    
    __tablename__ = "contacts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_name = Column(String, unique=True, nullable=False, index=True)
    etag = Column(String, nullable=True)
    given_name = Column(String, nullable=True)
    family_name = Column(String, nullable=True)
    display_name = Column(String, nullable=False, index=True)
    organization = Column(String, nullable=True)
    job_title = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted = Column(Boolean, default=False, nullable=False)
    synced_at = Column(DateTime, nullable=True)
    
    # Relationships
    phone_numbers = relationship("PhoneNumber", back_populates="contact", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_contact_display_name', 'display_name'),
        Index('idx_contact_resource_name', 'resource_name'),
    )
    
    def __repr__(self):
        return f"<Contact(id={self.id}, display_name='{self.display_name}')>"
```

### 4. Define PhoneNumber Model

Create `google_contacts_cisco/models/phone_number.py`:

```python
"""Phone number model."""
import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from . import Base


class PhoneNumber(Base):
    """Phone number model."""
    
    __tablename__ = "phone_numbers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False)
    value = Column(String, nullable=False, index=True)
    display_value = Column(String, nullable=False)
    type = Column(String, nullable=True)
    primary = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    contact = relationship("Contact", back_populates="phone_numbers")
    
    # Indexes
    __table_args__ = (
        Index('idx_phone_number_value', 'value'),
        Index('idx_phone_number_contact', 'contact_id'),
    )
    
    def __repr__(self):
        return f"<PhoneNumber(id={self.id}, value='{self.value}', type='{self.type}')>"
```

### 5. Define SyncState Model

Create `google_contacts_cisco/models/sync_state.py`:

```python
"""Sync state model."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from . import Base


class SyncState(Base):
    """Sync state model."""
    
    __tablename__ = "sync_states"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_token = Column(String, nullable=True)
    last_sync_at = Column(DateTime, nullable=True)
    sync_status = Column(String, default="idle", nullable=False)
    error_message = Column(String, nullable=True)
    
    def __repr__(self):
        return f"<SyncState(id={self.id}, status='{self.sync_status}', last_sync='{self.last_sync_at}')>"
```

### 6. Initialize Alembic

```bash
cd /workspaces/google-contacts-cisco
alembic init alembic
```

### 7. Configure Alembic

Edit `alembic.ini`:
- Set `sqlalchemy.url` to use the config: `%(DB_URL)s` or comment it out

Edit `alembic/env.py`:

```python
"""Alembic environment configuration."""
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import models
from google_contacts_cisco.models import Base
from google_contacts_cisco.config import settings

# Alembic Config object
config = context.config

# Set database URL from settings
config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

# ... rest of the file remains the same
```

### 8. Create Initial Migration

```bash
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

### 9. Create Database Helper Functions

Create `google_contacts_cisco/models/db_utils.py`:

```python
"""Database utility functions."""
from . import engine, Base


def create_tables():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all tables (use with caution)."""
    Base.metadata.drop_all(bind=engine)
```

### 10. Create Tests

Create `tests/test_database.py`:

```python
"""Test database models."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from google_contacts_cisco.models import Base
from google_contacts_cisco.models.contact import Contact
from google_contacts_cisco.models.phone_number import PhoneNumber
from google_contacts_cisco.models.sync_state import SyncState


@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_contact(db_session):
    """Test creating a contact."""
    contact = Contact(
        resource_name="people/12345",
        display_name="John Doe",
        given_name="John",
        family_name="Doe"
    )
    db_session.add(contact)
    db_session.commit()
    
    assert contact.id is not None
    assert contact.display_name == "John Doe"


def test_contact_with_phone_numbers(db_session):
    """Test contact with phone numbers relationship."""
    contact = Contact(
        resource_name="people/12345",
        display_name="John Doe"
    )
    db_session.add(contact)
    db_session.flush()
    
    phone = PhoneNumber(
        contact_id=contact.id,
        value="1234567890",
        display_value="(123) 456-7890",
        type="mobile",
        primary=True
    )
    db_session.add(phone)
    db_session.commit()
    
    assert len(contact.phone_numbers) == 1
    assert contact.phone_numbers[0].value == "1234567890"


def test_sync_state(db_session):
    """Test sync state model."""
    sync_state = SyncState(
        sync_token="token123",
        sync_status="idle"
    )
    db_session.add(sync_state)
    db_session.commit()
    
    assert sync_state.id is not None
    assert sync_state.sync_status == "idle"
```

## Verification

After completing this task:
1. Run `alembic upgrade head` - should complete without errors
2. Check that `data/contacts.db` file exists
3. Run `pytest tests/test_database.py` - all tests should pass
4. Verify tables exist in database using SQLite browser or command line

## Notes

- UUID is used for primary keys for better distributed system support
- Soft deletes are used (deleted flag) rather than hard deletes
- Indexes are created on frequently queried fields
- Relationships are properly defined for easy navigation

## Related Documentation

- SQLAlchemy 2.0: https://docs.sqlalchemy.org/en/20/
- Alembic: https://alembic.sqlalchemy.org/
- Pydantic Settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/

## Estimated Time

3-4 hours

