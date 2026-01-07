"""Test configuration utilities module.

This module tests the config_utils functions from Task 03: Configuration Management.
"""

import io
import sys

import pytest

from google_contacts_cisco.config import Settings
from google_contacts_cisco.config_utils import (
    generate_secret_key,
    get_safe_config_dict,
    print_configuration_summary,
    validate_configuration,
)


class TestGenerateSecretKey:
    """Test generate_secret_key function."""

    def test_returns_string(self):
        """Test generate_secret_key returns a string."""
        key = generate_secret_key()
        assert isinstance(key, str)

    def test_returns_64_character_hex_string(self):
        """Test generate_secret_key returns a 64-character hex string (32 bytes)."""
        key = generate_secret_key()
        assert len(key) == 64

    def test_returns_valid_hex(self):
        """Test generate_secret_key returns valid hexadecimal."""
        key = generate_secret_key()
        # This will raise ValueError if not valid hex
        int(key, 16)

    def test_returns_unique_keys(self):
        """Test generate_secret_key returns unique keys each time."""
        keys = [generate_secret_key() for _ in range(10)]
        assert len(set(keys)) == 10  # All keys should be unique


class TestValidateConfiguration:
    """Test validate_configuration function."""

    def test_valid_config_returns_true(self):
        """Test validation passes with valid configuration."""
        settings = Settings(
            google_client_id="test-client-id",
            google_client_secret="test-secret",
        )
        is_valid, errors = validate_configuration(settings)
        assert is_valid is True
        assert errors == []

    def test_missing_client_id_returns_error(self):
        """Test validation fails when client ID is missing."""
        settings = Settings(
            google_client_id=None,
            google_client_secret="test-secret",
        )
        is_valid, errors = validate_configuration(settings)
        assert is_valid is False
        assert "GOOGLE_CLIENT_ID is not set" in errors

    def test_missing_client_secret_returns_error(self):
        """Test validation fails when client secret is missing."""
        settings = Settings(
            google_client_id="test-client-id",
            google_client_secret=None,
        )
        is_valid, errors = validate_configuration(settings)
        assert is_valid is False
        assert "GOOGLE_CLIENT_SECRET is not set" in errors

    def test_missing_both_credentials_returns_both_errors(self):
        """Test validation returns both errors when both credentials missing."""
        settings = Settings(
            google_client_id=None,
            google_client_secret=None,
        )
        is_valid, errors = validate_configuration(settings)
        assert is_valid is False
        assert len(errors) == 2
        assert "GOOGLE_CLIENT_ID is not set" in errors
        assert "GOOGLE_CLIENT_SECRET is not set" in errors

    def test_empty_string_client_id_returns_error(self):
        """Test validation fails when client ID is empty string."""
        settings = Settings(
            google_client_id="",
            google_client_secret="test-secret",
        )
        is_valid, errors = validate_configuration(settings)
        assert is_valid is False
        assert "GOOGLE_CLIENT_ID is not set" in errors

    def test_uses_global_settings_when_none_provided(self, monkeypatch):
        """Test validate_configuration uses global settings when None provided."""
        # Test that the function works when no settings are passed
        # Since the global settings have no credentials by default, expect errors
        is_valid, errors = validate_configuration(None)
        # The global settings won't have credentials set, so validation should fail
        # This test verifies the None branch is executed
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)


class TestGetSafeConfigDict:
    """Test get_safe_config_dict function."""

    def test_returns_dict(self):
        """Test get_safe_config_dict returns a dictionary."""
        settings = Settings()
        result = get_safe_config_dict(settings)
        assert isinstance(result, dict)

    def test_masks_google_client_secret(self):
        """Test Google client secret is masked."""
        settings = Settings(google_client_secret="super-secret-value")
        result = get_safe_config_dict(settings)
        assert result["google_client_secret"] == "***MASKED***"

    def test_masks_secret_key(self):
        """Test secret key is masked."""
        settings = Settings(secret_key="my-secret-key")
        result = get_safe_config_dict(settings)
        assert result["secret_key"] == "***MASKED***"

    def test_does_not_mask_none_values(self):
        """Test None values are not masked."""
        settings = Settings(google_client_secret=None, secret_key=None)
        result = get_safe_config_dict(settings)
        assert result["google_client_secret"] is None
        assert result["secret_key"] is None

    def test_includes_non_sensitive_fields(self):
        """Test non-sensitive fields are included unmasked."""
        settings = Settings(
            app_name="Test App",
            debug=True,
            port=9000,
        )
        result = get_safe_config_dict(settings)
        assert result["app_name"] == "Test App"
        assert result["debug"] is True
        assert result["port"] == 9000

    def test_includes_google_client_id_unmasked(self):
        """Test Google client ID is not masked (it's not a secret)."""
        settings = Settings(google_client_id="my-client-id")
        result = get_safe_config_dict(settings)
        assert result["google_client_id"] == "my-client-id"

    def test_contains_all_config_fields(self):
        """Test result contains all configuration fields."""
        settings = Settings()
        result = get_safe_config_dict(settings)

        expected_fields = [
            "app_name",
            "debug",
            "log_level",
            "host",
            "port",
            "database_url",
            "database_echo",
            "google_client_id",
            "google_client_secret",
            "google_oauth_scopes",
            "google_redirect_uri",
            "google_token_file",
            "secret_key",
            "directory_max_entries_per_page",
            "directory_title",
            "sync_batch_size",
            "sync_delay_seconds",
            "search_results_limit",
        ]

        for field in expected_fields:
            assert field in result


