"""Unit tests for OAuth 2.0 authentication module.

This module tests all OAuth functionality including:
- OAuth client creation
- Token storage and retrieval
- Credential management
- Authentication status checking
- Token refresh logic
- Error handling
"""

import json
import os
import stat
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials

from google_contacts_cisco.auth import oauth
from google_contacts_cisco.auth.oauth import (
    CredentialsNotConfiguredError,
    OAuthError,
    TokenExchangeError,
    TokenRefreshError,
    credentials_to_dict,
    delete_token_file,
    get_auth_status,
    get_authorization_url,
    get_credentials,
    get_oauth_client,
    get_scopes,
    get_token_path,
    handle_oauth_callback,
    is_authenticated,
    revoke_credentials,
    save_credentials,
)


class TestExceptions:
    """Test custom OAuth exceptions."""

    def test_oauth_error_is_base_exception(self):
        """OAuthError should be the base exception class."""
        error = OAuthError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_credentials_not_configured_error(self):
        """CredentialsNotConfiguredError should inherit from OAuthError."""
        error = CredentialsNotConfiguredError("credentials missing")
        assert isinstance(error, OAuthError)
        assert str(error) == "credentials missing"

    def test_token_exchange_error(self):
        """TokenExchangeError should inherit from OAuthError."""
        error = TokenExchangeError("exchange failed")
        assert isinstance(error, OAuthError)
        assert str(error) == "exchange failed"

    def test_token_refresh_error(self):
        """TokenRefreshError should inherit from OAuthError."""
        error = TokenRefreshError("refresh failed")
        assert isinstance(error, OAuthError)
        assert str(error) == "refresh failed"


class TestGetScopes:
    """Test get_scopes function."""

    def test_get_scopes_returns_list(self, monkeypatch):
        """get_scopes should return the configured scopes."""
        mock_settings = Mock()
        mock_settings.google_oauth_scopes = [
            "https://www.googleapis.com/auth/contacts.readonly"
        ]
        monkeypatch.setattr(oauth, "settings", mock_settings)

        scopes = get_scopes()

        assert isinstance(scopes, list)
        assert "https://www.googleapis.com/auth/contacts.readonly" in scopes

    def test_get_scopes_returns_settings_value(self, monkeypatch):
        """get_scopes should return whatever is configured in settings."""
        mock_settings = Mock()
        mock_settings.google_oauth_scopes = ["scope1", "scope2"]
        monkeypatch.setattr(oauth, "settings", mock_settings)

        scopes = get_scopes()

        assert scopes == ["scope1", "scope2"]


class TestGetTokenPath:
    """Test get_token_path function."""

    def test_get_token_path_returns_path(self, monkeypatch):
        """get_token_path should return a Path object."""
        mock_settings = Mock()
        mock_settings.token_path = Path("/tmp/test/token.json")
        monkeypatch.setattr(oauth, "settings", mock_settings)

        path = get_token_path()

        assert isinstance(path, Path)
        assert path == Path("/tmp/test/token.json")


