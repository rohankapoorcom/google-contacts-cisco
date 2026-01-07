"""Configuration utilities."""

import secrets
from typing import Any

from .config import Settings, settings


def generate_secret_key() -> str:
    """Generate a secure secret key.

    Returns:
        A cryptographically secure random hex string (64 characters / 32 bytes).
    """
    return secrets.token_hex(32)


def validate_configuration(config: Settings | None = None) -> tuple[bool, list[str]]:
    """Validate configuration for required fields.

    This validation checks for fields that are required for the application
    to function properly but cannot be set to meaningful defaults.

    Args:
        config: Settings instance to validate. Uses global settings if None.

    Returns:
        Tuple of (is_valid, list of error messages).
    """
    if config is None:
        config = settings

    errors: list[str] = []

    # Check Google credentials
    if not config.google_client_id:
        errors.append("GOOGLE_CLIENT_ID is not set")
    if not config.google_client_secret:
        errors.append("GOOGLE_CLIENT_SECRET is not set")

    # Note: SECRET_KEY validation removed since it's optional for single-user app
    # If you implement sessions, add validation here

    return len(errors) == 0, errors


def get_safe_config_dict(config: Settings | None = None) -> dict[str, Any]:
    """Get configuration as a dictionary with sensitive values masked.

    Args:
        config: Settings instance to convert. Uses global settings if None.

    Returns:
        Dictionary with configuration values, sensitive fields masked.
    """
    if config is None:
        config = settings

    # Fields that should be masked
    sensitive_fields = {
        "google_client_secret",
        "secret_key",
    }

    result: dict[str, Any] = {}
    for field_name in type(config).model_fields:
        value = getattr(config, field_name)
        if field_name in sensitive_fields and value:
            result[field_name] = "***MASKED***"
        else:
            result[field_name] = value

    return result


def print_configuration_summary(config: Settings | None = None) -> None:
    """Print configuration summary to stdout (without sensitive values).

    Args:
        config: Settings instance to print. Uses global settings if None.
    """
    if config is None:
        config = settings

    print("Configuration Summary:")
    print(f"  App Name: {config.app_name}")
    print(f"  Debug: {config.debug}")
    print(f"  Log Level: {config.log_level}")
    print(f"  Host: {config.host}")
    print(f"  Port: {config.port}")
    print(f"  Database: {config.database_url}")
    client_id_status = "***SET***" if config.google_client_id else "NOT SET"
    client_secret_status = "***SET***" if config.google_client_secret else "NOT SET"
    print(f"  Google Client ID: {client_id_status}")
    print(f"  Google Client Secret: {client_secret_status}")
    print(f"  Redirect URI: {config.google_redirect_uri}")
    print(f"  Directory Title: {config.directory_title}")
    print(f"  Max Entries Per Page: {config.directory_max_entries_per_page}")

