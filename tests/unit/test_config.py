"""Test configuration module.

This module tests the Settings configuration class from Task 03: Configuration Management.
"""

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from google_contacts_cisco.config import Settings, get_settings


class TestSettingsDefaults:
    """Test default configuration values."""

    def test_app_name_default(self):
        """Test default app name."""
        settings = Settings()
        assert settings.app_name == "Google Contacts Cisco Directory"

    def test_debug_default(self):
        """Test debug mode is disabled by default."""
        settings = Settings()
        assert settings.debug is False

    def test_log_level_default(self):
        """Test default log level is INFO."""
        settings = Settings()
        assert settings.log_level == "INFO"

    def test_host_default(self):
        """Test default host."""
        settings = Settings()
        assert settings.host == "0.0.0.0"

    def test_port_default(self):
        """Test default port."""
        settings = Settings()
        assert settings.port == 8000

    def test_database_url_default(self):
        """Test default database URL."""
        settings = Settings()
        assert settings.database_url == "sqlite:///./data/contacts.db"

    def test_database_echo_default(self):
        """Test database echo is disabled by default."""
        settings = Settings()
        assert settings.database_echo is False

    def test_google_credentials_default_none(self):
        """Test Google credentials are None by default."""
        settings = Settings()
        assert settings.google_client_id is None
        assert settings.google_client_secret is None

    def test_google_oauth_scopes_default(self):
        """Test default OAuth scopes."""
        settings = Settings()
        assert settings.google_oauth_scopes == [
            "https://www.googleapis.com/auth/contacts.readonly"
        ]

    def test_google_redirect_uri_default(self):
        """Test default redirect URI."""
        settings = Settings()
        assert settings.google_redirect_uri == "http://localhost:8000/auth/callback"

    def test_google_token_file_default(self):
        """Test default token file path."""
        settings = Settings()
        assert settings.google_token_file == "./data/token.json"

    def test_secret_key_default_none(self):
        """Test secret key is None by default."""
        settings = Settings()
        assert settings.secret_key is None

    def test_directory_max_entries_default(self):
        """Test default max entries per page."""
        settings = Settings()
        assert settings.directory_max_entries_per_page == 32

    def test_directory_title_default(self):
        """Test default directory title."""
        settings = Settings()
        assert settings.directory_title == "Google Contacts"

    def test_sync_batch_size_default(self):
        """Test default sync batch size."""
        settings = Settings()
        assert settings.sync_batch_size == 100

    def test_sync_delay_default(self):
        """Test default sync delay."""
        settings = Settings()
        assert settings.sync_delay_seconds == 0.1

    def test_search_results_limit_default(self):
        """Test default search results limit."""
        settings = Settings()
        assert settings.search_results_limit == 50

    def test_sync_scheduler_enabled_default(self):
        """Test sync scheduler is disabled by default."""
        settings = Settings()
        assert settings.sync_scheduler_enabled is False

    def test_sync_interval_minutes_default(self):
        """Test default sync interval."""
        settings = Settings()
        assert settings.sync_interval_minutes == 60

    def test_timezone_default(self):
        """Test default timezone is UTC."""
        settings = Settings()
        assert settings.timezone == "UTC"