class TestGetOAuthClient:
    """Test OAuth client creation."""

    def test_get_oauth_client_missing_client_id(self, monkeypatch):
        """Should raise error when client_id is not configured."""
        mock_settings = Mock()
        mock_settings.google_client_id = None
        mock_settings.google_client_secret = "secret"
        monkeypatch.setattr(oauth, "settings", mock_settings)

        with pytest.raises(CredentialsNotConfiguredError) as exc_info:
            get_oauth_client()

        assert "GOOGLE_CLIENT_ID" in str(exc_info.value)

    def test_get_oauth_client_missing_client_secret(self, monkeypatch):
        """Should raise error when client_secret is not configured."""
        mock_settings = Mock()
        mock_settings.google_client_id = "client_id"
        mock_settings.google_client_secret = None
        monkeypatch.setattr(oauth, "settings", mock_settings)

        with pytest.raises(CredentialsNotConfiguredError) as exc_info:
            get_oauth_client()

        assert "GOOGLE_CLIENT_SECRET" in str(exc_info.value)

    def test_get_oauth_client_missing_both(self, monkeypatch):
        """Should raise error when both credentials are missing."""
        mock_settings = Mock()
        mock_settings.google_client_id = None
        mock_settings.google_client_secret = None
        monkeypatch.setattr(oauth, "settings", mock_settings)

        with pytest.raises(CredentialsNotConfiguredError):
            get_oauth_client()

    def test_get_oauth_client_success(self, monkeypatch):
        """Should return a Flow object when credentials are configured."""
        mock_settings = Mock()
        mock_settings.google_client_id = "test_client_id"
        mock_settings.google_client_secret = "test_client_secret"
        mock_settings.google_redirect_uri = "http://localhost:8000/auth/callback"
        mock_settings.google_oauth_scopes = [
            "https://www.googleapis.com/auth/contacts.readonly"
        ]
        monkeypatch.setattr(oauth, "settings", mock_settings)

        flow = get_oauth_client()

        assert flow is not None
        assert flow.redirect_uri == "http://localhost:8000/auth/callback"

    def test_get_oauth_client_empty_string_client_id(self, monkeypatch):
        """Should raise error when client_id is empty string."""
        mock_settings = Mock()
        mock_settings.google_client_id = ""
        mock_settings.google_client_secret = "secret"
        monkeypatch.setattr(oauth, "settings", mock_settings)

        with pytest.raises(CredentialsNotConfiguredError):
            get_oauth_client()


class TestSaveCredentials:
    """Test credential saving functionality."""

    def test_save_credentials_creates_directory(self, tmp_path, monkeypatch):
        """Should create parent directories if they don't exist."""
        token_path = tmp_path / "subdir" / "nested" / "token.json"
        mock_settings = Mock()
        mock_settings.token_path = token_path
        monkeypatch.setattr(oauth, "settings", mock_settings)

        creds = _create_mock_credentials()

        save_credentials(creds)

        assert token_path.exists()
        assert token_path.parent.exists()

    def test_save_credentials_writes_json(self, tmp_path, monkeypatch):
        """Should write valid JSON to token file."""
        token_path = tmp_path / "token.json"
        mock_settings = Mock()
        mock_settings.token_path = token_path
        monkeypatch.setattr(oauth, "settings", mock_settings)

        creds = _create_mock_credentials()

        save_credentials(creds)

        assert token_path.exists()
        content = token_path.read_text()
        data = json.loads(content)
        assert "token" in data
        assert data["token"] == "test_access_token"

    def test_save_credentials_overwrites_existing(self, tmp_path, monkeypatch):
        """Should overwrite existing token file."""
        token_path = tmp_path / "token.json"
        token_path.write_text('{"old": "data"}')
        mock_settings = Mock()
        mock_settings.token_path = token_path
        monkeypatch.setattr(oauth, "settings", mock_settings)

        creds = _create_mock_credentials()

        save_credentials(creds)

        content = json.loads(token_path.read_text())
        assert "token" in content
        assert "old" not in content

    @pytest.mark.skipif(
        os.name == "nt", reason="File permissions work differently on Windows"
    )
    def test_save_credentials_sets_permissions(self, tmp_path, monkeypatch):
        """Should set restrictive file permissions (Unix only)."""
        token_path = tmp_path / "token.json"
        mock_settings = Mock()
        mock_settings.token_path = token_path
        monkeypatch.setattr(oauth, "settings", mock_settings)

        creds = _create_mock_credentials()

        save_credentials(creds)

        file_stat = os.stat(token_path)
        # Check that only owner has read/write
        mode = stat.S_IMODE(file_stat.st_mode)
        assert mode == 0o600


