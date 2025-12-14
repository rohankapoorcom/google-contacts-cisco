# Task 1.3: Configuration Management

## Overview

Set up configuration management system using Pydantic Settings for type-safe, environment-based configuration.

## Priority

**P0 (Critical)** - Required for MVP

## Dependencies

- Task 1.1: Environment Setup (must be completed first)

## Objectives

1. Set up environment variable handling with python-dotenv
2. Create type-safe configuration schema with Pydantic
3. Create `.env.example` template
4. Document all configuration options
5. Implement configuration validation

## Technical Context

### Configuration Sources (Priority Order)
1. Environment variables
2. `.env` file
3. Default values

### Configuration Categories
- **Database**: Connection string, pool settings
- **Google API**: Client ID, client secret, scopes
- **Application**: Debug mode, log level, server settings
- **Security**: Secret key, token storage path
- **Cisco**: Directory settings, pagination limits

## Acceptance Criteria

- [ ] Pydantic Settings is configured
- [ ] `.env.example` file is created with all configuration options
- [ ] Configuration schema includes type hints and validation
- [ ] Configuration can be loaded from environment variables
- [ ] Configuration can be loaded from `.env` file
- [ ] Invalid configuration raises clear validation errors
- [ ] Sensitive values are not logged or displayed
- [ ] Documentation explains each configuration option

## Implementation Steps

### 1. Enhance config.py

Update `google_contacts_cisco/config.py`:

```python
"""Application configuration."""
from pathlib import Path
from typing import Optional
from pydantic import Field, validator
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
        default_factory=lambda: [
            "https://www.googleapis.com/auth/contacts.readonly"
        ]
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
        description="Secret key for session management (optional for single-user app)"
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
        extra="ignore"  # Ignore extra environment variables
    )
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v
    
    # Note: Removed secret_key validator since it's optional for this single-user application
    # If you add session management later, uncomment and use this validator:
    # @validator("secret_key")
    # def validate_secret_key(cls, v, values):
    #     """Validate secret key in production."""
    #     if not values.get("debug", False) and (v is None or v == "change-me-in-production-to-a-random-secret-key"):
    #         raise ValueError("Must set SECRET_KEY if using session management")
    #     return v
    
    @validator("google_client_id", "google_client_secret")
    def validate_google_credentials(cls, v, field):
        """Validate Google credentials are set."""
        if v is None or not v.strip():
            raise ValueError(f"{field.name} must be set for Google OAuth")
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
    
    def ensure_directories(self):
        """Ensure required directories exist."""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.parent.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()

# Ensure required directories exist
settings.ensure_directories()
```

### 2. Create .env.example

Create `.env.example` in project root:

```env
# Application Settings
APP_NAME="Google Contacts Cisco Directory"
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000

# Database Settings
DATABASE_URL=sqlite:///./data/contacts.db
DATABASE_ECHO=false

# Google OAuth 2.0 Settings
# Get these from: https://console.cloud.google.com/apis/credentials
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
GOOGLE_TOKEN_FILE=./data/token.json

# Scopes (comma-separated if multiple)
# GOOGLE_OAUTH_SCOPES=https://www.googleapis.com/auth/contacts.readonly

# Application Security (Optional)
# Only needed if you implement session management or signed cookies
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
# SECRET_KEY=your-secret-key-here

# Cisco Directory Settings
DIRECTORY_MAX_ENTRIES_PER_PAGE=32
DIRECTORY_TITLE="Google Contacts"

# Sync Settings
SYNC_BATCH_SIZE=100
SYNC_DELAY_SECONDS=0.1

# Search Settings
SEARCH_RESULTS_LIMIT=50
```

### 3. Create Configuration Documentation

Create `docs/configuration.md`:

```markdown
# Configuration Guide

## Overview

The application is configured using environment variables or a `.env` file. All settings have sensible defaults, but some (like Google OAuth credentials) must be set before running the application.

## Architecture Note: Single-User Application

This is a **single-user application** designed to sync one Google account's contacts to Cisco IP Phones. Because of this:

- **No user sessions**: OAuth tokens are stored in a file, not cookies
- **No multi-user authentication**: Only one Google account per instance
- **Stateless APIs**: Directory and search endpoints don't require sessions
- **Simple OAuth flow**: User authenticates once, tokens persist to disk

Therefore, many security features common in multi-user web apps (session management, CSRF protection, signed cookies) are **not required**.

## Required Settings

### Google OAuth Credentials

You must obtain OAuth 2.0 credentials from Google Cloud Console:

1. Go to https://console.cloud.google.com/apis/credentials
2. Create a new OAuth 2.0 Client ID
3. Set authorized redirect URI to `http://localhost:8000/auth/callback` (or your domain)
4. Copy the Client ID and Client Secret
5. Set them in your `.env` file:

```env
GOOGLE_CLIENT_ID=your_client_id_here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret_here
```