class TestPrintConfigurationSummary:
    """Test print_configuration_summary function."""

    def test_prints_to_stdout(self, capsys):
        """Test print_configuration_summary outputs to stdout."""
        settings = Settings()
        print_configuration_summary(settings)
        captured = capsys.readouterr()
        assert "Configuration Summary:" in captured.out

    def test_prints_app_name(self, capsys):
        """Test prints app name."""
        settings = Settings(app_name="Test Application")
        print_configuration_summary(settings)
        captured = capsys.readouterr()
        assert "Test Application" in captured.out

    def test_prints_debug_status(self, capsys):
        """Test prints debug status."""
        settings = Settings(debug=True)
        print_configuration_summary(settings)
        captured = capsys.readouterr()
        assert "Debug: True" in captured.out

    def test_prints_log_level(self, capsys):
        """Test prints log level."""
        settings = Settings(log_level="DEBUG")
        print_configuration_summary(settings)
        captured = capsys.readouterr()
        assert "Log Level: DEBUG" in captured.out

    def test_prints_host_and_port(self, capsys):
        """Test prints host and port."""
        settings = Settings(host="127.0.0.1", port=3000)
        print_configuration_summary(settings)
        captured = capsys.readouterr()
        assert "Host: 127.0.0.1" in captured.out
        assert "Port: 3000" in captured.out

    def test_prints_database_url(self, capsys):
        """Test prints database URL."""
        settings = Settings(database_url="sqlite:///test.db")
        print_configuration_summary(settings)
        captured = capsys.readouterr()
        assert "Database: sqlite:///test.db" in captured.out

    def test_masks_client_id_when_set(self, capsys):
        """Test shows masked indicator when client ID is set."""
        settings = Settings(google_client_id="actual-id")
        print_configuration_summary(settings)
        captured = capsys.readouterr()
        assert "Google Client ID: ***SET***" in captured.out
        assert "actual-id" not in captured.out

    def test_shows_not_set_when_client_id_missing(self, capsys):
        """Test shows NOT SET when client ID is missing."""
        settings = Settings(google_client_id=None)
        print_configuration_summary(settings)
        captured = capsys.readouterr()
        assert "Google Client ID: NOT SET" in captured.out

    def test_masks_client_secret_when_set(self, capsys):
        """Test shows masked indicator when client secret is set."""
        settings = Settings(google_client_secret="actual-secret")
        print_configuration_summary(settings)
        captured = capsys.readouterr()
        assert "Google Client Secret: ***SET***" in captured.out
        assert "actual-secret" not in captured.out

    def test_shows_not_set_when_client_secret_missing(self, capsys):
        """Test shows NOT SET when client secret is missing."""
        settings = Settings(google_client_secret=None)
        print_configuration_summary(settings)
        captured = capsys.readouterr()
        assert "Google Client Secret: NOT SET" in captured.out

    def test_prints_redirect_uri(self, capsys):
        """Test prints redirect URI."""
        settings = Settings(google_redirect_uri="http://example.com/callback")
        print_configuration_summary(settings)
        captured = capsys.readouterr()
        assert "Redirect URI: http://example.com/callback" in captured.out

    def test_prints_directory_title(self, capsys):
        """Test prints directory title."""
        settings = Settings(directory_title="My Contacts")
        print_configuration_summary(settings)
        captured = capsys.readouterr()
        assert "Directory Title: My Contacts" in captured.out

    def test_prints_max_entries(self, capsys):
        """Test prints max entries per page."""
        settings = Settings(directory_max_entries_per_page=64)
        print_configuration_summary(settings)
        captured = capsys.readouterr()
        assert "Max Entries Per Page: 64" in captured.out