class TestGetCredentials:
    """Test credential retrieval functionality."""

    def test_get_credentials_no_token_file(self, tmp_path, monkeypatch):
        """Should return None when token file doesn't exist."""
        token_path = tmp_path / "nonexistent.json"
        mock_settings = Mock()
        mock_settings.token_path = token_path
        mock_settings.google_oauth_scopes = [
            "https://www.googleapis.com/auth/contacts.readonly"
        ]
        monkeypatch.setattr(oauth, "settings", mock_settings)

        result = get_credentials()

        assert result is None

    def test_get_credentials_invalid_json(self, tmp_path, monkeypatch):
        """Should return None when token file contains invalid JSON."""
        token_path = tmp_path / "token.json"
        token_path.write_text("not valid json")
        mock_settings = Mock()
        mock_settings.token_path = token_path
        mock_settings.google_oauth_scopes = [
            "https://www.googleapis.com/auth/contacts.readonly"
        ]
        monkeypatch.setattr(oauth, "settings", mock_settings)

        result = get_credentials()

        assert result is None

    def test_get_credentials_valid_token(self, tmp_path, monkeypatch):
        """Should return valid credentials from token file."""
        token_path = tmp_path / "token.json"
        mock_settings = Mock()
        mock_settings.token_path = token_path
        mock_settings.google_oauth_scopes = [
            "https://www.googleapis.com/auth/contacts.readonly"
        ]
        monkeypatch.setattr(oauth, "settings", mock_settings)

        # Write a valid token file
        token_data = {
            "token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "scopes": ["https://www.googleapis.com/auth/contacts.readonly"],
        }
        token_path.write_text(json.dumps(token_data))

        # Mock the credentials as valid
        with patch.object(Credentials, "valid", True, create=True):
            result = get_credentials()

        assert result is not None
        assert result.token == "test_access_token"

    def test_get_credentials_expired_with_refresh(self, tmp_path, monkeypatch):
        """Should refresh expired credentials if refresh token available."""
        token_path = tmp_path / "token.json"
        mock_settings = Mock()
        mock_settings.token_path = token_path
        mock_settings.google_oauth_scopes = [
            "https://www.googleapis.com/auth/contacts.readonly"
        ]
        monkeypatch.setattr(oauth, "settings", mock_settings)

        # Write a token file with refresh token
        token_data = {
            "token": "expired_token",
            "refresh_token": "test_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "scopes": ["https://www.googleapis.com/auth/contacts.readonly"],
        }
        token_path.write_text(json.dumps(token_data))

        # Mock credentials behavior
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "test_refresh_token"
        mock_creds.token = "new_access_token"
        mock_creds.to_json.return_value = json.dumps(token_data)

        # After refresh, it should be valid
        def set_valid_after_refresh(request):
            mock_creds.valid = True

        mock_creds.refresh.side_effect = set_valid_after_refresh

        with patch(
            "google_contacts_cisco.auth.oauth.Credentials.from_authorized_user_file",
            return_value=mock_creds,
        ):
            result = get_credentials()

        assert result is not None
        mock_creds.refresh.assert_called_once()

    def test_get_credentials_refresh_failure(self, tmp_path, monkeypatch):
        """Should return None when token refresh fails."""
        token_path = tmp_path / "token.json"
        mock_settings = Mock()
        mock_settings.token_path = token_path
        mock_settings.google_oauth_scopes = [
            "https://www.googleapis.com/auth/contacts.readonly"
        ]
        monkeypatch.setattr(oauth, "settings", mock_settings)

        # Write a token file
        token_data = {
            "token": "expired_token",
            "refresh_token": "test_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
        }
        token_path.write_text(json.dumps(token_data))

        # Mock credentials that fail to refresh
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "test_refresh_token"
        mock_creds.refresh.side_effect = RefreshError("Refresh failed")

        with patch(
            "google_contacts_cisco.auth.oauth.Credentials.from_authorized_user_file",
            return_value=mock_creds,
        ):
            result = get_credentials()

        assert result is None

    def test_get_credentials_expired_no_refresh_token(self, tmp_path, monkeypatch):
        """Should return None when expired and no refresh token available."""
        token_path = tmp_path / "token.json"
        mock_settings = Mock()
        mock_settings.token_path = token_path
        mock_settings.google_oauth_scopes = [
            "https://www.googleapis.com/auth/contacts.readonly"
        ]
        monkeypatch.setattr(oauth, "settings", mock_settings)

        # Write a token file without refresh token
        token_data = {
            "token": "expired_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
        }
        token_path.write_text(json.dumps(token_data))

        # Mock expired credentials without refresh token
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = None

        with patch(
            "google_contacts_cisco.auth.oauth.Credentials.from_authorized_user_file",
            return_value=mock_creds,
        ):
            result = get_credentials()

        assert result is None


