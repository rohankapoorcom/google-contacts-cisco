"""Unit tests for Google API routes.

This module tests the Google API endpoints including:
- Connection test endpoint
- Error handling for authentication and API errors
"""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from google_contacts_cisco.api import google as google_module
from google_contacts_cisco.main import app
from google_contacts_cisco.services.google_client import (
    CredentialsError,
    RateLimitError,
    ServerError,
)


@pytest.fixture
def client():
    """Create test client for API testing."""
    return TestClient(app)


class TestTestConnectionEndpoint:
    """Test /api/test-connection endpoint."""

    def test_test_connection_not_authenticated(self, client):
        """Should return 401 when not authenticated."""
        with patch.object(google_module, "is_authenticated", return_value=False):
            response = client.get("/api/test-connection")

        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    def test_test_connection_success(self, client):
        """Should return success when connection succeeds."""
        mock_client = Mock()
        mock_client.test_connection.return_value = True
        mock_client.get_total_connections_count.return_value = 150

        with patch.object(google_module, "is_authenticated", return_value=True):
            with patch.object(
                google_module, "get_google_client", return_value=mock_client
            ):
                response = client.get("/api/test-connection")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Successfully connected to Google People API"
        assert data["total_contacts"] == 150

    def test_test_connection_success_no_count(self, client):
        """Should handle when count retrieval fails."""
        mock_client = Mock()
        mock_client.test_connection.return_value = True
        mock_client.get_total_connections_count.side_effect = Exception("Count error")

        with patch.object(google_module, "is_authenticated", return_value=True):
            with patch.object(
                google_module, "get_google_client", return_value=mock_client
            ):
                response = client.get("/api/test-connection")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["total_contacts"] is None

    def test_test_connection_credentials_error(self, client):
        """Should return 401 on credentials error."""
        with patch.object(google_module, "is_authenticated", return_value=True):
            with patch.object(
                google_module,
                "get_google_client",
                side_effect=CredentialsError("Invalid credentials"),
            ):
                response = client.get("/api/test-connection")

        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_test_connection_rate_limit_error(self, client):
        """Should return 429 on rate limit error."""
        mock_client = Mock()
        mock_client.test_connection.side_effect = RateLimitError(
            "Rate limit exceeded"
        )

        with patch.object(google_module, "is_authenticated", return_value=True):
            with patch.object(
                google_module, "get_google_client", return_value=mock_client
            ):
                response = client.get("/api/test-connection")

        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]

    def test_test_connection_server_error(self, client):
        """Should return 502 on Google server error."""
        mock_client = Mock()
        mock_client.test_connection.side_effect = ServerError("Google API error")

        with patch.object(google_module, "is_authenticated", return_value=True):
            with patch.object(
                google_module, "get_google_client", return_value=mock_client
            ):
                response = client.get("/api/test-connection")

        assert response.status_code == 502
        assert "Google API server error" in response.json()["detail"]

    def test_test_connection_unexpected_error(self, client):
        """Should return 500 on unexpected error."""
        mock_client = Mock()
        mock_client.test_connection.side_effect = Exception("Unexpected error")

        with patch.object(google_module, "is_authenticated", return_value=True):
            with patch.object(
                google_module, "get_google_client", return_value=mock_client
            ):
                response = client.get("/api/test-connection")

        assert response.status_code == 500
        assert "Connection test failed" in response.json()["detail"]


class TestResponseModels:
    """Test response model validation."""

    def test_test_connection_response_includes_all_fields(self, client):
        """Response should include all expected fields."""
        mock_client = Mock()
        mock_client.test_connection.return_value = True
        mock_client.get_total_connections_count.return_value = 42

        with patch.object(google_module, "is_authenticated", return_value=True):
            with patch.object(
                google_module, "get_google_client", return_value=mock_client
            ):
                response = client.get("/api/test-connection")

        data = response.json()
        assert "status" in data
        assert "message" in data
        assert "total_contacts" in data

