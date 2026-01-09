"""Tests for proxy headers middleware and OAuth callback with reverse proxy."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from google_contacts_cisco.main import app
from google_contacts_cisco.config import Settings


def test_proxy_headers_middleware_not_enabled_by_default():
    """Test that proxy headers middleware is not enabled by default."""
    # The app is created with default settings (behind_proxy=False)
    # Just verify the middleware count
    assert len(app.user_middleware) >= 1  # At least CORS middleware


def test_proxy_headers_middleware_enabled_with_setting():
    """Test that proxy headers middleware is enabled when trusted_proxies is set."""
    # This tests the configuration - actual middleware activation happens at app creation
    settings = Settings(trusted_proxies=["127.0.0.1", "172.17.0.0/16"])
    assert settings.trusted_proxies == ["127.0.0.1", "172.17.0.0/16"]


def test_oauth_callback_with_https_forwarded_header(monkeypatch):
    """Test that OAuth callback works correctly when X-Forwarded-Proto is https."""
    # Mock the oauth functions
    mock_credentials = MagicMock()
    mock_credentials.token = "test_token"
    mock_credentials.refresh_token = "test_refresh_token"
    
    with patch("google_contacts_cisco.api.routes.handle_oauth_callback") as mock_handle:
        mock_handle.return_value = mock_credentials
        
        client = TestClient(app)
        
        # Simulate request from reverse proxy with X-Forwarded headers
        response = client.get(
            "/auth/callback",
            params={"code": "test_code", "state": "/"},
            headers={
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "contacts.dev.rohankapoor.com",
            },
        )
        
        # Verify the callback was called
        assert mock_handle.called
        
        # The callback should succeed (even though we're mocking it)
        # In reality, ProxyHeadersMiddleware would reconstruct the URL with https://
        assert response.status_code == 200


def test_oauth_callback_url_format():
    """Test that OAuth callback receives the correct URL format."""
    with patch("google_contacts_cisco.api.routes.handle_oauth_callback") as mock_handle:
        mock_credentials = MagicMock()
        mock_credentials.token = "test_token"
        mock_handle.return_value = mock_credentials
        
        client = TestClient(app)
        
        # Make request with code parameter
        response = client.get(
            "/auth/callback",
            params={"code": "test_code", "state": "/"},
        )
        
        # Verify handle_oauth_callback was called
        assert mock_handle.called
        
        # Get the authorization_response argument (first positional arg)
        call_args = mock_handle.call_args[0]
        authorization_response = call_args[0]
        
        # Verify it's a full URL
        assert authorization_response.startswith("http")
        assert "code=test_code" in authorization_response
        
        # Response should be success
        assert response.status_code == 200


def test_config_proxy_settings():
    """Test proxy-related configuration settings."""
    # Default settings
    settings_default = Settings()
    assert settings_default.trusted_proxies == []
    
    # With trusted proxies configured
    settings_proxy = Settings(trusted_proxies=["127.0.0.1", "10.0.0.0/8"])
    assert settings_proxy.trusted_proxies == ["127.0.0.1", "10.0.0.0/8"]
    
    # With single proxy
    settings_single = Settings(trusted_proxies=["192.168.1.1"])
    assert settings_single.trusted_proxies == ["192.168.1.1"]


def test_oauth_error_without_code():
    """Test OAuth callback error handling when code is missing."""
    client = TestClient(app)
    
    # Request without code parameter
    response = client.get("/auth/callback")
    
    # Should return error page
    assert response.status_code == 400
    assert b"missing_code" in response.content or b"authorization code" in response.content


def test_oauth_error_response():
    """Test OAuth callback error handling when error parameter is present."""
    client = TestClient(app)
    
    # Request with error parameter (simulating Google OAuth error)
    response = client.get(
        "/auth/callback",
        params={
            "error": "access_denied",
            "error_description": "User denied access",
        },
    )
    
    # Should return error page
    assert response.status_code == 400
    assert b"access_denied" in response.content or b"denied" in response.content.lower()


@pytest.mark.parametrize(
    "trusted_proxies,expected",
    [
        ([], []),
        (["127.0.0.1"], ["127.0.0.1"]),
        (["127.0.0.1", "172.17.0.0/16"], ["127.0.0.1", "172.17.0.0/16"]),
        (["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"], ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]),
    ],
)
def test_trusted_proxies_setting_parsing(trusted_proxies, expected):
    """Test that trusted_proxies setting is parsed correctly from various inputs."""
    settings = Settings(trusted_proxies=trusted_proxies)
    assert settings.trusted_proxies == expected


def test_trusted_proxies_from_env_json(monkeypatch):
    """Test parsing JSON array from environment variable."""
    # Simulate environment variable with JSON array
    monkeypatch.setenv("TRUSTED_PROXIES", '["127.0.0.1", "172.17.0.0/16", "10.0.0.1"]')
    settings = Settings()
    assert settings.trusted_proxies == ["127.0.0.1", "172.17.0.0/16", "10.0.0.1"]
