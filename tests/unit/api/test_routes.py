"""Unit tests for OAuth API endpoints.

This module tests all OAuth-related API endpoints:
- GET /auth/url - Get OAuth authorization URL (JSON)
- GET /auth/google - Initiate OAuth flow (redirect)
- GET /auth/callback - Handle OAuth callback
- GET /auth/status - Check authentication status
- POST /auth/refresh - Refresh OAuth token
- POST /auth/revoke - Revoke credentials
- POST /auth/disconnect - Disconnect (alias for revoke)
"""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from google.auth.exceptions import RefreshError

from google_contacts_cisco.auth.oauth import (
    CredentialsNotConfiguredError,
    TokenExchangeError,
    TokenRefreshError,
)
from google_contacts_cisco.main import app

client = TestClient(app)


class TestAuthUrlEndpoint:
    """Test GET /auth/url endpoint."""

    def test_auth_url_returns_json(self):
        """Should return JSON with OAuth URL."""
        with patch(
            "google_contacts_cisco.api.routes.get_authorization_url"
        ) as mock_get_url:
            mock_get_url.return_value = ("https://accounts.google.com/auth", "state123")

            response = client.get("/auth/url")

            assert response.status_code == 200
            data = response.json()
            assert "auth_url" in data
            assert "accounts.google.com" in data["auth_url"]
            assert data["state"] == "state123"

    def test_auth_url_with_redirect_uri(self):
        """Should pass redirect_uri as state parameter."""
        with patch(
            "google_contacts_cisco.api.routes.get_authorization_url"
        ) as mock_get_url:
            mock_get_url.return_value = (
                "https://accounts.google.com/auth",
                "/dashboard",
            )

            response = client.get("/auth/url?redirect_uri=/dashboard")

            assert response.status_code == 200
            data = response.json()
            assert "auth_url" in data
            mock_get_url.assert_called_once_with(state="/dashboard")

    def test_auth_url_credentials_not_configured(self):
        """Should return 500 when credentials not configured."""
        with patch(
            "google_contacts_cisco.api.routes.get_authorization_url"
        ) as mock_get_url:
            mock_get_url.side_effect = CredentialsNotConfiguredError(
                "Credentials not set"
            )

            response = client.get("/auth/url")

            assert response.status_code == 500
            assert "GOOGLE_CLIENT_ID" in response.json()["detail"]


class TestAuthGoogleEndpoint:
    """Test GET /auth/google endpoint."""

    def test_auth_google_redirects(self):
        """Should redirect to Google OAuth URL."""
        with patch(
            "google_contacts_cisco.api.routes.get_authorization_url"
        ) as mock_get_url:
            mock_get_url.return_value = ("https://accounts.google.com/auth", "state123")

            response = client.get("/auth/google", follow_redirects=False)

            assert response.status_code == 307
            assert "accounts.google.com" in response.headers["location"]

    def test_auth_google_with_redirect_uri(self):
        """Should pass redirect_uri as state parameter."""
        with patch(
            "google_contacts_cisco.api.routes.get_authorization_url"
        ) as mock_get_url:
            mock_get_url.return_value = ("https://accounts.google.com/auth", "/dashboard")

            response = client.get(
                "/auth/google?redirect_uri=/dashboard", follow_redirects=False
            )

            assert response.status_code == 307
            mock_get_url.assert_called_once_with(state="/dashboard")

    def test_auth_google_credentials_not_configured(self):
        """Should return 500 when credentials not configured."""
        with patch(
            "google_contacts_cisco.api.routes.get_authorization_url"
        ) as mock_get_url:
            mock_get_url.side_effect = CredentialsNotConfiguredError(
                "Credentials not set"
            )

            response = client.get("/auth/google")

            assert response.status_code == 500
            assert "GOOGLE_CLIENT_ID" in response.json()["detail"]


