"""Shared test fixtures and configuration.

This module provides common fixtures used across all test modules.
Following pytest best practices, fixtures are organized by scope and purpose.
"""

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from google_contacts_cisco.main import app
from google_contacts_cisco.models import Base, Contact, PhoneNumber, SyncState
from google_contacts_cisco.models.sync_state import SyncStatus

# =============================================================================
# Test Configuration
# =============================================================================


@pytest.fixture(scope="session", autouse=True)
def test_environment():
    """Set up test environment variables."""
    os.environ["TESTING"] = "1"
    yield
    # Cleanup
    if "TESTING" in os.environ:
        del os.environ["TESTING"]


# =============================================================================
# Database Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine.

    Uses SQLite in-memory database for fast, isolated tests.
    Each test gets a fresh database instance.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False,  # Set to True for SQL debugging
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """Create a test database session.

    Provides a clean database session for each test.
    Automatically rolls back transactions after each test.

    Usage:
        def test_example(db_session):
            contact = Contact(...)
            db_session.add(contact)
            db_session.commit()
    """
    TestingSessionLocal = sessionmaker(  # noqa: N806
        autocommit=False, autoflush=False, bind=test_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# =============================================================================
# API Client Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def test_client() -> TestClient:
    """Create a FastAPI test client.

    Provides a test client for making API requests.

    Usage:
        def test_endpoint(test_client):
            response = test_client.get("/health")
            assert response.status_code == 200
    """
    return TestClient(app)


# =============================================================================
# Model Fixtures - Sample Data
# =============================================================================


@pytest.fixture
def sample_contact(db_session) -> Contact:
    """Create a sample contact for testing.

    Returns a committed Contact object with basic fields populated.
    """
    contact = Contact(
        resource_name="people/c12345",
        display_name="John Doe",
        given_name="John",
        family_name="Doe",
        etag="etag123",
        organization="Acme Corp",
        job_title="Software Engineer",
    )
    db_session.add(contact)
    db_session.commit()
    db_session.refresh(contact)
    return contact


@pytest.fixture
def sample_contact_with_phones(db_session) -> Contact:
    """Create a sample contact with multiple phone numbers.

    Returns a Contact with:
    - Primary mobile number: +1-555-0100
    - Work number: +1-555-0101
    """
    contact = Contact(
        resource_name="people/c12345",
        display_name="Jane Smith",
        given_name="Jane",
        family_name="Smith",
    )
    db_session.add(contact)
    db_session.flush()

    mobile = PhoneNumber(
        contact_id=contact.id,
        value="+15550100",
        display_value="+1-555-0100",
        type="mobile",
        primary=True,
    )
    work = PhoneNumber(
        contact_id=contact.id,
        value="+15550101",
        display_value="+1-555-0101",
        type="work",
        primary=False,
    )
    db_session.add_all([mobile, work])
    db_session.commit()
    db_session.refresh(contact)
    return contact


@pytest.fixture
def sample_contacts_batch(db_session) -> list[Contact]:
    """Create a batch of sample contacts for testing.

    Returns a list of 5 contacts with various configurations:
    - Contacts with/without phone numbers
    - Different name combinations
    - Various organizations
    """
    contacts = [
        Contact(
            resource_name=f"people/c{i}",
            display_name=f"Contact {i}",
            given_name=f"First{i}",
            family_name=f"Last{i}",
            organization=f"Company {i % 3}" if i % 2 == 0 else None,
        )
        for i in range(1, 6)
    ]

    for contact in contacts:
        db_session.add(contact)
    db_session.flush()

    # Add phone numbers to some contacts
    for i, contact in enumerate(contacts):
        if i % 2 == 0:  # Even-indexed contacts get phone numbers
            phone = PhoneNumber(
                contact_id=contact.id,
                value=f"+1555010{i}",
                display_value=f"+1-555-010{i}",
                type="mobile",
                primary=True,
            )
            db_session.add(phone)

    db_session.commit()
    for contact in contacts:
        db_session.refresh(contact)
    return contacts


@pytest.fixture
def sample_sync_state(db_session) -> SyncState:
    """Create a sample sync state for testing."""
    sync_state = SyncState(
        sync_token="test_sync_token_123",
        sync_status=SyncStatus.IDLE,
        last_sync_at=datetime.now(timezone.utc),
    )
    db_session.add(sync_state)
    db_session.commit()
    db_session.refresh(sync_state)
    return sync_state


# =============================================================================
# Mock Fixtures - External Services
# =============================================================================


@pytest.fixture
def mock_google_credentials():
    """Create mock Google OAuth credentials.

    Returns a mock credentials object with token and refresh_token.
    Useful for testing OAuth flows without real Google API calls.
    """
    creds = Mock()
    creds.token = "mock_access_token"
    creds.refresh_token = "mock_refresh_token"
    creds.token_uri = "https://oauth2.googleapis.com/token"
    creds.client_id = "mock_client_id"
    creds.client_secret = "mock_client_secret"
    creds.valid = True
    creds.expired = False
    creds.expiry = datetime.now(timezone.utc)
    return creds


@pytest.fixture
def mock_google_people_service():
    """Create a mock Google People API service.

    Returns a mock service object that can be used to test
    Google API interactions without making real API calls.

    Usage:
        def test_google_api(mock_google_people_service):
            service = mock_google_people_service.people().connections().list()
            service.execute.return_value = {...}
    """
    service = Mock()
    # Set up basic mock structure
    service.people.return_value = service
    service.connections.return_value = service
    service.list.return_value = service
    service.execute.return_value = {"connections": [], "nextPageToken": None}
    return service


@pytest.fixture
def sample_google_contact_response():
    """Sample Google People API contact response.

    Returns a dictionary matching the structure of a real
    Google People API contact response for testing parsers.
    """
    return {
        "resourceName": "people/c12345",
        "etag": "etag123",
        "names": [
            {
                "displayName": "John Doe",
                "givenName": "John",
                "familyName": "Doe",
                "metadata": {"primary": True},
            }
        ],
        "phoneNumbers": [
            {
                "value": "+1 555-0100",
                "canonicalForm": "+15550100",
                "type": "mobile",
                "metadata": {"primary": True},
            },
            {
                "value": "(555) 010-1",
                "canonicalForm": "+15550101",
                "type": "work",
                "metadata": {"primary": False},
            },
        ],
        "emailAddresses": [
            {
                "value": "john.doe@example.com",
                "type": "work",
                "metadata": {"primary": True},
            }
        ],
        "organizations": [
            {
                "name": "Acme Corp",
                "title": "Software Engineer",
                "metadata": {"primary": True},
            }
        ],
    }


# =============================================================================
# Temporary Directory Fixtures
# =============================================================================


@pytest.fixture
def temp_test_dir(tmp_path) -> Path:
    """Create a temporary directory for test files.

    Returns a Path object to a temporary directory.
    The directory is automatically cleaned up after the test.

    Usage:
        def test_file_operations(temp_test_dir):
            test_file = temp_test_dir / "test.txt"
            test_file.write_text("test content")
    """
    return tmp_path


@pytest.fixture
def temp_token_file(tmp_path) -> Path:
    """Create a temporary token file path for testing OAuth.

    Returns a Path to a non-existent token file in a temp directory.
    Useful for testing token storage without affecting real files.
    """
    token_file = tmp_path / "test_token.json"
    return token_file


# =============================================================================
# Test Markers and Configuration
# =============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


# =============================================================================
# Utility Functions for Tests
# =============================================================================


def create_test_contact(
    db_session: Session,
    resource_name: str = None,
    display_name: str = "Test Contact",
    **kwargs,
) -> Contact:
    """Helper function to create test contacts with custom fields.

    Args:
        db_session: Database session
        resource_name: Google resource name (auto-generated if None)
        display_name: Contact display name
        **kwargs: Additional contact fields

    Returns:
        Created and committed Contact object
    """
    if resource_name is None:
        resource_name = f"people/{uuid.uuid4().hex[:10]}"

    contact = Contact(
        resource_name=resource_name,
        display_name=display_name,
        **kwargs,
    )
    db_session.add(contact)
    db_session.commit()
    db_session.refresh(contact)
    return contact


def create_test_phone(
    db_session: Session,
    contact: Contact,
    value: str = "+15550100",
    **kwargs,
) -> PhoneNumber:
    """Helper function to create test phone numbers.

    Args:
        db_session: Database session
        contact: Contact to attach phone number to
        value: Phone number value
        **kwargs: Additional phone number fields

    Returns:
        Created and committed PhoneNumber object
    """
    phone = PhoneNumber(
        contact_id=contact.id,
        value=value,
        display_value=kwargs.pop("display_value", value),
        **kwargs,
    )
    db_session.add(phone)
    db_session.commit()
    db_session.refresh(phone)
    return phone
