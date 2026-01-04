"""Test database models and operations.

This module tests the database setup implementation from Task 02.
"""
import pytest
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from google_contacts_cisco.models import Base, Contact, PhoneNumber, SyncState
from google_contacts_cisco.models.db_utils import create_tables, drop_tables


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
    assert isinstance(contact.id, uuid.UUID)
    assert contact.display_name == "John Doe"
    assert contact.given_name == "John"
    assert contact.family_name == "Doe"
    assert contact.deleted is False
    assert contact.created_at is not None
    assert contact.updated_at is not None


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
    assert contact.phone_numbers[0].display_value == "(123) 456-7890"
    assert contact.phone_numbers[0].type == "mobile"
    assert contact.phone_numbers[0].primary is True


def test_contact_multiple_phone_numbers(db_session):
    """Test contact with multiple phone numbers."""
    contact = Contact(
        resource_name="people/12345",
        display_name="Jane Smith"
    )
    db_session.add(contact)
    db_session.flush()
    
    phone1 = PhoneNumber(
        contact_id=contact.id,
        value="1234567890",
        display_value="(123) 456-7890",
        type="mobile",
        primary=True
    )
    phone2 = PhoneNumber(
        contact_id=contact.id,
        value="0987654321",
        display_value="(098) 765-4321",
        type="work",
        primary=False
    )
    db_session.add_all([phone1, phone2])
    db_session.commit()
    
    assert len(contact.phone_numbers) == 2
    primary_phones = [p for p in contact.phone_numbers if p.primary]
    assert len(primary_phones) == 1
    assert primary_phones[0].value == "1234567890"


def test_contact_cascade_delete(db_session):
    """Test that phone numbers are deleted when contact is deleted."""
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
        type="mobile"
    )
    db_session.add(phone)
    db_session.commit()
    
    contact_id = contact.id
    phone_id = phone.id
    
    db_session.delete(contact)
    db_session.commit()
    
    # Verify contact is deleted
    deleted_contact = db_session.query(Contact).filter_by(id=contact_id).first()
    assert deleted_contact is None
    
    # Verify phone number is also deleted (cascade)
    deleted_phone = db_session.query(PhoneNumber).filter_by(id=phone_id).first()
    assert deleted_phone is None


def test_contact_soft_delete(db_session):
    """Test soft delete functionality."""
    contact = Contact(
        resource_name="people/12345",
        display_name="John Doe",
        deleted=False
    )
    db_session.add(contact)
    db_session.commit()
    
    assert contact.deleted is False
    
    contact.deleted = True
    db_session.commit()
    
    assert contact.deleted is True
    # Contact still exists in database
    found = db_session.query(Contact).filter_by(id=contact.id).first()
    assert found is not None
    assert found.deleted is True


def test_sync_state(db_session):
    """Test sync state model."""
    sync_state = SyncState(
        sync_token="token123",
        sync_status="idle"
    )
    db_session.add(sync_state)
    db_session.commit()
    
    assert sync_state.id is not None
    assert isinstance(sync_state.id, uuid.UUID)
    assert sync_state.sync_status == "idle"
    assert sync_state.sync_token == "token123"
    assert sync_state.error_message is None


def test_sync_state_statuses(db_session):
    """Test different sync state statuses."""
    states = ["idle", "syncing", "error"]
    
    for status in states:
        sync_state = SyncState(sync_status=status)
        db_session.add(sync_state)
    
    db_session.commit()
    
    for status in states:
        found = db_session.query(SyncState).filter_by(sync_status=status).first()
        assert found is not None
        assert found.sync_status == status


def test_sync_state_with_error(db_session):
    """Test sync state with error message."""
    sync_state = SyncState(
        sync_status="error",
        error_message="Connection timeout"
    )
    db_session.add(sync_state)
    db_session.commit()
    
    assert sync_state.sync_status == "error"
    assert sync_state.error_message == "Connection timeout"


def test_contact_timestamps(db_session):
    """Test that timestamps are automatically set."""
    contact = Contact(
        resource_name="people/12345",
        display_name="John Doe"
    )
    db_session.add(contact)
    db_session.commit()
    
    assert contact.created_at is not None
    assert contact.updated_at is not None
    assert isinstance(contact.created_at, datetime)
    assert isinstance(contact.updated_at, datetime)
    
    # Test updated_at changes on update
    original_updated = contact.updated_at
    contact.display_name = "John Updated"
    db_session.commit()
    
    assert contact.updated_at > original_updated


def test_contact_required_fields(db_session):
    """Test that required fields are enforced."""
    # Missing display_name should fail
    with pytest.raises(Exception):
        contact = Contact(resource_name="people/12345")
        db_session.add(contact)
        db_session.commit()


def test_contact_unique_resource_name(db_session):
    """Test that resource_name must be unique."""
    contact1 = Contact(
        resource_name="people/12345",
        display_name="John Doe"
    )
    db_session.add(contact1)
    db_session.commit()
    
    # Try to create another contact with same resource_name
    contact2 = Contact(
        resource_name="people/12345",
        display_name="Jane Doe"
    )
    db_session.add(contact2)
    
    with pytest.raises(Exception):
        db_session.commit()