### Secret Key (Optional)

**Note**: For this single-user application, a secret key is **optional** and only needed if you plan to implement:
- Session-based authentication in the web frontend
- Signed cookies
- CSRF protection for forms

If you don't need these features, you can skip setting the SECRET_KEY.

If you do need it later, generate a secure secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Set it in your `.env` file:

```env
SECRET_KEY=your_generated_secret_key_here
```

## All Configuration Options

[Document each setting from .env.example here]

## Environment-Specific Configurations

### Development

Use default settings with debug mode enabled:

```env
DEBUG=true
LOG_LEVEL=DEBUG
DATABASE_ECHO=true
```

### Production

Use secure settings:

```env
DEBUG=false
LOG_LEVEL=INFO
# SECRET_KEY is optional for single-user app
# Only set if implementing sessions:
# SECRET_KEY=<secure-random-key>
```

## Loading Configuration

Configuration is loaded automatically when the application starts. You can verify configuration by running:

```python
from google_contacts_cisco.config import settings
print(settings.model_dump())
```
```

### 4. Add Configuration Utilities

Create `google_contacts_cisco/config_utils.py`:

```python
"""Configuration utilities."""
import secrets
from .config import settings


def generate_secret_key() -> str:
    """Generate a secure secret key."""
    return secrets.token_hex(32)


def validate_configuration() -> tuple[bool, list[str]]:
    """Validate configuration.
    
    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []
    
    # Check Google credentials
    if not settings.google_client_id:
        errors.append("GOOGLE_CLIENT_ID is not set")
    if not settings.google_client_secret:
        errors.append("GOOGLE_CLIENT_SECRET is not set")
    
    # Note: SECRET_KEY validation removed since it's optional for single-user app
    # If you implement sessions, add validation here
    
    return len(errors) == 0, errors


def print_configuration_summary():
    """Print configuration summary (without sensitive values)."""
    print("Configuration Summary:")
    print(f"  App Name: {settings.app_name}")
    print(f"  Debug: {settings.debug}")
    print(f"  Log Level: {settings.log_level}")
    print(f"  Host: {settings.host}")
    print(f"  Port: {settings.port}")
    print(f"  Database: {settings.database_url}")
    print(f"  Google Client ID: {'***' if settings.google_client_id else 'NOT SET'}")
    print(f"  Google Client Secret: {'***' if settings.google_client_secret else 'NOT SET'}")
    print(f"  Redirect URI: {settings.google_redirect_uri}")
```

### 5. Add Configuration Validation to Startup

Update `google_contacts_cisco/main.py`:

```python
"""Main application entry point."""
from fastapi import FastAPI
from .config import settings
from .config_utils import validate_configuration, print_configuration_summary

app = FastAPI(
    title=settings.app_name,
    description="Web application for syncing Google Contacts to Cisco IP Phones",
    version="0.1.0",
    debug=settings.debug
)


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    print_configuration_summary()
    
    is_valid, errors = validate_configuration()
    if not is_valid:
        print("\nConfiguration Errors:")
        for error in errors:
            print(f"  - {error}")
        if not settings.debug:
            raise RuntimeError("Invalid configuration. Please fix the errors above.")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": settings.app_name}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "debug": settings.debug}
```

### 6. Create Tests

Create `tests/test_config.py`:

```python
"""Test configuration."""
import pytest
from pydantic import ValidationError
from google_contacts_cisco.config import Settings


def test_default_configuration():
    """Test default configuration values."""
    settings = Settings()
    assert settings.app_name == "Google Contacts Cisco Directory"
    assert settings.debug is False
    assert settings.log_level == "INFO"


def test_configuration_from_env(monkeypatch):
    """Test configuration from environment variables."""
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
    
    settings = Settings()
    assert settings.debug is True
    assert settings.log_level == "DEBUG"
    assert settings.google_client_id == "test-client-id"


def test_invalid_log_level():
    """Test invalid log level raises validation error."""
    with pytest.raises(ValidationError):
        Settings(log_level="INVALID")


def test_secret_key_validation_in_production():
    """Test secret key must be changed in production."""
    with pytest.raises(ValidationError):
        Settings(debug=False, google_client_id="test", google_client_secret="test")
```

## Verification

After completing this task:
1. Copy `.env.example` to `.env` and set required values
2. Run the application - should start without errors
3. Configuration validation should work
4. Tests should pass: `pytest tests/test_config.py`
5. Configuration summary should print on startup

## Notes

- Never commit `.env` file to version control
- Use `.env.example` as a template
- Sensitive values should not be logged or printed
- Configuration should be validated on startup
- Use type hints for all configuration options

## Related Documentation

- Pydantic Settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- python-dotenv: https://github.com/theskumar/python-dotenv
- Twelve-Factor App Config: https://12factor.net/config

## Estimated Time

2-3 hours

