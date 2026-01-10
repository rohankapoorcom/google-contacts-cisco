"""Unit tests for Google People API client.

This module tests all Google client functionality including:
- Client initialization
- Listing connections with pagination
- Single contact retrieval
- Connection testing
- Retry logic with exponential backoff
- Error handling for various API errors
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError

from google_contacts_cisco.services import google_client as google_client_module
from google_contacts_cisco.services.google_client import (
    PERSON_FIELDS,
    CredentialsError,
    GoogleClientError,
    GoogleContactsClient,
    RateLimitError,
    ServerError,
    SyncTokenExpiredError,
    get_google_client,
)


class TestExceptions:
    """Test custom Google client exceptions."""

    def test_google_client_error_is_base_exception(self):
        """GoogleClientError should be the base exception class."""
        error = GoogleClientError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_credentials_error(self):
        """CredentialsError should inherit from GoogleClientError."""
        error = CredentialsError("credentials missing")
        assert isinstance(error, GoogleClientError)
        assert str(error) == "credentials missing"

    def test_rate_limit_error(self):
        """RateLimitError should inherit from GoogleClientError."""
        error = RateLimitError("rate limit exceeded")
        assert isinstance(error, GoogleClientError)
        assert str(error) == "rate limit exceeded"

    def test_server_error(self):
        """ServerError should inherit from GoogleClientError."""
        error = ServerError("server error")
        assert isinstance(error, GoogleClientError)
        assert str(error) == "server error"

    def test_sync_token_expired_error(self):
        """SyncTokenExpiredError should inherit from GoogleClientError."""
        error = SyncTokenExpiredError("sync token expired")
        assert isinstance(error, GoogleClientError)
        assert str(error) == "sync token expired"


class TestPersonFields:
    """Test PERSON_FIELDS constant."""

    def test_person_fields_includes_required_fields(self):
        """PERSON_FIELDS should include all required fields."""
        assert "names" in PERSON_FIELDS
        assert "emailAddresses" in PERSON_FIELDS
        assert "phoneNumbers" in PERSON_FIELDS
        assert "organizations" in PERSON_FIELDS
        assert "metadata" in PERSON_FIELDS

    def test_person_fields_is_list(self):
        """PERSON_FIELDS should be a list."""
        assert isinstance(PERSON_FIELDS, list)

    def test_person_fields_has_minimum_required_count(self):
        """PERSON_FIELDS should have at least the required 5 fields."""
        assert len(PERSON_FIELDS) >= 5


class TestGoogleContactsClientInit:
    """Test GoogleContactsClient initialization."""

    def test_init_with_provided_credentials(self):
        """Should use provided credentials."""
        mock_creds = _create_mock_credentials()

        with patch.object(google_client_module, "build"):
            client = GoogleContactsClient(mock_creds)

        assert client.credentials == mock_creds

    def test_init_loads_credentials_when_none_provided(self, monkeypatch):
        """Should load credentials from storage when none provided."""
        mock_creds = _create_mock_credentials()
        monkeypatch.setattr(google_client_module, "get_credentials", lambda: mock_creds)

        with patch.object(google_client_module, "build"):
            client = GoogleContactsClient()

        assert client.credentials == mock_creds

    def test_init_raises_error_when_no_credentials(self, monkeypatch):
        """Should raise CredentialsError when no credentials available."""
        monkeypatch.setattr(google_client_module, "get_credentials", lambda: None)

        with pytest.raises(CredentialsError) as exc_info:
            GoogleContactsClient()

        assert "Please authenticate first" in str(exc_info.value)

    def test_init_default_max_retries(self):
        """Should have default max_retries of 5."""
        mock_creds = _create_mock_credentials()

        with patch.object(google_client_module, "build"):
            client = GoogleContactsClient(mock_creds)

        assert client.max_retries == 5

    def test_init_default_initial_backoff(self):
        """Should have default initial_backoff of 1.0 seconds."""
        mock_creds = _create_mock_credentials()

        with patch.object(google_client_module, "build"):
            client = GoogleContactsClient(mock_creds)

        assert client.initial_backoff == 1.0

    def test_init_custom_max_retries(self):
        """Should allow custom max_retries."""
        mock_creds = _create_mock_credentials()

        with patch.object(google_client_module, "build"):
            client = GoogleContactsClient(mock_creds, max_retries=3)

        assert client.max_retries == 3

    def test_init_custom_initial_backoff(self):
        """Should allow custom initial_backoff."""
        mock_creds = _create_mock_credentials()

        with patch.object(google_client_module, "build"):
            client = GoogleContactsClient(mock_creds, initial_backoff=2.0)

        assert client.initial_backoff == 2.0

    def test_service_is_lazy_initialized(self):
        """Service should be None until accessed."""
        mock_creds = _create_mock_credentials()

        with patch.object(google_client_module, "build"):
            client = GoogleContactsClient(mock_creds)

        assert client._service is None


class TestGoogleContactsClientService:
    """Test GoogleContactsClient service property."""

    def test_service_creates_api_on_first_access(self):
        """Should call build() on first service access."""
        mock_creds = _create_mock_credentials()
        mock_service = MagicMock()

        with patch.object(
            google_client_module, "build", return_value=mock_service
        ) as mock_build:
            client = GoogleContactsClient(mock_creds)
            _ = client.service

            mock_build.assert_called_once_with("people", "v1", credentials=mock_creds)

    def test_service_returns_same_instance(self):
        """Should return same service instance on repeated access."""
        mock_creds = _create_mock_credentials()
        mock_service = MagicMock()

        with patch.object(
            google_client_module, "build", return_value=mock_service
        ) as mock_build:
            client = GoogleContactsClient(mock_creds)
            service1 = client.service
            service2 = client.service

            assert service1 is service2
            mock_build.assert_called_once()


class TestListConnections:
    """Test listing connections functionality."""

    def test_list_connections_single_page(self):
        """Should yield response for single page of contacts."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        mock_response = {
            "connections": [
                {"resourceName": "people/1", "names": [{"displayName": "John Doe"}]},
                {"resourceName": "people/2", "names": [{"displayName": "Jane Doe"}]},
            ],
            "nextSyncToken": "sync123",
        }
        mock_service.people().connections().list().execute.return_value = mock_response

        with patch.object(google_client_module, "build", return_value=mock_service):
            client = GoogleContactsClient(mock_creds)
            results = list(client.list_connections(page_size=100))

        assert len(results) == 1
        assert len(results[0]["connections"]) == 2
        assert results[0]["nextSyncToken"] == "sync123"

    def test_list_connections_multiple_pages(self):
        """Should yield responses for multiple pages."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        page1 = {
            "connections": [{"resourceName": "people/1"}],
            "nextPageToken": "page2",
            "nextSyncToken": "sync123",
        }
        page2 = {
            "connections": [{"resourceName": "people/2"}],
            "nextSyncToken": "sync123",
        }

        mock_service.people().connections().list().execute.side_effect = [
            page1,
            page2,
        ]

        with patch.object(google_client_module, "build", return_value=mock_service):
            with patch("time.sleep"):  # Skip sleep in tests
                client = GoogleContactsClient(mock_creds)
                results = list(client.list_connections(page_size=1))

        assert len(results) == 2
        assert results[0]["connections"][0]["resourceName"] == "people/1"
        assert results[1]["connections"][0]["resourceName"] == "people/2"

    def test_list_connections_empty_response(self):
        """Should handle empty connections list."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        mock_response = {
            "connections": [],
            "nextSyncToken": "sync123",
        }
        mock_service.people().connections().list().execute.return_value = mock_response

        with patch.object(google_client_module, "build", return_value=mock_service):
            client = GoogleContactsClient(mock_creds)
            results = list(client.list_connections())

        assert len(results) == 1
        assert results[0]["connections"] == []

    def test_list_connections_with_sync_token(self):
        """Should pass sync token in request."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        mock_response = {"connections": [], "nextSyncToken": "newsync"}
        mock_service.people().connections().list().execute.return_value = mock_response

        with patch.object(google_client_module, "build", return_value=mock_service):
            client = GoogleContactsClient(mock_creds)
            list(client.list_connections(sync_token="oldsync"))

        # Verify sync_token was passed in the call
        call_kwargs = mock_service.people().connections().list.call_args[1]
        assert call_kwargs.get("syncToken") == "oldsync"

    def test_list_connections_respects_max_page_size(self):
        """Should cap page size at 1000."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        mock_response = {"connections": [], "nextSyncToken": "sync"}
        mock_service.people().connections().list().execute.return_value = mock_response

        with patch.object(google_client_module, "build", return_value=mock_service):
            client = GoogleContactsClient(mock_creds)
            list(client.list_connections(page_size=2000))

        # Verify the page size was capped at 1000
        call_kwargs = mock_service.people().connections().list.call_args[1]
        assert call_kwargs.get("pageSize") == 1000

    def test_list_connections_sync_token_expired(self):
        """Should raise SyncTokenExpiredError on 410 response."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        error_response = Mock()
        error_response.status = 410
        mock_service.people().connections().list().execute.side_effect = HttpError(
            error_response, b"Sync token expired"
        )

        with patch.object(google_client_module, "build", return_value=mock_service):
            client = GoogleContactsClient(mock_creds)

            with pytest.raises(SyncTokenExpiredError) as exc_info:
                list(client.list_connections(sync_token="expired"))

        assert "full sync" in str(exc_info.value).lower()

    def test_list_connections_adds_delay_between_pages(self):
        """Should add delay between page requests."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        page1 = {"connections": [{}], "nextPageToken": "page2"}
        page2 = {"connections": [{}]}
        mock_service.people().connections().list().execute.side_effect = [
            page1,
            page2,
        ]

        with patch.object(google_client_module, "build", return_value=mock_service):
            with patch("time.sleep") as mock_sleep:
                client = GoogleContactsClient(mock_creds)
                list(client.list_connections())

            mock_sleep.assert_called_with(0.1)


