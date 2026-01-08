"""Unit tests for search API routes.

This module tests the search endpoints including
contact search by name, phone, and combined queries.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from google_contacts_cisco.main import app
from google_contacts_cisco.models.contact import Contact
from google_contacts_cisco.models.phone_number import PhoneNumber


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    return Mock()


@pytest.fixture
def sample_contact():
    """Create a sample contact for testing."""
    contact = Contact(
        id=uuid.uuid4(),
        resource_name="people/c123",
        display_name="John Doe",
        given_name="John",
        family_name="Doe",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        deleted=False,
    )
    phone = PhoneNumber(
        id=uuid.uuid4(),
        contact_id=contact.id,
        value="+12025551234",
        display_value="(202) 555-1234",
        type="mobile",
        primary=True,
    )
    contact.phone_numbers = [phone]
    return contact


@pytest.fixture
def sample_contacts():
    """Create multiple sample contacts for testing."""
    contacts = []
    
    # Contact 1: John Doe
    contact1 = Contact(
        id=uuid.uuid4(),
        resource_name="people/c1",
        display_name="John Doe",
        given_name="John",
        family_name="Doe",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        deleted=False,
    )
    phone1 = PhoneNumber(
        id=uuid.uuid4(),
        contact_id=contact1.id,
        value="+12025551234",
        display_value="(202) 555-1234",
        type="mobile",
        primary=True,
    )
    contact1.phone_numbers = [phone1]
    contacts.append(contact1)
    
    # Contact 2: Jane Smith
    contact2 = Contact(
        id=uuid.uuid4(),
        resource_name="people/c2",
        display_name="Jane Smith",
        given_name="Jane",
        family_name="Smith",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        deleted=False,
    )
    phone2 = PhoneNumber(
        id=uuid.uuid4(),
        contact_id=contact2.id,
        value="+13105559876",
        display_value="(310) 555-9876",
        type="work",
        primary=True,
    )
    contact2.phone_numbers = [phone2]
    contacts.append(contact2)
    
    return contacts


class TestSearchContacts:
    """Tests for /api/contacts/search endpoint."""

    @patch("google_contacts_cisco.api.search_routes.get_db")
    @patch("google_contacts_cisco.api.search_routes.get_search_service")
    def test_search_contacts_success(
        self, mock_get_service, mock_get_db, client, sample_contacts
    ):
        """Should return search results successfully."""
        # Setup mocks
        mock_service = Mock()
        mock_service.search_contacts.return_value = sample_contacts
        mock_service.count_search_results.return_value = 2
        mock_get_service.return_value = mock_service
        mock_get_db.return_value = Mock()

        # Make request
        response = client.get("/api/contacts/search?q=John")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total_count" in data
        assert data["total_count"] == 2
        assert len(data["results"]) == 2
        assert data["has_more"] is False

    @patch("google_contacts_cisco.api.search_routes.get_db")
    @patch("google_contacts_cisco.api.search_routes.get_search_service")
    def test_search_contacts_with_pagination(
        self, mock_get_service, mock_get_db, client, sample_contacts
    ):
        """Should handle pagination parameters."""
        # Setup mocks
        mock_service = Mock()
        mock_service.search_contacts.return_value = [sample_contacts[0]]
        mock_service.count_search_results.return_value = 10
        mock_get_service.return_value = mock_service
        mock_get_db.return_value = Mock()

        # Make request with pagination
        response = client.get("/api/contacts/search?q=John&limit=1&offset=0")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 1
        assert data["offset"] == 0
        assert data["has_more"] is True  # 0 + 1 < 10
        assert len(data["results"]) == 1

    @patch("google_contacts_cisco.api.search_routes.get_db")
    @patch("google_contacts_cisco.api.search_routes.get_search_service")
    def test_search_contacts_without_phone_search(
        self, mock_get_service, mock_get_db, client
    ):
        """Should support disabling phone search."""
        # Setup mocks
        mock_service = Mock()
        mock_service.search_contacts.return_value = []
        mock_service.count_search_results.return_value = 0
        mock_get_service.return_value = mock_service
        mock_get_db.return_value = Mock()

        # Make request
        response = client.get(
            "/api/contacts/search?q=5551234&include_phone_search=false"
        )

        # Assert
        assert response.status_code == 200
        mock_service.search_contacts.assert_called_once()
        call_kwargs = mock_service.search_contacts.call_args.kwargs
        assert call_kwargs["include_phone_search"] is False

    def test_search_contacts_missing_query(self, client):
        """Should return 422 for missing query parameter."""
        response = client.get("/api/contacts/search")
        assert response.status_code == 422

    def test_search_contacts_empty_query(self, client):
        """Should return 422 for empty query."""
        response = client.get("/api/contacts/search?q=")
        assert response.status_code == 422

    def test_search_contacts_invalid_limit(self, client):
        """Should return 422 for invalid limit."""
        response = client.get("/api/contacts/search?q=test&limit=0")
        assert response.status_code == 422
        
        response = client.get("/api/contacts/search?q=test&limit=101")
        assert response.status_code == 422

    def test_search_contacts_invalid_offset(self, client):
        """Should return 422 for invalid offset."""
        response = client.get("/api/contacts/search?q=test&offset=-1")
        assert response.status_code == 422

    @patch("google_contacts_cisco.api.search_routes.get_db")
    @patch("google_contacts_cisco.api.search_routes.get_search_service")
    def test_search_contacts_service_error(
        self, mock_get_service, mock_get_db, client
    ):
        """Should return 500 on service error."""
        # Setup mocks to raise exception
        mock_service = Mock()
        mock_service.search_contacts.side_effect = Exception("Database error")
        mock_get_service.return_value = mock_service
        mock_get_db.return_value = Mock()

        # Make request
        response = client.get("/api/contacts/search?q=test")

        # Assert
        assert response.status_code == 500
        assert "Search failed" in response.json()["detail"]


class TestSearchContactsByName:
    """Tests for /api/contacts/search/by-name endpoint."""

    @patch("google_contacts_cisco.api.search_routes.get_db")
    @patch("google_contacts_cisco.api.search_routes.get_search_service")
    def test_search_by_name_success(
        self, mock_get_service, mock_get_db, client, sample_contacts
    ):
        """Should search by name only."""
        # Setup mocks
        mock_service = Mock()
        mock_service.search_by_name.return_value = sample_contacts
        mock_service.count_search_results.return_value = 2
        mock_get_service.return_value = mock_service
        mock_get_db.return_value = Mock()

        # Make request
        response = client.get("/api/contacts/search/by-name?q=Smith")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        mock_service.search_by_name.assert_called_once()

    @patch("google_contacts_cisco.api.search_routes.get_db")
    @patch("google_contacts_cisco.api.search_routes.get_search_service")
    def test_search_by_name_with_pagination(
        self, mock_get_service, mock_get_db, client, sample_contacts
    ):
        """Should handle pagination for name search."""
        # Setup mocks
        mock_service = Mock()
        mock_service.search_by_name.return_value = [sample_contacts[0]]
        mock_service.count_search_results.return_value = 5
        mock_get_service.return_value = mock_service
        mock_get_db.return_value = Mock()

        # Make request
        response = client.get("/api/contacts/search/by-name?q=John&limit=1&offset=2")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 1
        assert data["offset"] == 2
        mock_service.search_by_name.assert_called_once_with(
            query="John",
            limit=1,
            offset=2,
        )

    def test_search_by_name_missing_query(self, client):
        """Should return 422 for missing query."""
        response = client.get("/api/contacts/search/by-name")
        assert response.status_code == 422


class TestSearchContactsByPhone:
    """Tests for /api/contacts/search/by-phone endpoint."""

    @patch("google_contacts_cisco.api.search_routes.get_db")
    @patch("google_contacts_cisco.api.search_routes.get_search_service")
    def test_search_by_phone_success(
        self, mock_get_service, mock_get_db, client, sample_contact
    ):
        """Should search by phone number."""
        # Setup mocks
        mock_service = Mock()
        mock_service.search_by_phone.return_value = [sample_contact]
        mock_get_service.return_value = mock_service
        mock_get_db.return_value = Mock()

        # Make request
        response = client.get("/api/contacts/search/by-phone?q=2025551234")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["display_name"] == "John Doe"

    @patch("google_contacts_cisco.api.search_routes.get_db")
    @patch("google_contacts_cisco.api.search_routes.get_search_service")
    def test_search_by_phone_formatted(
        self, mock_get_service, mock_get_db, client, sample_contact
    ):
        """Should handle formatted phone numbers."""
        # Setup mocks
        mock_service = Mock()
        mock_service.search_by_phone.return_value = [sample_contact]
        mock_get_service.return_value = mock_service
        mock_get_db.return_value = Mock()

        # Make request with formatted number
        response = client.get("/api/contacts/search/by-phone?q=(202)%20555-1234")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1

    def test_search_by_phone_too_short(self, client):
        """Should return 422 for too short phone number."""
        response = client.get("/api/contacts/search/by-phone?q=123")
        assert response.status_code == 422

    def test_search_by_phone_missing_query(self, client):
        """Should return 422 for missing query."""
        response = client.get("/api/contacts/search/by-phone")
        assert response.status_code == 422


class TestGetContact:
    """Tests for /api/contacts/{contact_id} endpoint."""

    @patch("google_contacts_cisco.api.search_routes.get_db")
    @patch("google_contacts_cisco.api.search_routes.ContactRepository")
    def test_get_contact_success(
        self, mock_repo_class, mock_get_db, client, sample_contact
    ):
        """Should return contact by ID."""
        # Setup mocks
        mock_repo = Mock()
        mock_repo.get_by_id.return_value = sample_contact
        mock_repo_class.return_value = mock_repo
        mock_get_db.return_value = Mock()

        # Make request
        response = client.get(f"/api/contacts/{sample_contact.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_contact.id)
        assert data["display_name"] == "John Doe"
        assert "created_at" in data
        assert "updated_at" in data
        assert len(data["phone_numbers"]) == 1

    @patch("google_contacts_cisco.api.search_routes.get_db")
    @patch("google_contacts_cisco.api.search_routes.ContactRepository")
    def test_get_contact_not_found(self, mock_repo_class, mock_get_db, client):
        """Should return 404 for non-existent contact."""
        # Setup mocks
        mock_repo = Mock()
        mock_repo.get_by_id.return_value = None
        mock_repo_class.return_value = mock_repo
        mock_get_db.return_value = Mock()

        # Make request
        contact_id = uuid.uuid4()
        response = client.get(f"/api/contacts/{contact_id}")

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @patch("google_contacts_cisco.api.search_routes.get_db")
    @patch("google_contacts_cisco.api.search_routes.ContactRepository")
    def test_get_contact_deleted(self, mock_repo_class, mock_get_db, client):
        """Should return 404 for deleted contact."""
        # Setup mocks
        deleted_contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/c999",
            display_name="Deleted Contact",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            deleted=True,  # Marked as deleted
        )
        deleted_contact.phone_numbers = []
        
        mock_repo = Mock()
        mock_repo.get_by_id.return_value = deleted_contact
        mock_repo_class.return_value = mock_repo
        mock_get_db.return_value = Mock()

        # Make request
        response = client.get(f"/api/contacts/{deleted_contact.id}")

        # Assert
        assert response.status_code == 404

    def test_get_contact_invalid_uuid(self, client):
        """Should return 422 for invalid UUID."""
        response = client.get("/api/contacts/not-a-uuid")
        assert response.status_code == 422


class TestListContacts:
    """Tests for /api/contacts (list) endpoint."""

    @patch("google_contacts_cisco.api.search_routes.get_db")
    @patch("google_contacts_cisco.api.search_routes.ContactRepository")
    def test_list_contacts_success(
        self, mock_repo_class, mock_get_db, client, sample_contacts
    ):
        """Should list all contacts with pagination."""
        # Setup mocks
        mock_repo = Mock()
        mock_repo.list_contacts.return_value = sample_contacts
        mock_repo.count_contacts.return_value = 2
        mock_repo_class.return_value = mock_repo
        mock_get_db.return_value = Mock()

        # Make request
        response = client.get("/api/contacts")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        assert data["total_count"] == 2
        assert data["limit"] == 50  # Default limit
        assert data["offset"] == 0  # Default offset

    @patch("google_contacts_cisco.api.search_routes.get_db")
    @patch("google_contacts_cisco.api.search_routes.ContactRepository")
    def test_list_contacts_with_pagination(
        self, mock_repo_class, mock_get_db, client, sample_contacts
    ):
        """Should handle pagination parameters."""
        # Setup mocks
        mock_repo = Mock()
        mock_repo.list_contacts.return_value = [sample_contacts[0]]
        mock_repo.count_contacts.return_value = 10
        mock_repo_class.return_value = mock_repo
        mock_get_db.return_value = Mock()

        # Make request
        response = client.get("/api/contacts?limit=1&offset=5")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 1
        assert data["offset"] == 5
        assert data["has_more"] is True  # 5 + 1 < 10
        mock_repo.list_contacts.assert_called_once_with(
            limit=1,
            offset=5,
            include_deleted=False,
        )

    @patch("google_contacts_cisco.api.search_routes.get_db")
    @patch("google_contacts_cisco.api.search_routes.ContactRepository")
    def test_list_contacts_empty_result(
        self, mock_repo_class, mock_get_db, client
    ):
        """Should handle empty contact list."""
        # Setup mocks
        mock_repo = Mock()
        mock_repo.list_contacts.return_value = []
        mock_repo.count_contacts.return_value = 0
        mock_repo_class.return_value = mock_repo
        mock_get_db.return_value = Mock()

        # Make request
        response = client.get("/api/contacts")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 0
        assert data["total_count"] == 0
        assert data["has_more"] is False

    def test_list_contacts_invalid_parameters(self, client):
        """Should validate pagination parameters."""
        # Invalid limit
        response = client.get("/api/contacts?limit=0")
        assert response.status_code == 422
        
        # Limit too high
        response = client.get("/api/contacts?limit=101")
        assert response.status_code == 422
        
        # Negative offset
        response = client.get("/api/contacts?offset=-1")
        assert response.status_code == 422


class TestResponseModels:
    """Tests for response model serialization."""

    @patch("google_contacts_cisco.api.search_routes.get_db")
    @patch("google_contacts_cisco.api.search_routes.get_search_service")
    def test_contact_response_format(
        self, mock_get_service, mock_get_db, client, sample_contact
    ):
        """Should format contact response correctly."""
        # Setup mocks
        mock_service = Mock()
        mock_service.search_contacts.return_value = [sample_contact]
        mock_service.count_search_results.return_value = 1
        mock_get_service.return_value = mock_service
        mock_get_db.return_value = Mock()

        # Make request
        response = client.get("/api/contacts/search?q=John")

        # Assert
        assert response.status_code == 200
        data = response.json()
        contact_data = data["results"][0]
        
        # Check all required fields
        assert "id" in contact_data
        assert "resource_name" in contact_data
        assert "display_name" in contact_data
        assert "given_name" in contact_data
        assert "family_name" in contact_data
        assert "phone_numbers" in contact_data
        
        # Check phone number format
        if contact_data["phone_numbers"]:
            phone = contact_data["phone_numbers"][0]
            assert "id" in phone
            assert "value" in phone
            assert "display_value" in phone
            assert "type" in phone
            assert "primary" in phone

    @patch("google_contacts_cisco.api.search_routes.get_db")
    @patch("google_contacts_cisco.api.search_routes.get_search_service")
    def test_search_response_pagination_fields(
        self, mock_get_service, mock_get_db, client, sample_contacts
    ):
        """Should include all pagination fields in response."""
        # Setup mocks
        mock_service = Mock()
        mock_service.search_contacts.return_value = sample_contacts
        mock_service.count_search_results.return_value = 5
        mock_get_service.return_value = mock_service
        mock_get_db.return_value = Mock()

        # Make request
        response = client.get("/api/contacts/search?q=test&limit=2&offset=1")

        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert "results" in data
        assert "total_count" in data
        assert "limit" in data
        assert "offset" in data
        assert "has_more" in data
        
        assert data["total_count"] == 5
        assert data["limit"] == 2
        assert data["offset"] == 1
        assert data["has_more"] is True  # 1 + 2 < 5


class TestErrorHandling:
    """Tests for error handling in search endpoints."""

    @patch("google_contacts_cisco.api.search_routes.get_db")
    @patch("google_contacts_cisco.api.search_routes.get_search_service")
    def test_search_service_raises_exception(
        self, mock_get_service, mock_get_db, client
    ):
        """Should handle service exceptions gracefully."""
        # Setup mock to raise exception
        mock_service = Mock()
        mock_service.search_contacts.side_effect = RuntimeError("Test error")
        mock_get_service.return_value = mock_service
        mock_get_db.return_value = Mock()

        # Make request
        response = client.get("/api/contacts/search?q=test")

        # Assert
        assert response.status_code == 500
        assert "detail" in response.json()

    @patch("google_contacts_cisco.api.search_routes.get_db")
    @patch("google_contacts_cisco.api.search_routes.ContactRepository")
    def test_get_contact_repository_error(
        self, mock_repo_class, mock_get_db, client
    ):
        """Should handle repository errors."""
        # Setup mock to raise exception
        mock_repo = Mock()
        mock_repo.get_by_id.side_effect = RuntimeError("Database error")
        mock_repo_class.return_value = mock_repo
        mock_get_db.return_value = Mock()

        # Make request
        contact_id = uuid.uuid4()
        response = client.get(f"/api/contacts/{contact_id}")

        # Assert
        assert response.status_code == 500
        assert "Failed to retrieve contact" in response.json()["detail"]