class TestDeleteTokenFile:
    """Test token file deletion."""

    def test_delete_token_file_exists(self, tmp_path, monkeypatch):
        """Should delete existing token file and return True."""
        token_path = tmp_path / "token.json"
        token_path.write_text('{"token": "test"}')
        mock_settings = Mock()
        mock_settings.token_path = token_path
        monkeypatch.setattr(oauth, "settings", mock_settings)

        result = delete_token_file()

        assert result is True
        assert not token_path.exists()

    def test_delete_token_file_not_exists(self, tmp_path, monkeypatch):
        """Should return False when token file doesn't exist."""
        token_path = tmp_path / "nonexistent.json"
        mock_settings = Mock()
        mock_settings.token_path = token_path
        monkeypatch.setattr(oauth, "settings", mock_settings)

        result = delete_token_file()

        assert result is False


class TestIsAuthenticated:
    """Test authentication status checking."""

    def test_is_authenticated_true(self, tmp_path, monkeypatch):
        """Should return True when valid credentials exist."""
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        with patch(
            "google_contacts_cisco.auth.oauth.get_credentials", return_value=mock_creds
        ):
            result = is_authenticated()

        assert result is True

    def test_is_authenticated_false_no_credentials(self, monkeypatch):
        """Should return False when no credentials exist."""
        with patch(
            "google_contacts_cisco.auth.oauth.get_credentials", return_value=None
        ):
            result = is_authenticated()

        assert result is False

    def test_is_authenticated_false_invalid_credentials(self, monkeypatch):
        """Should return False when credentials are invalid."""
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = False

        with patch(
            "google_contacts_cisco.auth.oauth.get_credentials", return_value=mock_creds
        ):
            result = is_authenticated()

        assert result is False


class TestRevokeCredentials:
    """Test credential revocation."""

    def test_revoke_credentials_success(self, tmp_path, monkeypatch):
        """Should revoke token and delete file on success."""
        token_path = tmp_path / "token.json"
        token_path.write_text('{"token": "test"}')
        mock_settings = Mock()
        mock_settings.token_path = token_path
        monkeypatch.setattr(oauth, "settings", mock_settings)

        mock_creds = Mock(spec=Credentials)
        mock_creds.token = "test_token"
        mock_creds.valid = True

        mock_response = Mock()
        mock_response.status_code = 200

        with patch(
            "google_contacts_cisco.auth.oauth.get_credentials", return_value=mock_creds
        ):
            with patch(
                "google_contacts_cisco.auth.oauth.requests.post",
                return_value=mock_response,
            ):
                result = revoke_credentials()

        assert result is True
        assert not token_path.exists()

    def test_revoke_credentials_no_token(self, tmp_path, monkeypatch):
        """Should return False when no credentials to revoke."""
        token_path = tmp_path / "nonexistent.json"
        mock_settings = Mock()
        mock_settings.token_path = token_path
        monkeypatch.setattr(oauth, "settings", mock_settings)

        with patch(
            "google_contacts_cisco.auth.oauth.get_credentials", return_value=None
        ):
            result = revoke_credentials()

        assert result is False

    def test_revoke_credentials_api_error_still_deletes(self, tmp_path, monkeypatch):
        """Should delete local file even if revocation API fails."""
        token_path = tmp_path / "token.json"
        token_path.write_text('{"token": "test"}')
        mock_settings = Mock()
        mock_settings.token_path = token_path
        monkeypatch.setattr(oauth, "settings", mock_settings)

        mock_creds = Mock(spec=Credentials)
        mock_creds.token = "test_token"
        mock_creds.valid = True

        # Need to patch requests at the module level where it's imported
        import requests as requests_module

        with patch(
            "google_contacts_cisco.auth.oauth.get_credentials", return_value=mock_creds
        ):
            with patch.object(
                requests_module,
                "post",
                side_effect=Exception("Network error"),
            ):
                # Since the module imports requests directly,
                # we also need to patch it there
                with patch(
                    "google_contacts_cisco.auth.oauth.requests.post",
                ) as mock_post:
                    mock_post.side_effect = oauth.requests.RequestException(
                        "Network error"
                    )
                    result = revoke_credentials()

        assert result is True
        assert not token_path.exists()

    def test_revoke_credentials_api_returns_error(self, tmp_path, monkeypatch):
        """Should still delete file when API returns non-200 status."""
        token_path = tmp_path / "token.json"
        token_path.write_text('{"token": "test"}')
        mock_settings = Mock()
        mock_settings.token_path = token_path
        monkeypatch.setattr(oauth, "settings", mock_settings)

        mock_creds = Mock(spec=Credentials)
        mock_creds.token = "test_token"
        mock_creds.valid = True

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"

        with patch(
            "google_contacts_cisco.auth.oauth.get_credentials", return_value=mock_creds
        ):
            with patch(
                "google_contacts_cisco.auth.oauth.requests.post",
                return_value=mock_response,
            ):
                result = revoke_credentials()

        assert result is True
        assert not token_path.exists()