class TestSettingsFromEnvironment:
    """Test configuration loading from environment variables."""

    def test_debug_from_env(self, monkeypatch):
        """Test loading debug flag from environment."""
        monkeypatch.setenv("DEBUG", "true")
        settings = Settings()
        assert settings.debug is True

    def test_log_level_from_env(self, monkeypatch):
        """Test loading log level from environment."""
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        settings = Settings()
        assert settings.log_level == "DEBUG"

    def test_log_level_case_insensitive(self, monkeypatch):
        """Test log level is case insensitive."""
        monkeypatch.setenv("LOG_LEVEL", "warning")
        settings = Settings()
        assert settings.log_level == "WARNING"

    def test_port_from_env(self, monkeypatch):
        """Test loading port from environment."""
        monkeypatch.setenv("PORT", "3000")
        settings = Settings()
        assert settings.port == 3000

    def test_google_client_id_from_env(self, monkeypatch):
        """Test loading Google client ID from environment."""
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
        settings = Settings()
        assert settings.google_client_id == "test-client-id"

    def test_google_client_secret_from_env(self, monkeypatch):
        """Test loading Google client secret from environment."""
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
        settings = Settings()
        assert settings.google_client_secret == "test-secret"

    def test_database_url_from_env(self, monkeypatch):
        """Test loading database URL from environment."""
        monkeypatch.setenv("DATABASE_URL", "sqlite:///custom.db")
        settings = Settings()
        assert settings.database_url == "sqlite:///custom.db"

    def test_secret_key_from_env(self, monkeypatch):
        """Test loading secret key from environment."""
        monkeypatch.setenv("SECRET_KEY", "my-secret-key")
        settings = Settings()
        assert settings.secret_key == "my-secret-key"

    def test_multiple_env_vars(self, monkeypatch):
        """Test loading multiple environment variables at once."""
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("LOG_LEVEL", "ERROR")
        monkeypatch.setenv("PORT", "9000")
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "multi-test-id")

        settings = Settings()
        assert settings.debug is True
        assert settings.log_level == "ERROR"
        assert settings.port == 9000
        assert settings.google_client_id == "multi-test-id"

    def test_sync_scheduler_enabled_from_env(self, monkeypatch):
        """Test loading sync scheduler enabled from environment."""
        monkeypatch.setenv("SYNC_SCHEDULER_ENABLED", "true")
        settings = Settings()
        assert settings.sync_scheduler_enabled is True

    def test_sync_interval_minutes_from_env(self, monkeypatch):
        """Test loading sync interval from environment."""
        monkeypatch.setenv("SYNC_INTERVAL_MINUTES", "30")
        settings = Settings()
        assert settings.sync_interval_minutes == 30

    def test_timezone_from_env(self, monkeypatch):
        """Test loading timezone from environment."""
        monkeypatch.setenv("TIMEZONE", "America/New_York")
        settings = Settings()
        assert settings.timezone == "America/New_York"