def test_phone_number_required_fields(db_session):
    """Test that phone number required fields are enforced."""
    contact = Contact(
        resource_name="people/12345",
        display_name="John Doe"
    )
    db_session.add(contact)
    db_session.flush()
    
    # Missing value should fail
    with pytest.raises(Exception):
        phone = PhoneNumber(
            contact_id=contact.id,
            display_value="(123) 456-7890"
        )
        db_session.add(phone)
        db_session.commit()


def test_phone_number_foreign_key(db_session):
    """Test that phone number requires valid contact_id.
    
    Note: SQLite doesn't enforce foreign key constraints by default.
    This test verifies the relationship exists but doesn't enforce referential integrity.
    """
    invalid_contact_id = uuid.uuid4()
    
    # SQLite allows orphaned foreign keys unless PRAGMA foreign_keys is enabled
    # This test verifies the model structure is correct
    phone = PhoneNumber(
        contact_id=invalid_contact_id,
        value="1234567890",
        display_value="(123) 456-7890"
    )
    db_session.add(phone)
    db_session.commit()
    
    # Verify phone was created (SQLite doesn't enforce FK by default)
    found = db_session.query(PhoneNumber).filter_by(id=phone.id).first()
    assert found is not None
    # The relationship won't work since contact doesn't exist
    assert found.contact_id == invalid_contact_id


def test_database_utils_create_tables():
    """Test create_tables utility function."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.bind = engine
    
    # Should not raise an exception
    create_tables()


def test_database_utils_drop_tables():
    """Test drop_tables utility function."""
    from google_contacts_cisco.models.db_utils import drop_tables
    from google_contacts_cisco.models import Base
    from sqlalchemy import create_engine, inspect
    
    # Use a separate test engine
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.bind = test_engine
    
    # Create tables first
    Base.metadata.create_all(bind=test_engine)
    
    # Verify tables exist using inspector
    inspector = inspect(test_engine)
    table_names = inspector.get_table_names()
    assert 'contacts' in table_names
    assert 'phone_numbers' in table_names
    assert 'sync_states' in table_names
    
    # Temporarily replace the engine in db_utils to use our test engine
    import google_contacts_cisco.models.db_utils as db_utils_module
    original_engine = db_utils_module.engine
    db_utils_module.engine = test_engine
    
    try:
        # Then drop them
        drop_tables()
        
        # Verify tables are dropped
        table_names_after = inspect(test_engine).get_table_names()
        # Filter out alembic_version if it exists
        table_names_after = [t for t in table_names_after if t != 'alembic_version']
        assert 'contacts' not in table_names_after
        assert 'phone_numbers' not in table_names_after
        assert 'sync_states' not in table_names_after
    finally:
        # Restore original engine
        db_utils_module.engine = original_engine


def test_contact_query_by_display_name(db_session):
    """Test querying contacts by display_name (indexed field)."""
    contact1 = Contact(
        resource_name="people/1",
        display_name="Alice"
    )
    contact2 = Contact(
        resource_name="people/2",
        display_name="Bob"
    )
    db_session.add_all([contact1, contact2])
    db_session.commit()
    
    found = db_session.query(Contact).filter_by(display_name="Alice").first()
    assert found is not None
    assert found.display_name == "Alice"
    assert found.resource_name == "people/1"


def test_phone_number_query_by_value(db_session):
    """Test querying phone numbers by value (indexed field)."""
    contact = Contact(
        resource_name="people/1",
        display_name="John Doe"
    )
    db_session.add(contact)
    db_session.flush()
    
    phone = PhoneNumber(
        contact_id=contact.id,
        value="1234567890",
        display_value="(123) 456-7890",
        type="mobile"
    )
    db_session.add(phone)
    db_session.commit()
    
    found = db_session.query(PhoneNumber).filter_by(value="1234567890").first()
    assert found is not None
    assert found.value == "1234567890"
    assert found.contact.display_name == "John Doe"


def test_contact_synced_at(db_session):
    """Test synced_at field."""
    contact = Contact(
        resource_name="people/12345",
        display_name="John Doe"
    )
    db_session.add(contact)
    db_session.commit()
    
    assert contact.synced_at is None
    
    contact.synced_at = datetime.utcnow()
    db_session.commit()
    
    assert contact.synced_at is not None
    assert isinstance(contact.synced_at, datetime)


def test_contact_optional_fields(db_session):
    """Test that optional fields can be None."""
    contact = Contact(
        resource_name="people/12345",
        display_name="John Doe"
    )
    db_session.add(contact)
    db_session.commit()
    
    assert contact.etag is None
    assert contact.given_name is None
    assert contact.family_name is None
    assert contact.organization is None
    assert contact.job_title is None
    assert contact.synced_at is None


def test_phone_number_optional_type(db_session):
    """Test that phone number type can be None."""
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
        type=None
    )
    db_session.add(phone)
    db_session.commit()
    
    assert phone.type is None


def test_phone_number_primary_default(db_session):
    """Test that phone number primary defaults to False."""
    contact = Contact(
        resource_name="people/12345",
        display_name="John Doe"
    )
    db_session.add(contact)
    db_session.flush()
    
    phone = PhoneNumber(
        contact_id=contact.id,
        value="1234567890",
        display_value="(123) 456-7890"
    )
    db_session.add(phone)
    db_session.commit()
    
    assert phone.primary is False

