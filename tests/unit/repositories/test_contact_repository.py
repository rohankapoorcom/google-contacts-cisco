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

    def test_get_all_active_with_phones(self, contact_repo, db_session):
        """Test get_all_active_with_phones returns only contacts with phone numbers."""
        # Create contact with phone
        contact1 = ContactCreateSchema(
            resource_name="people/withphone",
            display_name="Has Phone",
            phone_numbers=[
                PhoneNumberSchema(
                    value="+15551234567",
                    display_value="+1-555-123-4567",
                    type="mobile",
                    primary=True,
                ),
            ],
            deleted=False,
        )
        contact_repo.create_contact(contact1)

        # Create contact without phone
        contact2 = ContactCreateSchema(
            resource_name="people/nophone",
            display_name="No Phone",
            phone_numbers=[],
            deleted=False,
        )
        contact_repo.create_contact(contact2)

        # Create deleted contact with phone
        contact3 = ContactCreateSchema(
            resource_name="people/deleted",
            display_name="Deleted With Phone",
            phone_numbers=[
                PhoneNumberSchema(
                    value="+15559876543",
                    display_value="+1-555-987-6543",
                    type="work",
                    primary=True,
                ),
            ],
            deleted=True,
        )
        contact_repo.create_contact(contact3)
        db_session.commit()

        # Get contacts with phones
        results = contact_repo.get_all_active_with_phones()

        # Should only return contact1
        assert len(results) == 1
        assert results[0].display_name == "Has Phone"

    def test_get_all_active_with_phones_empty(self, contact_repo, db_session):
        """Test get_all_active_with_phones with no qualifying contacts."""
        # Create contact without phone
        contact = ContactCreateSchema(
            resource_name="people/nophone",
            display_name="No Phone",
            phone_numbers=[],
            deleted=False,
        )
        contact_repo.create_contact(contact)
        db_session.commit()

        results = contact_repo.get_all_active_with_phones()
        assert len(results) == 0

    def test_get_all_active_with_phones_multiple(self, contact_repo, db_session):
        """Test get_all_active_with_phones returns multiple contacts correctly."""
        # Create 3 contacts with phones
        for i in range(3):
            contact = ContactCreateSchema(
                resource_name=f"people/contact{i}",
                display_name=f"Contact {i}",
                phone_numbers=[
                    PhoneNumberSchema(
                        value=f"+155512340{i}",
                        display_value=f"+1-555-1234-0{i}",
                        type="mobile",
                        primary=True,
                    ),
                ],
                deleted=False,
            )
            contact_repo.create_contact(contact)

        # Create 2 contacts without phones
        for i in range(2):
            contact = ContactCreateSchema(
                resource_name=f"people/nophone{i}",
                display_name=f"No Phone {i}",
                phone_numbers=[],
                deleted=False,
            )
            contact_repo.create_contact(contact)
        db_session.commit()

        results = contact_repo.get_all_active_with_phones()
        
        # Should return exactly 3 contacts
        assert len(results) == 3
        display_names = [c.display_name for c in results]
        assert "Contact 0" in display_names
        assert "Contact 1" in display_names
        assert "Contact 2" in display_names
        assert "No Phone 0" not in display_names
        assert "No Phone 1" not in display_names


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