class TestGetPerson:
    """Test getting a single person."""

    def test_get_person_success(self):
        """Should return person data."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        person_data = {
            "resourceName": "people/12345",
            "names": [{"displayName": "John Doe"}],
            "phoneNumbers": [{"value": "+1234567890"}],
        }
        mock_service.people().get().execute.return_value = person_data

        with patch.object(google_client_module, "build", return_value=mock_service):
            client = GoogleContactsClient(mock_creds)
            result = client.get_person("people/12345")

        assert result["resourceName"] == "people/12345"
        assert result["names"][0]["displayName"] == "John Doe"

    def test_get_person_not_found(self):
        """Should raise HttpError when person not found."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        error_response = Mock()
        error_response.status = 404
        mock_service.people().get().execute.side_effect = HttpError(
            error_response, b"Not found"
        )

        with patch.object(google_client_module, "build", return_value=mock_service):
            client = GoogleContactsClient(mock_creds)

            with pytest.raises(HttpError):
                client.get_person("people/nonexistent")


class TestTestConnection:
    """Test connection testing functionality."""

    def test_test_connection_success(self):
        """Should return True on successful connection."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        mock_service.people().connections().list().execute.return_value = {
            "connections": [{"resourceName": "people/1"}]
        }

        with patch.object(google_client_module, "build", return_value=mock_service):
            client = GoogleContactsClient(mock_creds)
            result = client.test_connection()

        assert result is True

    def test_test_connection_empty_contacts(self):
        """Should return True even with no contacts."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        mock_service.people().connections().list().execute.return_value = {
            "connections": []
        }

        with patch.object(google_client_module, "build", return_value=mock_service):
            client = GoogleContactsClient(mock_creds)
            result = client.test_connection()

        assert result is True

    def test_test_connection_failure(self):
        """Should raise HttpError on connection failure."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        error_response = Mock()
        error_response.status = 403
        mock_service.people().connections().list().execute.side_effect = HttpError(
            error_response, b"Forbidden"
        )

        with patch.object(google_client_module, "build", return_value=mock_service):
            client = GoogleContactsClient(mock_creds)

            with pytest.raises(HttpError):
                client.test_connection()


class TestGetTotalConnectionsCount:
    """Test getting total connections count."""

    def test_get_total_connections_count_with_total_items(self):
        """Should return totalItems when available."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        mock_service.people().connections().list().execute.return_value = {
            "connections": [],
            "totalItems": 150,
        }

        with patch.object(google_client_module, "build", return_value=mock_service):
            client = GoogleContactsClient(mock_creds)
            result = client.get_total_connections_count()

        assert result == 150

    def test_get_total_connections_count_with_total_people(self):
        """Should return totalPeople as fallback."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        mock_service.people().connections().list().execute.return_value = {
            "connections": [],
            "totalPeople": 200,
        }

        with patch.object(google_client_module, "build", return_value=mock_service):
            client = GoogleContactsClient(mock_creds)
            result = client.get_total_connections_count()

        assert result == 200

    def test_get_total_connections_count_zero(self):
        """Should return 0 when no total available."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        mock_service.people().connections().list().execute.return_value = {
            "connections": []
        }

        with patch.object(google_client_module, "build", return_value=mock_service):
            client = GoogleContactsClient(mock_creds)
            result = client.get_total_connections_count()

        assert result == 0


