"""Test Contact Repository.

This module tests the ContactRepository implementation for database operations
on Contact and PhoneNumber entities.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from google_contacts_cisco.models import Base, Contact, PhoneNumber
from google_contacts_cisco.repositories.contact_repository import ContactRepository
from google_contacts_cisco.schemas.contact import ContactCreateSchema, PhoneNumberSchema


@pytest.fixture
def db_session():
    """Create test database session with in-memory SQLite."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def contact_repo(db_session):
    """Create ContactRepository instance."""
    return ContactRepository(db_session)


@pytest.fixture
def sample_contact_data():
    """Create sample contact data for testing."""
    return ContactCreateSchema(
        resource_name="people/c12345",
        etag="abc123",
        given_name="John",
        family_name="Doe",
        display_name="John Doe",
        organization="Acme Corp",
        job_title="Engineer",
        phone_numbers=[
            PhoneNumberSchema(
                value="5551234567",
                display_value="(555) 123-4567",
                type="mobile",
                primary=True,
            ),
            PhoneNumberSchema(
                value="5559876543",
                display_value="(555) 987-6543",
                type="work",
                primary=False,
            ),
        ],
        deleted=False,
    )


@pytest.fixture
def sample_contact_minimal():
    """Create minimal contact data (only required fields)."""
    return ContactCreateSchema(
        resource_name="people/c99999",
        display_name="Minimal Contact",
    )


class TestCreateContact:
    """Test contact creation functionality."""

    def test_create_contact_success(self, contact_repo, db_session, sample_contact_data):
        """Test creating a contact with all fields."""
        contact = contact_repo.create_contact(sample_contact_data)
        db_session.commit()

        assert contact.id is not None
        assert contact.resource_name == "people/c12345"
        assert contact.etag == "abc123"
        assert contact.given_name == "John"
        assert contact.family_name == "Doe"
        assert contact.display_name == "John Doe"
        assert contact.organization == "Acme Corp"
        assert contact.job_title == "Engineer"
        assert contact.deleted is False
        assert contact.synced_at is not None

    def test_create_contact_with_phone_numbers(
        self, contact_repo, db_session, sample_contact_data
    ):
        """Test that phone numbers are created with contact."""
        contact = contact_repo.create_contact(sample_contact_data)
        db_session.commit()

        assert len(contact.phone_numbers) == 2

        # Check first phone number (primary)
        primary_phones = [p for p in contact.phone_numbers if p.primary]
        assert len(primary_phones) == 1
        assert primary_phones[0].value == "5551234567"
        assert primary_phones[0].type == "mobile"

        # Check second phone number
        work_phones = [p for p in contact.phone_numbers if p.type == "work"]
        assert len(work_phones) == 1
        assert work_phones[0].value == "5559876543"

    def test_create_contact_minimal(self, contact_repo, db_session, sample_contact_minimal):
        """Test creating contact with only required fields."""
        contact = contact_repo.create_contact(sample_contact_minimal)
        db_session.commit()

        assert contact.id is not None
        assert contact.resource_name == "people/c99999"
        assert contact.display_name == "Minimal Contact"
        assert contact.given_name is None
        assert contact.family_name is None
        assert contact.organization is None
        assert len(contact.phone_numbers) == 0

    def test_create_contact_no_phone_numbers(self, contact_repo, db_session):
        """Test creating contact without phone numbers."""
        data = ContactCreateSchema(
            resource_name="people/c11111",
            display_name="No Phones",
            phone_numbers=[],
        )
        contact = contact_repo.create_contact(data)
        db_session.commit()

        assert contact.id is not None
        assert len(contact.phone_numbers) == 0