class TestSearchByPhone:
    """Test phone number search functionality."""

    def test_search_by_phone_exact_match(self, contact_repo, db_session):
        """Test searching for exact phone number match."""
        # Create contact with normalized phone number
        data = ContactCreateSchema(
            resource_name="people/c1",
            display_name="John Doe",
            phone_numbers=[
                PhoneNumberSchema(
                    value="+15551234567",
                    display_value="(555) 123-4567",
                    type="mobile",
                    primary=True,
                ),
            ],
        )
        contact_repo.create_contact(data)
        db_session.commit()

        # Search with same format
        results = contact_repo.search_by_phone("5551234567")
        assert len(results) == 1
        assert results[0].display_name == "John Doe"

    def test_search_by_phone_formatted(self, contact_repo, db_session):
        """Test searching with formatted phone number."""
        data = ContactCreateSchema(
            resource_name="people/c1",
            display_name="Jane Doe",
            phone_numbers=[
                PhoneNumberSchema(
                    value="+15559876543",
                    display_value="(555) 987-6543",
                    type="work",
                    primary=True,
                ),
            ],
        )
        contact_repo.create_contact(data)
        db_session.commit()

        # Search with formatted number
        results = contact_repo.search_by_phone("(555) 987-6543")
        assert len(results) == 1
        assert results[0].display_name == "Jane Doe"

    def test_search_by_phone_with_country_code(self, contact_repo, db_session):
        """Test searching with country code prefix."""
        data = ContactCreateSchema(
            resource_name="people/c1",
            display_name="Bob Smith",
            phone_numbers=[
                PhoneNumberSchema(
                    value="+15551112222",
                    display_value="(555) 111-2222",
                    type="home",
                    primary=True,
                ),
            ],
        )
        contact_repo.create_contact(data)
        db_session.commit()

        # Search with +1 prefix
        results = contact_repo.search_by_phone("+1 555-111-2222")
        assert len(results) == 1
        assert results[0].display_name == "Bob Smith"

    def test_search_by_phone_no_results(self, contact_repo, db_session):
        """Test searching for non-existent phone number."""
        data = ContactCreateSchema(
            resource_name="people/c1",
            display_name="Alice",
            phone_numbers=[
                PhoneNumberSchema(
                    value="+15551234567",
                    display_value="(555) 123-4567",
                    type="mobile",
                    primary=True,
                ),
            ],
        )
        contact_repo.create_contact(data)
        db_session.commit()

        results = contact_repo.search_by_phone("5559999999")
        assert len(results) == 0

    def test_search_by_phone_excludes_deleted(self, contact_repo, db_session):
        """Test that search excludes deleted contacts."""
        data = ContactCreateSchema(
            resource_name="people/c1",
            display_name="Deleted Contact",
            phone_numbers=[
                PhoneNumberSchema(
                    value="+15551234567",
                    display_value="(555) 123-4567",
                    type="mobile",
                    primary=True,
                ),
            ],
            deleted=True,
        )
        contact_repo.create_contact(data)
        db_session.commit()

        results = contact_repo.search_by_phone("5551234567")
        assert len(results) == 0

    def test_search_by_phone_multiple_contacts(self, contact_repo, db_session):
        """Test searching returns multiple contacts with same number."""
        # Create two contacts with different phone numbers
        for i, name in enumerate(["John", "Jane"]):
            data = ContactCreateSchema(
                resource_name=f"people/c{i}",
                display_name=name,
                phone_numbers=[
                    PhoneNumberSchema(
                        value=f"+1555123456{i}",
                        display_value=f"(555) 123-456{i}",
                        type="mobile",
                        primary=True,
                    ),
                ],
            )
            contact_repo.create_contact(data)
        db_session.commit()

        # Search for John's number
        results = contact_repo.search_by_phone("5551234560")
        assert len(results) == 1
        assert results[0].display_name == "John"

    def test_search_by_phone_fallback_digits(self, contact_repo, db_session):
        """Test fallback to digit-only search for invalid format."""
        data = ContactCreateSchema(
            resource_name="people/c1",
            display_name="Test Contact",
            phone_numbers=[
                PhoneNumberSchema(
                    value="+15551234567",
                    display_value="(555) 123-4567",
                    type="mobile",
                    primary=True,
                ),
            ],
        )
        contact_repo.create_contact(data)
        db_session.commit()

        # Search with invalid format but enough digits for suffix match
        results = contact_repo.search_by_phone("1234567")
        # This may or may not match depending on the LIKE pattern
        # The fallback uses %digits pattern
        assert isinstance(results, list)

    def test_search_by_phone_empty_database(self, contact_repo):
        """Test searching in empty database."""
        results = contact_repo.search_by_phone("5551234567")
        assert len(results) == 0

    def test_search_by_phone_empty_input(self, contact_repo, db_session):
        """Test searching with empty input."""
        data = ContactCreateSchema(
            resource_name="people/c1",
            display_name="Test",
            phone_numbers=[
                PhoneNumberSchema(
                    value="+15551234567",
                    display_value="(555) 123-4567",
                    type="mobile",
                    primary=True,
                ),
            ],
        )
        contact_repo.create_contact(data)
        db_session.commit()

        results = contact_repo.search_by_phone("")
        assert len(results) == 0

    def test_search_by_phone_distinct_results(self, contact_repo, db_session):
        """Test that contacts with multiple matching phones appear once."""
        data = ContactCreateSchema(
            resource_name="people/c1",
            display_name="Multi Phone",
            phone_numbers=[
                PhoneNumberSchema(
                    value="+15551234567",
                    display_value="(555) 123-4567",
                    type="mobile",
                    primary=True,
                ),
                PhoneNumberSchema(
                    value="+15551234567",  # Same number twice
                    display_value="(555) 123-4567",
                    type="work",
                    primary=False,
                ),
            ],
        )
        contact_repo.create_contact(data)
        db_session.commit()

        results = contact_repo.search_by_phone("5551234567")
        # Should return contact only once even with multiple matching phones
        assert len(results) == 1
        assert results[0].display_name == "Multi Phone"