class TestRetryLogic:
    """Test retry logic with exponential backoff."""

    def test_retry_on_rate_limit(self):
        """Should retry on 429 rate limit error."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        error_response = Mock()
        error_response.status = 429

        # First call fails, second succeeds
        mock_service.people().connections().list().execute.side_effect = [
            HttpError(error_response, b"Rate limit"),
            {"connections": [], "nextSyncToken": "sync123"},
        ]

        with patch.object(google_client_module, "build", return_value=mock_service):
            with patch("time.sleep"):
                client = GoogleContactsClient(mock_creds)
                results = list(client.list_connections())

        assert len(results) == 1

    def test_retry_on_server_error(self):
        """Should retry on 500+ server errors."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        error_response = Mock()
        error_response.status = 500

        # First call fails, second succeeds
        mock_service.people().connections().list().execute.side_effect = [
            HttpError(error_response, b"Server error"),
            {"connections": []},
        ]

        with patch.object(google_client_module, "build", return_value=mock_service):
            with patch("time.sleep"):
                client = GoogleContactsClient(mock_creds)
                results = list(client.list_connections())

        assert len(results) == 1

    def test_retry_on_502_error(self):
        """Should retry on 502 bad gateway error."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        error_response = Mock()
        error_response.status = 502

        mock_service.people().connections().list().execute.side_effect = [
            HttpError(error_response, b"Bad gateway"),
            {"connections": []},
        ]

        with patch.object(google_client_module, "build", return_value=mock_service):
            with patch("time.sleep"):
                client = GoogleContactsClient(mock_creds)
                results = list(client.list_connections())

        assert len(results) == 1

    def test_retry_on_503_error(self):
        """Should retry on 503 service unavailable error."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        error_response = Mock()
        error_response.status = 503

        mock_service.people().connections().list().execute.side_effect = [
            HttpError(error_response, b"Service unavailable"),
            {"connections": []},
        ]

        with patch.object(google_client_module, "build", return_value=mock_service):
            with patch("time.sleep"):
                client = GoogleContactsClient(mock_creds)
                results = list(client.list_connections())

        assert len(results) == 1

    def test_exponential_backoff_timing(self):
        """Should use exponential backoff for retries."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        error_response = Mock()
        error_response.status = 429

        mock_service.people().connections().list().execute.side_effect = [
            HttpError(error_response, b"Rate limit"),
            HttpError(error_response, b"Rate limit"),
            {"connections": []},
        ]

        with patch.object(google_client_module, "build", return_value=mock_service):
            with patch("time.sleep") as mock_sleep:
                client = GoogleContactsClient(mock_creds, initial_backoff=1.0)
                list(client.list_connections())

            # First retry: 1.0 * 2^0 = 1.0
            # Second retry: 1.0 * 2^1 = 2.0
            calls = mock_sleep.call_args_list
            assert len(calls) >= 2
            assert calls[0][0][0] == 1.0
            assert calls[1][0][0] == 2.0

    def test_max_retries_exceeded_rate_limit(self):
        """Should raise RateLimitError after max retries."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        error_response = Mock()
        error_response.status = 429

        mock_service.people().connections().list().execute.side_effect = HttpError(
            error_response, b"Rate limit"
        )

        with patch.object(google_client_module, "build", return_value=mock_service):
            with patch("time.sleep"):
                client = GoogleContactsClient(mock_creds, max_retries=2)

                with pytest.raises(RateLimitError) as exc_info:
                    list(client.list_connections())

        assert "2 retries" in str(exc_info.value)

    def test_max_retries_exceeded_server_error(self):
        """Should raise ServerError after max retries."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        error_response = Mock()
        error_response.status = 500

        mock_service.people().connections().list().execute.side_effect = HttpError(
            error_response, b"Server error"
        )

        with patch.object(google_client_module, "build", return_value=mock_service):
            with patch("time.sleep"):
                client = GoogleContactsClient(mock_creds, max_retries=2)

                with pytest.raises(ServerError) as exc_info:
                    list(client.list_connections())

        assert "500" in str(exc_info.value)
        assert "2 retries" in str(exc_info.value)

    def test_no_retry_on_401(self):
        """Should not retry on 401 unauthorized error."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        error_response = Mock()
        error_response.status = 401

        mock_service.people().connections().list().execute.side_effect = HttpError(
            error_response, b"Unauthorized"
        )

        with patch.object(google_client_module, "build", return_value=mock_service):
            with patch("time.sleep") as mock_sleep:
                client = GoogleContactsClient(mock_creds)

                with pytest.raises(HttpError):
                    list(client.list_connections())

            # Should not have called sleep (no retries)
            mock_sleep.assert_not_called()

    def test_no_retry_on_403(self):
        """Should not retry on 403 forbidden error."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        error_response = Mock()
        error_response.status = 403

        mock_service.people().connections().list().execute.side_effect = HttpError(
            error_response, b"Forbidden"
        )

        with patch.object(google_client_module, "build", return_value=mock_service):
            with patch("time.sleep") as mock_sleep:
                client = GoogleContactsClient(mock_creds)

                with pytest.raises(HttpError):
                    list(client.list_connections())

            mock_sleep.assert_not_called()

    def test_no_retry_on_404(self):
        """Should not retry on 404 not found error."""
        mock_creds = _create_mock_credentials()
        mock_service = _create_mock_service()

        error_response = Mock()
        error_response.status = 404

        mock_service.people().get().execute.side_effect = HttpError(
            error_response, b"Not found"
        )

        with patch.object(google_client_module, "build", return_value=mock_service):
            with patch("time.sleep") as mock_sleep:
                client = GoogleContactsClient(mock_creds)

                with pytest.raises(HttpError):
                    client.get_person("people/nonexistent")

            mock_sleep.assert_not_called()


class TestGetGoogleClient:
    """Test get_google_client factory function."""

    def test_get_google_client_returns_client(self, monkeypatch):
        """Should return GoogleContactsClient instance."""
        mock_creds = _create_mock_credentials()
        monkeypatch.setattr(google_client_module, "get_credentials", lambda: mock_creds)

        with patch.object(google_client_module, "build"):
            client = get_google_client()

        assert isinstance(client, GoogleContactsClient)

    def test_get_google_client_with_credentials(self):
        """Should use provided credentials."""
        mock_creds = _create_mock_credentials()

        with patch.object(google_client_module, "build"):
            client = get_google_client(mock_creds)

        assert client.credentials == mock_creds

    def test_get_google_client_no_credentials(self, monkeypatch):
        """Should raise CredentialsError when no credentials."""
        monkeypatch.setattr(google_client_module, "get_credentials", lambda: None)

        with pytest.raises(CredentialsError):
            get_google_client()


# Helper functions


def _create_mock_credentials() -> Mock:
    """Create mock Google OAuth credentials for testing."""
    creds = Mock(spec=Credentials)
    creds.valid = True
    creds.expired = False
    creds.refresh_token = "test_refresh_token"
    creds.token = "test_access_token"
    return creds


def _create_mock_service() -> MagicMock:
    """Create mock Google API service for testing."""
    service = MagicMock()
    # Set up the chain of method calls for people().connections().list()
    service.people.return_value.connections.return_value.list.return_value.execute.return_value = (  # noqa: E501
        {}
    )
    # Set up for people().get()
    service.people.return_value.get.return_value.execute.return_value = {}
    return service
