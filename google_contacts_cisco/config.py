"""Application configuration."""

from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    # Application Settings
    app_name: str = "Google Contacts Cisco Directory"
    debug: bool = False
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    # Database Settings
    database_url: str = "sqlite:///./data/contacts.db"
    database_echo: bool = False  # Log SQL queries

    # Google OAuth Settings
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_oauth_scopes: list[str] = Field(
        default_factory=lambda: ["https://www.googleapis.com/auth/contacts.readonly"]
    )
    google_redirect_uri: str = "http://localhost:8000/auth/callback"
    google_token_file: str = "./data/token.json"

    # Application Security (Optional)
    # Note: For this single-user application with file-based OAuth token storage,
    # a secret key may not be necessary. Include it if you plan to add:
    # - Multi-user sessions
    # - Signed cookies
    # - CSRF protection for forms
    secret_key: Optional[str] = Field(
        default=None,
        description="Secret key for session management (optional for single-user app)",
    )

    # Cisco Directory Settings
    directory_max_entries_per_page: int = 32  # Max entries per Cisco XML page
    directory_title: str = "Google Contacts"

    # Sync Settings
    sync_batch_size: int = 100  # Number of contacts to process per batch
    sync_delay_seconds: float = 0.1  # Delay between API requests

    # Search Settings
    search_results_limit: int = 50  # Max search results to return

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra environment variables
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port is in valid range."""
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v

    @field_validator("directory_max_entries_per_page")
    @classmethod
    def validate_max_entries(cls, v: int) -> int:
        """Validate max entries per page is reasonable."""
        if not 1 <= v <= 100:
            raise ValueError("Max entries per page must be between 1 and 100")
        return v

    @field_validator("sync_batch_size")
    @classmethod
    def validate_batch_size(cls, v: int) -> int:
        """Validate batch size is reasonable."""
        if not 1 <= v <= 1000:
            raise ValueError("Batch size must be between 1 and 1000")
        return v

    @field_validator("sync_delay_seconds")
    @classmethod
    def validate_sync_delay(cls, v: float) -> float:
        """Validate sync delay is non-negative."""
        if v < 0:
            raise ValueError("Sync delay must be non-negative")
        return v

    @field_validator("search_results_limit")
    @classmethod
    def validate_search_limit(cls, v: int) -> int:
        """Validate search results limit is reasonable."""
        if not 1 <= v <= 500:
            raise ValueError("Search results limit must be between 1 and 500")
        return v

    @property
    def database_path(self) -> Path:
        """Get database file path."""
        if self.database_url.startswith("sqlite:///"):
            db_path = self.database_url.replace("sqlite:///", "")
            return Path(db_path)
        return Path("data/contacts.db")

    @property
    def token_path(self) -> Path:
        """Get token file path."""
        return Path(self.google_token_file)

    def ensure_directories(self) -> None:
        """Ensure required directories exist."""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.parent.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    """Get application settings instance.

    This function creates a new Settings instance each time it's called,
    which allows for proper testing with different configurations.
    For production use, consider caching the settings instance.
    """
    return Settings()


# Global settings instance for convenience
# Note: For testing, use get_settings() or create Settings directly
settings = Settings()