class TestGetAuthorizationUrl:
    """Test authorization URL generation."""

    def test_get_authorization_url_returns_tuple(self, monkeypatch):
        """Should return a tuple of (url, state)."""
        mock_settings = Mock()
        mock_settings.google_client_id = "test_client_id"
        mock_settings.google_client_secret = "test_client_secret"
        mock_settings.google_redirect_uri = "http://localhost:8000/auth/callback"
        mock_settings.google_oauth_scopes = [
            "https://www.googleapis.com/auth/contacts.readonly"
        ]
        monkeypatch.setattr(oauth, "settings", mock_settings)

        url, state = get_authorization_url()

        assert isinstance(url, str)
        assert isinstance(state, str)
        assert "accounts.google.com" in url

    def test_get_authorization_url_includes_params(self, monkeypatch):
        """Should include required OAuth parameters in URL."""
        mock_settings = Mock()
        mock_settings.google_client_id = "test_client_id"
        mock_settings.google_client_secret = "test_client_secret"
        mock_settings.google_redirect_uri = "http://localhost:8000/auth/callback"
        mock_settings.google_oauth_scopes = [
            "https://www.googleapis.com/auth/contacts.readonly"
        ]
        monkeypatch.setattr(oauth, "settings", mock_settings)

        url, _ = get_authorization_url()

        assert "client_id=test_client_id" in url
        assert "access_type=offline" in url
        assert "prompt=consent" in url

    def test_get_authorization_url_with_custom_state(self, monkeypatch):
        """Should use provided state parameter."""
        mock_settings = Mock()
        mock_settings.google_client_id = "test_client_id"
        mock_settings.google_client_secret = "test_client_secret"
        mock_settings.google_redirect_uri = "http://localhost:8000/auth/callback"
        mock_settings.google_oauth_scopes = [
            "https://www.googleapis.com/auth/contacts.readonly"
        ]
        monkeypatch.setattr(oauth, "settings", mock_settings)

        url, state = get_authorization_url(state="/dashboard")

        # Note: The state might be encoded, so we check the returned state
        assert state is not None