class TestGetContact:
    """Test contact retrieval functionality."""

    def test_get_by_resource_name_exists(
        self, contact_repo, db_session, sample_contact_data
    ):
        """Test getting contact by resource name when it exists."""
        created = contact_repo.create_contact(sample_contact_data)
        db_session.commit()

        found = contact_repo.get_by_resource_name("people/c12345")

        assert found is not None
        assert found.id == created.id
        assert found.display_name == "John Doe"

    def test_get_by_resource_name_not_found(self, contact_repo):
        """Test getting contact by resource name when it doesn't exist."""
        found = contact_repo.get_by_resource_name("people/nonexistent")
        assert found is None

    def test_get_by_id_exists(self, contact_repo, db_session, sample_contact_data):
        """Test getting contact by ID when it exists."""
        created = contact_repo.create_contact(sample_contact_data)
        db_session.commit()

        found = contact_repo.get_by_id(created.id)

        assert found is not None
        assert found.resource_name == "people/c12345"

    def test_get_by_id_not_found(self, contact_repo):
        """Test getting contact by ID when it doesn't exist."""
        import uuid

        found = contact_repo.get_by_id(uuid.uuid4())
        assert found is None


class TestUpsertContact:
    """Test contact upsert (insert or update) functionality."""

    def test_upsert_creates_new_contact(
        self, contact_repo, db_session, sample_contact_data
    ):
        """Test that upsert creates a new contact when none exists."""
        contact = contact_repo.upsert_contact(sample_contact_data)
        db_session.commit()

        assert contact.id is not None
        assert contact.display_name == "John Doe"
        assert contact_repo.count_all() == 1

    def test_upsert_updates_existing_contact(
        self, contact_repo, db_session, sample_contact_data
    ):
        """Test that upsert updates existing contact."""
        # Create initial contact
        initial = contact_repo.create_contact(sample_contact_data)
        db_session.commit()
        initial_id = initial.id

        # Update data
        updated_data = ContactCreateSchema(
            resource_name="people/c12345",  # Same resource name
            etag="xyz789",  # New etag
            given_name="Johnny",  # Changed name
            family_name="Doe",
            display_name="Johnny Doe",  # Changed display name
            organization="New Corp",  # Changed org
            job_title="Senior Engineer",  # Changed title
            phone_numbers=[
                PhoneNumberSchema(
                    value="5551111111",  # New phone number
                    display_value="(555) 111-1111",
                    type="home",
                    primary=True,
                ),
            ],
            deleted=False,
        )

        # Upsert
        contact = contact_repo.upsert_contact(updated_data)
        db_session.commit()

        # Verify updates
        assert contact.id == initial_id  # Same ID
        assert contact.display_name == "Johnny Doe"
        assert contact.given_name == "Johnny"
        assert contact.organization == "New Corp"
        assert contact.job_title == "Senior Engineer"
        assert contact.etag == "xyz789"
        assert len(contact.phone_numbers) == 1
        assert contact.phone_numbers[0].value == "5551111111"
        assert contact_repo.count_all() == 1  # Still just one contact

    def test_upsert_replaces_phone_numbers(
        self, contact_repo, db_session, sample_contact_data
    ):
        """Test that upsert replaces all phone numbers."""
        # Create contact with 2 phone numbers
        contact_repo.create_contact(sample_contact_data)
        db_session.commit()

        # Update with 1 phone number
        updated_data = ContactCreateSchema(
            resource_name="people/c12345",
            display_name="John Doe",
            phone_numbers=[
                PhoneNumberSchema(
                    value="5552222222",
                    display_value="(555) 222-2222",
                    type="mobile",
                    primary=True,
                ),
            ],
        )

        contact = contact_repo.upsert_contact(updated_data)
        db_session.commit()

        # Refresh to get updated phone numbers
        db_session.refresh(contact)
        assert len(contact.phone_numbers) == 1
        assert contact.phone_numbers[0].value == "5552222222"