class TestSettingsValidation:
    """Test configuration validation."""

    def test_invalid_log_level_raises_error(self):
        """Test invalid log level raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(log_level="INVALID")
        assert "log_level" in str(exc_info.value).lower()

    def test_port_too_low_raises_error(self):
        """Test port below 1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(port=0)
        assert "port" in str(exc_info.value).lower()

    def test_port_too_high_raises_error(self):
        """Test port above 65535 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(port=65536)
        assert "port" in str(exc_info.value).lower()

    def test_valid_port_boundaries(self):
        """Test valid port boundary values."""
        settings_min = Settings(port=1)
        assert settings_min.port == 1

        settings_max = Settings(port=65535)
        assert settings_max.port == 65535

    def test_max_entries_too_low_raises_error(self):
        """Test max entries below 1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(directory_max_entries_per_page=0)
        assert "max_entries" in str(exc_info.value).lower()

    def test_max_entries_too_high_raises_error(self):
        """Test max entries above 100 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(directory_max_entries_per_page=101)
        assert "max_entries" in str(exc_info.value).lower()

    def test_batch_size_too_low_raises_error(self):
        """Test batch size below 1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(sync_batch_size=0)
        assert "batch_size" in str(exc_info.value).lower()

    def test_batch_size_too_high_raises_error(self):
        """Test batch size above 1000 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(sync_batch_size=1001)
        assert "batch_size" in str(exc_info.value).lower()

    def test_sync_delay_negative_raises_error(self):
        """Test negative sync delay raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(sync_delay_seconds=-0.1)
        assert "sync_delay" in str(exc_info.value).lower()

    def test_sync_delay_zero_is_valid(self):
        """Test zero sync delay is valid."""
        settings = Settings(sync_delay_seconds=0)
        assert settings.sync_delay_seconds == 0

    def test_search_limit_too_low_raises_error(self):
        """Test search limit below 1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(search_results_limit=0)
        assert "search_results_limit" in str(exc_info.value).lower()

    def test_search_limit_too_high_raises_error(self):
        """Test search limit above 500 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(search_results_limit=501)
        assert "search_results_limit" in str(exc_info.value).lower()

    def test_all_valid_log_levels(self):
        """Test all valid log levels are accepted."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in valid_levels:
            settings = Settings(log_level=level)
            assert settings.log_level == level

    def test_sync_interval_too_low_raises_error(self):
        """Test sync interval below 5 minutes raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(sync_interval_minutes=4)
        assert "sync_interval" in str(exc_info.value).lower()

    def test_sync_interval_too_high_raises_error(self):
        """Test sync interval above 1440 minutes raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(sync_interval_minutes=1441)
        assert "sync_interval" in str(exc_info.value).lower()

    def test_sync_interval_valid_boundaries(self):
        """Test valid sync interval boundary values."""
        settings_min = Settings(sync_interval_minutes=5)
        assert settings_min.sync_interval_minutes == 5

        settings_max = Settings(sync_interval_minutes=1440)
        assert settings_max.sync_interval_minutes == 1440

    def test_timezone_valid(self):
        """Test valid timezone is accepted."""
        settings = Settings(timezone="America/New_York")
        assert settings.timezone == "America/New_York"

    def test_timezone_invalid_fallback_to_utc(self, monkeypatch):
        """Test invalid timezone falls back to UTC."""
        # Capture warning logs
        import logging
        import io
        
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        logging.root.addHandler(handler)
        
        settings = Settings(timezone="Invalid/Timezone")
        assert settings.timezone == "UTC"
        
        logging.root.removeHandler(handler)


class TestSettingsProperties:
    """Test Settings property methods."""

    def test_database_path_sqlite(self):
        """Test database_path property with SQLite URL."""
        settings = Settings(database_url="sqlite:///./data/test.db")
        assert settings.database_path == Path("./data/test.db")

    def test_database_path_absolute(self):
        """Test database_path property with absolute path."""
        settings = Settings(database_url="sqlite:////tmp/contacts.db")
        assert settings.database_path == Path("/tmp/contacts.db")

    def test_database_path_non_sqlite(self):
        """Test database_path property with non-SQLite URL returns default."""
        settings = Settings(database_url="postgresql://localhost/db")
        assert settings.database_path == Path("data/contacts.db")

    def test_token_path(self):
        """Test token_path property."""
        settings = Settings(google_token_file="./custom/token.json")
        assert settings.token_path == Path("./custom/token.json")

    def test_ensure_directories_creates_dirs(self, tmp_path):
        """Test ensure_directories creates required directories."""
        db_dir = tmp_path / "db_data"
        token_dir = tmp_path / "token_data"

        settings = Settings(
            database_url=f"sqlite:///{db_dir}/contacts.db",
            google_token_file=str(token_dir / "token.json"),
        )

        # Directories should not exist yet
        assert not db_dir.exists()
        assert not token_dir.exists()

        # Call ensure_directories
        settings.ensure_directories()

        # Directories should now exist
        assert db_dir.exists()
        assert token_dir.exists()


class TestGetSettings:
    """Test get_settings function."""

    def test_get_settings_returns_settings_instance(self):
        """Test get_settings returns a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_returns_new_instance_each_call(self):
        """Test get_settings returns a new instance each time."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is not settings2

    def test_get_settings_respects_env_vars(self, monkeypatch):
        """Test get_settings loads from environment."""
        monkeypatch.setenv("DEBUG", "true")
        settings = get_settings()
        assert settings.debug is True


class TestSettingsModelConfig:
    """Test Settings model configuration."""

    def test_extra_env_vars_ignored(self, monkeypatch):
        """Test extra environment variables are ignored."""
        monkeypatch.setenv("UNKNOWN_SETTING", "value")
        # Should not raise an error
        settings = Settings()
        assert not hasattr(settings, "unknown_setting")

    def test_case_insensitive_env_vars(self, monkeypatch):
        """Test environment variables are case insensitive."""
        monkeypatch.setenv("debug", "true")
        settings = Settings()
        assert settings.debug is True