class TestHandleOAuthCallback:
    """Test OAuth callback handling."""

    def test_handle_oauth_callback_success(self, tmp_path, monkeypatch):
        """Should exchange code for tokens and save credentials."""
        mock_settings = Mock()
        mock_settings.google_client_id = "test_client_id"
        mock_settings.google_client_secret = "test_client_secret"
        mock_settings.google_redirect_uri = "http://localhost:8000/auth/callback"
        mock_settings.google_oauth_scopes = [
            "https://www.googleapis.com/auth/contacts.readonly"
        ]
        mock_settings.token_path = tmp_path / "token.json"
        monkeypatch.setattr(oauth, "settings", mock_settings)

        mock_creds = _create_mock_credentials()

        mock_flow = Mock()
        mock_flow.credentials = mock_creds

        with patch(
            "google_contacts_cisco.auth.oauth.get_oauth_client", return_value=mock_flow
        ):
            result = handle_oauth_callback(
                "http://localhost:8000/auth/callback?code=test_code"
            )

        assert result is not None
        mock_flow.fetch_token.assert_called_once()

    def test_handle_oauth_callback_exchange_failure(self, monkeypatch):
        """Should raise TokenExchangeError when exchange fails."""
        mock_settings = Mock()
        mock_settings.google_client_id = "test_client_id"
        mock_settings.google_client_secret = "test_client_secret"
        mock_settings.google_redirect_uri = "http://localhost:8000/auth/callback"
        mock_settings.google_oauth_scopes = [
            "https://www.googleapis.com/auth/contacts.readonly"
        ]
        monkeypatch.setattr(oauth, "settings", mock_settings)

        mock_flow = Mock()
        mock_flow.fetch_token.side_effect = Exception("Exchange failed")

        with patch(
            "google_contacts_cisco.auth.oauth.get_oauth_client", return_value=mock_flow
        ):
            with pytest.raises(TokenExchangeError) as exc_info:
                handle_oauth_callback(
                    "http://localhost:8000/auth/callback?code=invalid_code"
                )

        assert "Exchange failed" in str(exc_info.value)


class TestCredentialsToDict:
    """Test credentials serialization."""

    def test_credentials_to_dict_full(self):
        """Should include all credential fields."""
        creds = _create_mock_credentials()

        result = credentials_to_dict(creds)

        assert result["token"] == "test_access_token"
        assert result["refresh_token"] == "test_refresh_token"
        assert result["token_uri"] == "https://oauth2.googleapis.com/token"
        assert result["client_id"] == "test_client_id"
        assert result["client_secret"] == "test_client_secret"
        assert isinstance(result["scopes"], list)

    def test_credentials_to_dict_no_expiry(self):
        """Should handle None expiry."""
        creds = Mock(spec=Credentials)
        creds.token = "token"
        creds.refresh_token = None
        creds.token_uri = "uri"
        creds.client_id = "id"
        creds.client_secret = "secret"
        creds.scopes = None
        creds.expiry = None

        result = credentials_to_dict(creds)

        assert result["expiry"] is None
        assert result["scopes"] == []


class TestGetAuthStatus:
    """Test authentication status reporting."""

    def test_get_auth_status_not_authenticated(self, tmp_path, monkeypatch):
        """Should return correct status when not authenticated."""
        mock_settings = Mock()
        mock_settings.token_path = tmp_path / "nonexistent.json"
        monkeypatch.setattr(oauth, "settings", mock_settings)

        with patch(
            "google_contacts_cisco.auth.oauth.get_credentials", return_value=None
        ):
            status = get_auth_status()

        assert status["authenticated"] is False
        assert status["has_token_file"] is False
        assert status["credentials_valid"] is False

    def test_get_auth_status_authenticated(self, tmp_path, monkeypatch):
        """Should return correct status when authenticated."""
        token_path = tmp_path / "token.json"
        token_path.write_text('{"token": "test"}')
        mock_settings = Mock()
        mock_settings.token_path = token_path
        monkeypatch.setattr(oauth, "settings", mock_settings)

        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True
        mock_creds.expired = False
        mock_creds.refresh_token = "refresh"
        mock_creds.scopes = ["scope1", "scope2"]

        with patch(
            "google_contacts_cisco.auth.oauth.get_credentials", return_value=mock_creds
        ):
            status = get_auth_status()

        assert status["authenticated"] is True
        assert status["has_token_file"] is True
        assert status["credentials_valid"] is True
        assert status["credentials_expired"] is False
        assert status["has_refresh_token"] is True
        assert status["scopes"] == ["scope1", "scope2"]


# Helper function to create mock credentials
def _create_mock_credentials() -> Credentials:
    """Create mock Google OAuth credentials for testing."""
    return Credentials(
        token="test_access_token",
        refresh_token="test_refresh_token",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="test_client_id",
        client_secret="test_client_secret",
        scopes=["https://www.googleapis.com/auth/contacts.readonly"],
    )