class TestMarkAsDeleted:
    """Test soft delete functionality."""

    def test_mark_as_deleted_exists(
        self, contact_repo, db_session, sample_contact_data
    ):
        """Test marking an existing contact as deleted."""
        contact_repo.create_contact(sample_contact_data)
        db_session.commit()

        result = contact_repo.mark_as_deleted("people/c12345")
        db_session.commit()

        assert result is not None
        assert result.deleted is True
        assert result.synced_at is not None

    def test_mark_as_deleted_not_found(self, contact_repo):
        """Test marking a non-existent contact as deleted."""
        result = contact_repo.mark_as_deleted("people/nonexistent")
        assert result is None


class TestGetContacts:
    """Test bulk contact retrieval functionality."""

    def test_get_all_active_with_deleted(self, contact_repo, db_session):
        """Test getting active contacts excludes deleted ones."""
        # Create active contact
        active_data = ContactCreateSchema(
            resource_name="people/c1",
            display_name="Active Contact",
            deleted=False,
        )
        contact_repo.create_contact(active_data)

        # Create deleted contact
        deleted_data = ContactCreateSchema(
            resource_name="people/c2",
            display_name="Deleted Contact",
            deleted=True,
        )
        contact_repo.create_contact(deleted_data)
        db_session.commit()

        active = contact_repo.get_all_active()

        assert len(active) == 1
        assert active[0].display_name == "Active Contact"

    def test_get_all_active_empty(self, contact_repo):
        """Test getting active contacts when none exist."""
        active = contact_repo.get_all_active()
        assert len(active) == 0

    def test_get_all_includes_deleted(self, contact_repo, db_session):
        """Test getting all contacts includes deleted ones."""
        # Create active and deleted contacts
        for i, deleted in enumerate([False, True]):
            data = ContactCreateSchema(
                resource_name=f"people/c{i}",
                display_name=f"Contact {i}",
                deleted=deleted,
            )
            contact_repo.create_contact(data)
        db_session.commit()

        all_contacts = contact_repo.get_all()

        assert len(all_contacts) == 2


class TestCountContacts:
    """Test contact counting functionality."""

    def test_count_all(self, contact_repo, db_session):
        """Test counting all contacts."""
        for i in range(3):
            data = ContactCreateSchema(
                resource_name=f"people/c{i}",
                display_name=f"Contact {i}",
            )
            contact_repo.create_contact(data)
        db_session.commit()

        assert contact_repo.count_all() == 3

    def test_count_all_empty(self, contact_repo):
        """Test counting when no contacts exist."""
        assert contact_repo.count_all() == 0

    def test_count_active(self, contact_repo, db_session):
        """Test counting active (non-deleted) contacts."""
        # Create 2 active and 1 deleted
        for i in range(3):
            data = ContactCreateSchema(
                resource_name=f"people/c{i}",
                display_name=f"Contact {i}",
                deleted=(i == 2),  # Last one is deleted
            )
            contact_repo.create_contact(data)
        db_session.commit()

        assert contact_repo.count_active() == 2

    def test_count_active_empty(self, contact_repo):
        """Test counting active contacts when none exist."""
        assert contact_repo.count_active() == 0


class TestDeleteAllContacts:
    """Test bulk delete functionality."""

    def test_delete_all(self, contact_repo, db_session):
        """Test deleting all contacts."""
        for i in range(5):
            data = ContactCreateSchema(
                resource_name=f"people/c{i}",
                display_name=f"Contact {i}",
                phone_numbers=[
                    PhoneNumberSchema(
                        value=f"555000{i}",
                        display_value=f"555-000-{i}",
                        type="mobile",
                        primary=True,
                    ),
                ],
            )
            contact_repo.create_contact(data)
        db_session.commit()

        count = contact_repo.delete_all()
        db_session.commit()

        assert count == 5
        assert contact_repo.count_all() == 0
        # Verify phone numbers also deleted
        assert db_session.query(PhoneNumber).count() == 0

    def test_delete_all_empty(self, contact_repo, db_session):
        """Test deleting when no contacts exist."""
        count = contact_repo.delete_all()
        assert count == 0

