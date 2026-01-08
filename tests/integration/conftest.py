"""Integration test fixtures and configuration.

This module provides fixtures specifically for integration testing,
building on top of the base fixtures from the main conftest.py.
"""

import os
from datetime import datetime, timezone
from typing import Generator
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from google_contacts_cisco.main import app
from google_contacts_cisco.models import get_db
from google_contacts_cisco.models import Base, Contact, PhoneNumber, SyncState
from google_contacts_cisco.models.sync_state import SyncStatus


# =============================================================================
# Integration Database Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def integration_db(test_engine) -> Generator[Session, None, None]:
    """Create an integration test database session.
    
    Reuses the test_engine from base conftest and provides a database session
    that is used for integration tests.
    """
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def integration_client(test_engine) -> TestClient:
    """Create a FastAPI test client with integrated database.
    
    This client uses the test database for all requests,
    allowing tests to verify end-to-end workflows.
    """
    # Create a session factory
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# =============================================================================
# Mock Google API Fixtures
# =============================================================================


@pytest.fixture
def mock_google_api_responses():
    """Comprehensive mock Google API responses for integration testing."""
    return {
        "connections_list_page1": {
            "connections": [
                {
                    "resourceName": "people/c1",
                    "etag": "etag1",
                    "names": [
                        {
                            "displayName": "Alice Johnson",
                            "givenName": "Alice",
                            "familyName": "Johnson",
                            "metadata": {"primary": True},
                        }
                    ],
                    "phoneNumbers": [
                        {
                            "value": "+1 555-0101",
                            "canonicalForm": "+15550101",
                            "type": "mobile",
                            "metadata": {"primary": True},
                        }
                    ],
                },
                {
                    "resourceName": "people/c2",
                    "etag": "etag2",
                    "names": [
                        {
                            "displayName": "Bob Smith",
                            "givenName": "Bob",
                            "familyName": "Smith",
                            "metadata": {"primary": True},
                        }
                    ],
                    "phoneNumbers": [
                        {
                            "value": "+1 555-0102",
                            "canonicalForm": "+15550102",
                            "type": "work",
                            "metadata": {"primary": True},
                        }
                    ],
                },
            ],
            "nextPageToken": "token_page2",
        },
        "connections_list_page2": {
            "connections": [
                {
                    "resourceName": "people/c3",
                    "etag": "etag3",
                    "names": [
                        {
                            "displayName": "Carol White",
                            "givenName": "Carol",
                            "familyName": "White",
                            "metadata": {"primary": True},
                        }
                    ],
                },
            ],
            "nextPageToken": None,
        },
        "sync_response": {
            "connections": [
                {
                    "resourceName": "people/c1",
                    "etag": "etag1_updated",
                    "names": [
                        {
                            "displayName": "Alice Johnson Updated",
                            "givenName": "Alice",
                            "familyName": "Johnson",
                            "metadata": {"primary": True},
                        }
                    ],
                }
            ],
            "nextSyncToken": "new_sync_token",
        },
        "empty_response": {
            "connections": [],
            "nextPageToken": None,
        },
    }


@pytest.fixture
def mock_google_client_service(mock_google_api_responses):
    """Mock Google People API client service for integration tests.
    
    Simulates the Google People API with realistic responses.
    """
    service = Mock()
    
    # Track call count for pagination
    call_count = {"list_calls": 0}
    
    def list_side_effect(*args, **kwargs):
        """Simulate paginated list responses."""
        call_count["list_calls"] += 1
        if call_count["list_calls"] == 1:
            return mock_google_api_responses["connections_list_page1"]
        elif call_count["list_calls"] == 2:
            return mock_google_api_responses["connections_list_page2"]
        else:
            return mock_google_api_responses["empty_response"]
    
    # Mock the service structure
    service.people().connections().list().execute.side_effect = list_side_effect
    service.people().connections().sync().execute.return_value = mock_google_api_responses["sync_response"]
    
    return service


# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def integration_test_contacts(integration_db) -> list[Contact]:
    """Create a set of test contacts in the integration database."""
    contacts = []
    
    # Contact with full data
    contact1 = Contact(
        resource_name="people/test1",
        display_name="Integration Test User 1",
        given_name="Integration",
        family_name="User1",
        etag="etag_test1",
        organization="Test Corp",
        job_title="Engineer",
    )
    integration_db.add(contact1)
    integration_db.flush()
    
    phone1 = PhoneNumber(
        contact_id=contact1.id,
        value="+15551001",
        display_value="+1-555-1001",
        type="mobile",
        primary=True,
    )
    integration_db.add(phone1)
    contacts.append(contact1)
    
    # Contact with minimal data
    contact2 = Contact(
        resource_name="people/test2",
        display_name="Test User 2",
    )
    integration_db.add(contact2)
    contacts.append(contact2)
    
    # Contact with multiple phones
    contact3 = Contact(
        resource_name="people/test3",
        display_name="Test User 3",
        given_name="Test",
        family_name="User3",
    )
    integration_db.add(contact3)
    integration_db.flush()
    
    for i, phone_type in enumerate(["mobile", "work", "home"]):
        phone = PhoneNumber(
            contact_id=contact3.id,
            value=f"+1555200{i}",
            display_value=f"+1-555-200{i}",
            type=phone_type,
            primary=(i == 0),
        )
        integration_db.add(phone)
    contacts.append(contact3)
    
    integration_db.commit()
    for contact in contacts:
        integration_db.refresh(contact)
    
    return contacts


@pytest.fixture
def integration_sync_state(integration_db) -> SyncState:
    """Create a sync state for integration testing."""
    sync_state = SyncState(
        sync_token="integration_sync_token",
        sync_status=SyncStatus.IDLE,
        last_sync_at=datetime.now(timezone.utc),
    )
    integration_db.add(sync_state)
    integration_db.commit()
    integration_db.refresh(sync_state)
    return sync_state


# =============================================================================
# OAuth Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_oauth_flow():
    """Mock OAuth flow for integration testing."""
    mock_flow = Mock()
    mock_flow.authorization_url.return_value = (
        "https://accounts.google.com/o/oauth2/auth?mock=true",
        "mock_state",
    )
    
    mock_credentials = Mock()
    mock_credentials.token = "mock_access_token"
    mock_credentials.refresh_token = "mock_refresh_token"
    mock_credentials.valid = True
    mock_credentials.expired = False
    
    mock_flow.fetch_token.return_value = None
    mock_flow.credentials = mock_credentials
    
    return mock_flow


@pytest.fixture
def mock_credentials():
    """Mock Google credentials for integration testing."""
    creds = Mock()
    creds.token = "integration_test_token"
    creds.refresh_token = "integration_test_refresh_token"
    creds.token_uri = "https://oauth2.googleapis.com/token"
    creds.client_id = "test_client_id"
    creds.client_secret = "test_client_secret"
    creds.valid = True
    creds.expired = False
    creds.expiry = datetime.now(timezone.utc)
    return creds


# =============================================================================
# Environment Configuration
# =============================================================================


@pytest.fixture(autouse=True)
def integration_test_env():
    """Set up environment for integration tests."""
    original_env = os.environ.copy()
    
    # Set test environment variables
    os.environ["TESTING"] = "1"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["GOOGLE_CLIENT_ID"] = "test_client_id"
    os.environ["GOOGLE_CLIENT_SECRET"] = "test_client_secret"
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