class TestAuthCallbackEndpoint:
    """Test GET /auth/callback endpoint."""

    def test_auth_callback_success(self):
        """Should return success HTML when authentication succeeds."""
        mock_creds = Mock()
        mock_creds.token = "test_token"

        with patch(
            "google_contacts_cisco.api.routes.handle_oauth_callback"
        ) as mock_handle:
            mock_handle.return_value = (mock_creds, None)  # Return tuple

            response = client.get("/auth/callback?code=test_code&state=/")

            assert response.status_code == 200
            assert "Successful" in response.text
            assert "text/html" in response.headers["content-type"]

    def test_auth_callback_with_state_redirect(self):
        """Should include redirect link when state contains path."""
        mock_creds = Mock()

        with patch(
            "google_contacts_cisco.api.routes.handle_oauth_callback"
        ) as mock_handle:
            mock_handle.return_value = (mock_creds, "/dashboard")  # Return tuple with custom_data

            response = client.get("/auth/callback?code=test_code&state=/dashboard")

            assert response.status_code == 200
            assert "/dashboard" in response.text

    def test_auth_callback_error_from_google(self):
        """Should return error HTML when Google returns error."""
        response = client.get("/auth/callback?error=access_denied&error_description=User+denied")

        assert response.status_code == 400
        assert "Failed" in response.text
        assert "access_denied" in response.text

    def test_auth_callback_error_no_description(self):
        """Should handle error without description."""
        response = client.get("/auth/callback?error=access_denied")

        assert response.status_code == 400
        assert "access_denied" in response.text

    def test_auth_callback_missing_code(self):
        """Should return error when code is missing."""
        response = client.get("/auth/callback")

        assert response.status_code == 400
        assert "missing_code" in response.text

    def test_auth_callback_token_exchange_error(self):
        """Should return error HTML when token exchange fails."""
        with patch(
            "google_contacts_cisco.api.routes.handle_oauth_callback"
        ) as mock_handle:
            mock_handle.side_effect = TokenExchangeError("Exchange failed")

            response = client.get("/auth/callback?code=invalid_code")

            assert response.status_code == 500
            assert "Exchange failed" in response.text

    def test_auth_callback_credentials_not_configured(self):
        """Should return error when credentials not configured."""
        with patch(
            "google_contacts_cisco.api.routes.handle_oauth_callback"
        ) as mock_handle:
            mock_handle.side_effect = CredentialsNotConfiguredError("Not configured")

            response = client.get("/auth/callback?code=test_code")

            assert response.status_code == 500
            assert "not_configured" in response.text

    def test_auth_callback_unexpected_error(self):
        """Should handle unexpected exceptions gracefully."""
        with patch(
            "google_contacts_cisco.api.routes.handle_oauth_callback"
        ) as mock_handle:
            mock_handle.side_effect = Exception("Unexpected error")

            response = client.get("/auth/callback?code=test_code")

            assert response.status_code == 500
            assert "unexpected_error" in response.text


class TestAuthStatusEndpoint:
    """Test GET /auth/status endpoint."""

    def test_auth_status_not_authenticated(self):
        """Should return authenticated=False when not authenticated."""
        with patch("google_contacts_cisco.api.routes.get_auth_status") as mock_status:
            mock_status.return_value = {
                "authenticated": False,
                "has_token_file": False,
                "credentials_valid": False,
                "credentials_expired": False,
                "has_refresh_token": False,
                "scopes": [],
            }

            response = client.get("/auth/status")

            assert response.status_code == 200
            data = response.json()
            assert data["authenticated"] is False
            assert data["has_token_file"] is False

    def test_auth_status_authenticated(self):
        """Should return detailed status when authenticated."""
        with patch("google_contacts_cisco.api.routes.get_auth_status") as mock_status:
            mock_status.return_value = {
                "authenticated": True,
                "has_token_file": True,
                "credentials_valid": True,
                "credentials_expired": False,
                "has_refresh_token": True,
                "scopes": ["https://www.googleapis.com/auth/contacts.readonly"],
            }

            response = client.get("/auth/status")

            assert response.status_code == 200
            data = response.json()
            assert data["authenticated"] is True
            assert data["credentials_valid"] is True
            assert data["has_refresh_token"] is True
            assert len(data["scopes"]) == 1

    def test_auth_status_expired_credentials(self):
        """Should indicate when credentials are expired."""
        with patch("google_contacts_cisco.api.routes.get_auth_status") as mock_status:
            mock_status.return_value = {
                "authenticated": False,
                "has_token_file": True,
                "credentials_valid": False,
                "credentials_expired": True,
                "has_refresh_token": True,
                "scopes": ["https://www.googleapis.com/auth/contacts.readonly"],
            }

            response = client.get("/auth/status")

            assert response.status_code == 200
            data = response.json()
            assert data["authenticated"] is False
            assert data["credentials_expired"] is True


class TestAuthRefreshEndpoint:
    """Test POST /auth/refresh endpoint."""

    def test_auth_refresh_success(self):
        """Should refresh token successfully."""
        mock_creds = Mock()
        mock_creds.refresh_token = "test_refresh_token"
        mock_creds.token = "new_access_token"
        mock_creds.to_json.return_value = '{"token": "new_access_token"}'

        with patch("google_contacts_cisco.api.routes.is_authenticated") as mock_auth:
            mock_auth.return_value = True
            with patch(
                "google_contacts_cisco.api.routes.get_credentials"
            ) as mock_get_creds:
                mock_get_creds.return_value = mock_creds
                with patch("google_contacts_cisco.api.routes.save_credentials"):
                    response = client.post("/auth/refresh")

                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert "refreshed" in data["message"]

    def test_auth_refresh_not_authenticated(self):
        """Should return 401 when not authenticated."""
        with patch("google_contacts_cisco.api.routes.is_authenticated") as mock_auth:
            mock_auth.return_value = False

            response = client.post("/auth/refresh")

            assert response.status_code == 401
            assert "Not authenticated" in response.json()["detail"]

    def test_auth_refresh_no_refresh_token(self):
        """Should return 400 when no refresh token available."""
        mock_creds = Mock()
        mock_creds.refresh_token = None

        with patch("google_contacts_cisco.api.routes.is_authenticated") as mock_auth:
            mock_auth.return_value = True
            with patch(
                "google_contacts_cisco.api.routes.get_credentials"
            ) as mock_get_creds:
                mock_get_creds.return_value = mock_creds

                response = client.post("/auth/refresh")

                assert response.status_code == 400
                assert "No refresh token" in response.json()["detail"]

    def test_auth_refresh_failure(self):
        """Should handle refresh failure gracefully."""
        mock_creds = Mock()
        mock_creds.refresh_token = "test_refresh_token"
        mock_creds.refresh.side_effect = RefreshError("Refresh failed")

        with patch("google_contacts_cisco.api.routes.is_authenticated") as mock_auth:
            mock_auth.return_value = True
            with patch(
                "google_contacts_cisco.api.routes.get_credentials"
            ) as mock_get_creds:
                mock_get_creds.return_value = mock_creds

                response = client.post("/auth/refresh")

                assert response.status_code == 401
                assert "failed" in response.json()["detail"].lower()


