"""Test Search API Endpoints.

This module tests the FastAPI endpoints for contact search.
These are unit tests that mock the search service to test the API layer in isolation.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from google_contacts_cisco.main import app
from google_contacts_cisco.models.contact import Contact
from google_contacts_cisco.models.phone_number import PhoneNumber


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_contact():
    """Create a sample contact for testing."""
    contact = Contact(
        id="test-id-123",
        resource_name="people/abc123",
        display_name="John Doe",
        given_name="John",
        family_name="Doe",
        deleted=False,
    )
    
    # Add phone numbers
    contact.phone_numbers = [
        PhoneNumber(
            value="+15551234567",
            display_value="(555) 123-4567",
            type="mobile",
            primary=True,
        ),
        PhoneNumber(
            value="+15559876543",
            display_value="(555) 987-6543",
            type="work",
            primary=False,
        ),
    ]
    
    return contact


class TestGeneralSearchEndpoint:
    """Test GET /api/search endpoint."""

    @patch("google_contacts_cisco.api.search.get_search_service")
    def test_search_with_results(
        self, mock_get_service, client, sample_contact
    ):
        """Test search with matching results."""
        mock_service = Mock()
        mock_service.search_contacts.return_value = [sample_contact]
        mock_service.count_search_results.return_value = 1
        mock_get_service.return_value = mock_service

        response = client.get("/api/search?q=John")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["total_count"] == 1
        assert data["query"] == "John"
        assert len(data["results"]) == 1
        assert data["results"][0]["display_name"] == "John Doe"
        assert data["results"][0]["given_name"] == "John"
        assert data["results"][0]["family_name"] == "Doe"
        assert data["results"][0]["resource_name"] == "people/abc123"
        assert len(data["results"][0]["phone_numbers"]) == 2
        assert data["results"][0]["phone_numbers"][0]["value"] == "+15551234567"
        assert data["results"][0]["phone_numbers"][0]["primary"] is True
        assert "elapsed_ms" in data
        assert data["limit"] == 50
        assert data["offset"] == 0

        # Verify search service was called correctly
        mock_service.search_contacts.assert_called_once_with(
            query="John",
            limit=50,
            offset=0,
        )
        mock_service.count_search_results.assert_called_once_with(query="John")

    @patch("google_contacts_cisco.api.search.get_search_service")
    def test_search_no_results(self, mock_get_service, client):
        """Test search with no matching results."""
        mock_service = Mock()
        mock_service.search_contacts.return_value = []
        mock_service.count_search_results.return_value = 0
        mock_get_service.return_value = mock_service

        response = client.get("/api/search?q=NonExistent")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["total_count"] == 0
        assert data["results"] == []
        assert data["query"] == "NonExistent"

    @patch("google_contacts_cisco.api.search.get_search_service")
    def test_search_with_pagination(
        self, mock_get_service, client, sample_contact
    ):
        """Test search with pagination parameters."""
        mock_service = Mock()
        mock_service.search_contacts.return_value = [sample_contact]
        mock_service.count_search_results.return_value = 100
        mock_get_service.return_value = mock_service

        response = client.get("/api/search?q=John&limit=10&offset=20")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["total_count"] == 100
        assert data["limit"] == 10
        assert data["offset"] == 20

        # Verify pagination parameters were passed
        mock_service.search_contacts.assert_called_once_with(
            query="John",
            limit=10,
            offset=20,
        )

    def test_search_missing_query(self, client):
        """Test search fails without query parameter."""
        response = client.get("/api/search")

        assert response.status_code == 422  # Validation error

    def test_search_empty_query(self, client):
        """Test search fails with empty query."""
        response = client.get("/api/search?q=")

        assert response.status_code == 422  # Validation error

    def test_search_limit_too_low(self, client):
        """Test search validates minimum limit."""
        response = client.get("/api/search?q=test&limit=0")

        assert response.status_code == 422

    def test_search_limit_too_high(self, client):
        """Test search validates maximum limit."""
        response = client.get("/api/search?q=test&limit=101")

        assert response.status_code == 422

    def test_search_negative_offset(self, client):
        """Test search validates non-negative offset."""
        response = client.get("/api/search?q=test&offset=-1")

        assert response.status_code == 422

    @patch("google_contacts_cisco.api.search.get_search_service")
    def test_search_with_phone_number_query(
        self, mock_get_service, client, sample_contact
    ):
        """Test search with phone number as query."""
        mock_service = Mock()
        mock_service.search_contacts.return_value = [sample_contact]
        mock_service.count_search_results.return_value = 1
        mock_get_service.return_value = mock_service

        response = client.get("/api/search?q=555-123-4567")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["query"] == "555-123-4567"

    @patch("google_contacts_cisco.api.search.get_search_service")
    def test_search_with_special_characters(
        self, mock_get_service, client
    ):
        """Test search handles special characters safely."""
        mock_service = Mock()
        mock_service.search_contacts.return_value = []
        mock_service.count_search_results.return_value = 0
        mock_get_service.return_value = mock_service

        response = client.get("/api/search?q=O%27Brien")  # O'Brien encoded

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "O'Brien"

    @patch("google_contacts_cisco.api.search.get_search_service")
    def test_search_service_error(self, mock_get_service, client):
        """Test search handles service errors gracefully."""
        mock_service = Mock()
        mock_service.search_contacts.side_effect = Exception("Database error")
        mock_get_service.return_value = mock_service

        response = client.get("/api/search?q=test")

        assert response.status_code == 500
        data = response.json()
        assert "Database error" in data["detail"]

    @patch("google_contacts_cisco.api.search.get_search_service")
    def test_search_value_error(self, mock_get_service, client):
        """Test search handles ValueError from service."""
        mock_service = Mock()
        mock_service.search_contacts.side_effect = ValueError("Invalid parameter")
        mock_get_service.return_value = mock_service

        response = client.get("/api/search?q=test")

        assert response.status_code == 422
        data = response.json()
        assert "Invalid parameter" in data["detail"]

    @patch("google_contacts_cisco.api.search.get_search_service")
    def test_search_with_multiple_contacts(
        self, mock_get_service, client, sample_contact
    ):
        """Test search returns multiple contacts."""
        contact2 = Contact(
            id="test-id-456",
            resource_name="people/def456",
            display_name="Jane Smith",
            given_name="Jane",
            family_name="Smith",
            deleted=False,
        )
        contact2.phone_numbers = []

        mock_service = Mock()
        mock_service.search_contacts.return_value = [sample_contact, contact2]
        mock_service.count_search_results.return_value = 2
        mock_get_service.return_value = mock_service

        response = client.get("/api/search?q=test")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["total_count"] == 2
        assert len(data["results"]) == 2
        assert data["results"][0]["display_name"] == "John Doe"
        assert data["results"][1]["display_name"] == "Jane Smith"


class TestSearchByNameEndpoint:
    """Test GET /api/search/name endpoint."""

    @patch("google_contacts_cisco.api.search.get_search_service")
    def test_search_by_name_with_results(
        self, mock_get_service, client, sample_contact
    ):
        """Test name search with matching results."""
        mock_service = Mock()
        mock_service.search_by_name.return_value = [sample_contact]
        mock_service.count_search_results.return_value = 1
        mock_get_service.return_value = mock_service

        response = client.get("/api/search/name?q=John")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["total_count"] == 1
        assert data["query"] == "John"
        assert data["results"][0]["display_name"] == "John Doe"

        # Verify name search was called
        mock_service.search_by_name.assert_called_once_with(
            query="John",
            limit=50,
            offset=0,
        )
        # Verify count was called without phone search
        mock_service.count_search_results.assert_called_once_with(
            query="John",
            include_phone_search=False,
        )

    @patch("google_contacts_cisco.api.search.get_search_service")
    def test_search_by_name_no_results(self, mock_get_service, client):
        """Test name search with no results."""
        mock_service = Mock()
        mock_service.search_by_name.return_value = []
        mock_service.count_search_results.return_value = 0
        mock_get_service.return_value = mock_service

        response = client.get("/api/search/name?q=NonExistent")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["results"] == []

    @patch("google_contacts_cisco.api.search.get_search_service")
    def test_search_by_name_with_pagination(
        self, mock_get_service, client, sample_contact
    ):
        """Test name search with pagination."""
        mock_service = Mock()
        mock_service.search_by_name.return_value = [sample_contact]
        mock_service.count_search_results.return_value = 50
        mock_get_service.return_value = mock_service

        response = client.get("/api/search/name?q=John&limit=25&offset=10")

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 25
        assert data["offset"] == 10

        mock_service.search_by_name.assert_called_once_with(
            query="John",
            limit=25,
            offset=10,
        )

    def test_search_by_name_missing_query(self, client):
        """Test name search fails without query."""
        response = client.get("/api/search/name")

        assert response.status_code == 422

    def test_search_by_name_empty_query(self, client):
        """Test name search fails with empty query."""
        response = client.get("/api/search/name?q=")

        assert response.status_code == 422

    @patch("google_contacts_cisco.api.search.get_search_service")
    def test_search_by_name_service_error(self, mock_get_service, client):
        """Test name search handles service errors."""
        mock_service = Mock()
        mock_service.search_by_name.side_effect = Exception("Service error")
        mock_get_service.return_value = mock_service

        response = client.get("/api/search/name?q=test")

        assert response.status_code == 500
        data = response.json()
        assert "Service error" in data["detail"]


class TestSearchByPhoneEndpoint:
    """Test GET /api/search/phone endpoint."""

    @patch("google_contacts_cisco.api.search.get_search_service")
    def test_search_by_phone_with_results(
        self, mock_get_service, client, sample_contact
    ):
        """Test phone search with matching results."""
        mock_service = Mock()
        mock_service.search_by_phone.return_value = [sample_contact]
        mock_get_service.return_value = mock_service

        response = client.get("/api/search/phone?q=555-123-4567")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["total_count"] == 1  # Same as count for phone search
        assert data["query"] == "555-123-4567"
        assert data["results"][0]["display_name"] == "John Doe"
        assert len(data["results"][0]["phone_numbers"]) == 2

        # Verify phone search was called
        mock_service.search_by_phone.assert_called_once_with(
            phone_number="555-123-4567",
            limit=50,
            offset=0,
        )

    @patch("google_contacts_cisco.api.search.get_search_service")
    def test_search_by_phone_no_results(self, mock_get_service, client):
        """Test phone search with no results."""
        mock_service = Mock()
        mock_service.search_by_phone.return_value = []
        mock_get_service.return_value = mock_service

        response = client.get("/api/search/phone?q=999-999-9999")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["results"] == []

    @patch("google_contacts_cisco.api.search.get_search_service")
    def test_search_by_phone_various_formats(
        self, mock_get_service, client, sample_contact
    ):
        """Test phone search handles various phone formats."""
        from urllib.parse import quote
        
        mock_service = Mock()
        mock_service.search_by_phone.return_value = [sample_contact]
        mock_get_service.return_value = mock_service

        # Test different phone number formats
        # Format: (input, expected_query_in_response)
        formats = [
            ("5551234567", "5551234567"),
            ("(555) 123-4567", "(555) 123-4567"),
            ("+1-555-123-4567", " 1-555-123-4567"),  # + is decoded as space in query params
            ("555.123.4567", "555.123.4567"),
        ]

        for phone_format, expected_query in formats:
            response = client.get(f"/api/search/phone?q={phone_format}")
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == expected_query

    @patch("google_contacts_cisco.api.search.get_search_service")
    def test_search_by_phone_with_pagination(
        self, mock_get_service, client, sample_contact
    ):
        """Test phone search with pagination."""
        mock_service = Mock()
        mock_service.search_by_phone.return_value = [sample_contact]
        mock_get_service.return_value = mock_service

        response = client.get("/api/search/phone?q=555-123-4567&limit=10&offset=5")

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 5

        mock_service.search_by_phone.assert_called_once_with(
            phone_number="555-123-4567",
            limit=10,
            offset=5,
        )

    def test_search_by_phone_missing_query(self, client):
        """Test phone search fails without query."""
        response = client.get("/api/search/phone")

        assert response.status_code == 422

    def test_search_by_phone_empty_query(self, client):
        """Test phone search fails with empty query."""
        response = client.get("/api/search/phone?q=")

        assert response.status_code == 422

    @patch("google_contacts_cisco.api.search.get_search_service")
    def test_search_by_phone_service_error(self, mock_get_service, client):
        """Test phone search handles service errors."""
        mock_service = Mock()
        mock_service.search_by_phone.side_effect = Exception("Database error")
        mock_get_service.return_value = mock_service

        response = client.get("/api/search/phone?q=555-123-4567")

        assert response.status_code == 500
        data = response.json()
        assert "Database error" in data["detail"]

    @patch("google_contacts_cisco.api.search.get_search_service")
    def test_search_by_phone_value_error(self, mock_get_service, client):
        """Test phone search handles ValueError."""
        mock_service = Mock()
        mock_service.search_by_phone.side_effect = ValueError("Invalid phone")
        mock_get_service.return_value = mock_service

        response = client.get("/api/search/phone?q=invalid")

        assert response.status_code == 422
        data = response.json()
        assert "Invalid phone" in data["detail"]


class TestSearchHealthEndpoint:
    """Test GET /api/search/health endpoint."""

    def test_search_health(self, client):
        """Test search health check."""
        response = client.get("/api/search/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "search"
        assert "endpoints" in data
        assert "/api/search" in data["endpoints"]
        assert "/api/search/name" in data["endpoints"]
        assert "/api/search/phone" in data["endpoints"]


class TestContactResultFormat:
    """Test contact result format and schema."""

    @patch("google_contacts_cisco.api.search.get_search_service")
    def test_contact_includes_all_fields(
        self, mock_get_service, client, sample_contact
    ):
        """Test contact result includes all expected fields."""
        mock_service = Mock()
        mock_service.search_contacts.return_value = [sample_contact]
        mock_service.count_search_results.return_value = 1
        mock_get_service.return_value = mock_service

        response = client.get("/api/search?q=John")

        assert response.status_code == 200
        data = response.json()
        contact = data["results"][0]

        # Check all fields are present
        assert "id" in contact
        assert "resource_name" in contact
        assert "display_name" in contact
        assert "given_name" in contact
        assert "family_name" in contact
        assert "organization" in contact
        assert "job_title" in contact
        assert "phone_numbers" in contact

    @patch("google_contacts_cisco.api.search.get_search_service")
    def test_phone_number_format(
        self, mock_get_service, client, sample_contact
    ):
        """Test phone number fields are formatted correctly."""
        mock_service = Mock()
        mock_service.search_contacts.return_value = [sample_contact]
        mock_service.count_search_results.return_value = 1
        mock_get_service.return_value = mock_service

        response = client.get("/api/search?q=John")

        assert response.status_code == 200
        data = response.json()
        phone = data["results"][0]["phone_numbers"][0]

        # Check phone number fields
        assert "value" in phone
        assert "display_value" in phone
        assert "type" in phone
        assert "primary" in phone
        assert phone["value"] == "+15551234567"
        assert phone["display_value"] == "(555) 123-4567"
        assert phone["type"] == "mobile"
        assert phone["primary"] is True

    @patch("google_contacts_cisco.api.search.get_search_service")
    def test_contact_without_optional_fields(
        self, mock_get_service, client
    ):
        """Test contact result handles missing optional fields."""
        minimal_contact = Contact(
            id="minimal-id",
            resource_name="people/minimal",
            display_name="Minimal Contact",
            given_name=None,
            family_name=None,
            organization=None,
            job_title=None,
            deleted=False,
        )
        minimal_contact.phone_numbers = []

        mock_service = Mock()
        mock_service.search_contacts.return_value = [minimal_contact]
        mock_service.count_search_results.return_value = 1
        mock_get_service.return_value = mock_service

        response = client.get("/api/search?q=Minimal")

        assert response.status_code == 200
        data = response.json()
        contact = data["results"][0]

        assert contact["display_name"] == "Minimal Contact"
        assert contact["resource_name"] == "people/minimal"
        assert contact["given_name"] is None
        assert contact["family_name"] is None
        assert contact["organization"] is None
        assert contact["job_title"] is None
        assert contact["phone_numbers"] == []


class TestSearchResponseMetadata:
    """Test search response metadata."""

    @patch("google_contacts_cisco.api.search.get_search_service")
    def test_response_includes_metadata(
        self, mock_get_service, client, sample_contact
    ):
        """Test search response includes all metadata."""
        mock_service = Mock()
        mock_service.search_contacts.return_value = [sample_contact]
        mock_service.count_search_results.return_value = 10
        mock_get_service.return_value = mock_service

        response = client.get("/api/search?q=test&limit=5&offset=2")

        assert response.status_code == 200
        data = response.json()

        # Check all metadata fields
        assert "results" in data
        assert "count" in data
        assert "total_count" in data
        assert "query" in data
        assert "elapsed_ms" in data
        assert "limit" in data
        assert "offset" in data

        assert data["count"] == 1  # Number of results returned
        assert data["total_count"] == 10  # Total matching results
        assert data["query"] == "test"
        assert data["limit"] == 5
        assert data["offset"] == 2
        assert isinstance(data["elapsed_ms"], (int, float))
        assert data["elapsed_ms"] >= 0

    @patch("google_contacts_cisco.api.search.get_search_service")
    def test_elapsed_time_is_measured(
        self, mock_get_service, client
    ):
        """Test that elapsed time is measured and reasonable."""
        import time
        
        def slow_search(*args, **kwargs):
            time.sleep(0.01)  # 10ms delay
            return []
        
        mock_service = Mock()
        mock_service.search_contacts.side_effect = slow_search
        mock_service.count_search_results.return_value = 0
        mock_get_service.return_value = mock_service

        response = client.get("/api/search?q=test")

        assert response.status_code == 200
        data = response.json()
        # Should be at least 10ms (we slept for 10ms)
        assert data["elapsed_ms"] >= 10
        # Should be reasonable (less than 1 second for this test)
        assert data["elapsed_ms"] < 1000