class TestAuthRevokeEndpoint:
    """Test POST /auth/revoke endpoint."""

    def test_auth_revoke_success(self):
        """Should revoke credentials successfully."""
        with patch("google_contacts_cisco.api.routes.is_authenticated") as mock_auth:
            mock_auth.return_value = True
            with patch(
                "google_contacts_cisco.api.routes.revoke_credentials"
            ) as mock_revoke:
                mock_revoke.return_value = True

                response = client.post("/auth/revoke")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "successfully" in data["message"]

    def test_auth_revoke_no_credentials(self):
        """Should return success=False when no credentials to revoke."""
        with patch("google_contacts_cisco.api.routes.is_authenticated") as mock_auth:
            mock_auth.return_value = False

            response = client.post("/auth/revoke")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "No credentials" in data["message"]

    def test_auth_revoke_failure(self):
        """Should handle revocation failure gracefully."""
        with patch("google_contacts_cisco.api.routes.is_authenticated") as mock_auth:
            mock_auth.return_value = True
            with patch(
                "google_contacts_cisco.api.routes.revoke_credentials"
            ) as mock_revoke:
                mock_revoke.return_value = False

                response = client.post("/auth/revoke")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is False


class TestAuthDisconnectEndpoint:
    """Test POST /auth/disconnect endpoint."""

    def test_auth_disconnect_success(self):
        """Should disconnect successfully (alias for revoke)."""
        with patch("google_contacts_cisco.api.routes.is_authenticated") as mock_auth:
            mock_auth.return_value = True
            with patch(
                "google_contacts_cisco.api.routes.revoke_credentials"
            ) as mock_revoke:
                mock_revoke.return_value = True

                response = client.post("/auth/disconnect")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    def test_auth_disconnect_no_credentials(self):
        """Should return success=False when no credentials."""
        with patch("google_contacts_cisco.api.routes.is_authenticated") as mock_auth:
            mock_auth.return_value = False

            response = client.post("/auth/disconnect")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False


class TestAuthEndpointIntegration:
    """Integration tests for auth endpoints working together."""

    def test_full_oauth_flow_status_before_auth(self):
        """Should show not authenticated before OAuth."""
        with patch("google_contacts_cisco.api.routes.get_auth_status") as mock_status:
            mock_status.return_value = {
                "authenticated": False,
                "has_token_file": False,
                "credentials_valid": False,
                "credentials_expired": False,
                "has_refresh_token": False,
                "scopes": [],
            }

            response = client.get("/auth/status")

            assert response.json()["authenticated"] is False

    def test_html_response_content_type(self):
        """Callback should return HTML content type."""
        mock_creds = Mock()

        with patch(
            "google_contacts_cisco.api.routes.handle_oauth_callback"
        ) as mock_handle:
            mock_handle.return_value = mock_creds

            response = client.get("/auth/callback?code=test")

            assert "text/html" in response.headers["content-type"]

    def test_error_page_includes_styling(self):
        """Error page should include CSS styling."""
        response = client.get("/auth/callback?error=test_error")

        assert response.status_code == 400
        assert "<style>" in response.text
        assert "</style>" in response.text

    def test_success_page_includes_styling(self):
        """Success page should include CSS styling."""
        mock_creds = Mock()

        with patch(
            "google_contacts_cisco.api.routes.handle_oauth_callback"
        ) as mock_handle:
            mock_handle.return_value = mock_creds

            response = client.get("/auth/callback?code=test")

            assert "<style>" in response.text
            assert "</style>" in response.text


class TestOpenAPISchema:
    """Test that endpoints are properly documented."""

    def test_auth_endpoints_in_schema(self):
        """All auth endpoints should appear in OpenAPI schema."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()

        paths = schema["paths"]
        assert "/auth/url" in paths
        assert "/auth/google" in paths
        assert "/auth/callback" in paths
        assert "/auth/status" in paths
        assert "/auth/refresh" in paths
        assert "/auth/revoke" in paths
        assert "/auth/disconnect" in paths

    def test_auth_tag_in_schema(self):
        """Auth endpoints should have authentication tag."""
        response = client.get("/openapi.json")
        schema = response.json()

        # Check that endpoints are tagged
        auth_google = schema["paths"]["/auth/google"]["get"]
        assert "authentication" in auth_google.get("tags", [])

