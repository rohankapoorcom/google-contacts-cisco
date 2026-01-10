"""OAuth 2.0 authentication with Google.

This module handles the complete OAuth 2.0 flow for Google authentication:
- Creating OAuth clients
- Generating authorization URLs with CSRF protection
- Handling callbacks and token exchange
- Storing and retrieving credentials
- Automatic token refresh
- Credential revocation
"""

import json
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, cast

import requests
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow  # type: ignore[import-untyped]

from ..config import settings

logger = logging.getLogger(__name__)


class OAuthError(Exception):
    """Base exception for OAuth-related errors."""

    pass


class CredentialsNotConfiguredError(OAuthError):
    """Raised when OAuth credentials are not configured."""

    pass


class TokenExchangeError(OAuthError):
    """Raised when token exchange fails."""

    pass


class TokenRefreshError(OAuthError):
    """Raised when token refresh fails."""

    pass


class StateValidationError(OAuthError):
    """Raised when OAuth state validation fails (CSRF protection)."""

    pass


def get_scopes() -> list[str]:
    """Get the configured OAuth scopes.

    Returns:
        List of OAuth scope strings
    """
    return settings.google_oauth_scopes


def get_oauth_client() -> Flow:
    """Create OAuth 2.0 client.

    Returns:
        Flow: OAuth flow instance configured for Google

    Raises:
        CredentialsNotConfiguredError: If client credentials are not configured
    """
    if not settings.google_client_id or not settings.google_client_secret:
        raise CredentialsNotConfiguredError(
            "Google OAuth credentials not configured. "
            "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
        )

    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=get_scopes(),
        redirect_uri=settings.google_redirect_uri,
    )

    return flow


def get_token_path() -> Path:
    """Get the path to the token file.

    Returns:
        Path to the token file
    """
    return settings.token_path


def get_state_storage_path() -> Path:
    """Get the path to the OAuth state storage directory.

    Returns:
        Path to the state storage directory
    """
    return settings.token_path.parent / "oauth_states"


def _ensure_state_storage_exists() -> None:
    """Ensure the state storage directory exists with secure permissions."""
    state_dir = get_state_storage_path()
    state_dir.mkdir(parents=True, exist_ok=True)
    # Set directory permissions (owner read/write/execute only)
    try:
        os.chmod(state_dir, 0o700)
    except OSError as e:
        logger.warning("Could not set directory permissions: %s", e)


def _generate_state() -> str:
    """Generate a cryptographically secure random state parameter.

    Returns:
        Random state string (32 bytes hex = 64 characters)
    """
    return secrets.token_hex(32)


def _save_state(state: str, custom_data: Optional[str] = None) -> None:
    """Save OAuth state for CSRF validation.

    Args:
        state: The state parameter to save
        custom_data: Optional custom data to store with the state (e.g., redirect URI)

    Raises:
        OSError: If unable to write state file
    """
    _ensure_state_storage_exists()
    state_dir = get_state_storage_path()
    state_file = state_dir / f"{state}.json"

    state_data = {
        "state": state,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "custom_data": custom_data,
    }

    with open(state_file, "w") as f:
        json.dump(state_data, f)

    # Set file permissions (owner read/write only)
    try:
        os.chmod(state_file, 0o600)
    except OSError as e:
        logger.warning("Could not set file permissions: %s", e)

    logger.debug("Saved OAuth state: %s", state)


def _validate_and_consume_state(state: str) -> Optional[str]:
    """Validate and consume an OAuth state parameter.

    This function checks if the state exists, is not expired (15 min TTL),
    and then deletes it to prevent reuse (CSRF protection).

    Args:
        state: The state parameter to validate

    Returns:
        The custom_data associated with the state, or None if not present

    Raises:
        StateValidationError: If state is invalid, expired, or not found
    """
    state_dir = get_state_storage_path()
    state_file = state_dir / f"{state}.json"

    if not state_file.exists():
        logger.warning("OAuth state not found: %s", state)
        raise StateValidationError("Invalid or expired state parameter")

    try:
        with open(state_file, "r") as f:
            state_data = json.load(f)

        # Validate state matches
        if state_data.get("state") != state:
            logger.error("State mismatch in state file")
            raise StateValidationError("State parameter validation failed")

        # Check if state is expired (15 minute TTL)
        created_at = datetime.fromisoformat(state_data["created_at"])
        age = datetime.now(timezone.utc) - created_at
        if age > timedelta(minutes=15):
            logger.warning("OAuth state expired (age: %s)", age)
            raise StateValidationError("State parameter has expired")

        # State is valid, consume it (delete to prevent reuse)
        state_file.unlink()
        logger.info("OAuth state validated and consumed: %s", state)

        return state_data.get("custom_data")

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error("Error reading state file: %s", e)
        # Try to clean up invalid state file
        try:
            state_file.unlink()
        except OSError:
            pass
        raise StateValidationError("State validation failed due to corrupted data") from e
    finally:
        # Clean up expired states (best effort)
        _cleanup_expired_states()


def _cleanup_expired_states() -> None:
    """Clean up expired OAuth state files.

    Removes state files older than 15 minutes. This is called opportunistically
    during state validation to keep the state directory clean.
    """
    try:
        state_dir = get_state_storage_path()
        if not state_dir.exists():
            return

        now = datetime.now(timezone.utc)
        for state_file in state_dir.glob("*.json"):
            try:
                # Check file age
                mtime = datetime.fromtimestamp(state_file.stat().st_mtime, tz=timezone.utc)
                age = now - mtime
                if age > timedelta(minutes=15):
                    state_file.unlink()
                    logger.debug("Cleaned up expired state file: %s", state_file.name)
            except (OSError, ValueError) as e:
                logger.debug("Error cleaning up state file %s: %s", state_file.name, e)
    except Exception as e:
        # Don't let cleanup errors affect the main flow
        logger.debug("Error during state cleanup: %s", e)


def get_credentials() -> Optional[Credentials]:
    """Get stored credentials or None if not authenticated.

    This function attempts to load credentials from the token file,
    and will automatically refresh them if expired.

    Returns:
        Credentials if authenticated and valid, None otherwise
    """
    token_path = get_token_path()

    if not token_path.exists():
        logger.debug("Token file does not exist at %s", token_path)
        return None

    try:
        creds = Credentials.from_authorized_user_file(str(token_path), get_scopes())
    except Exception as e:
        logger.error("Error loading credentials from %s: %s", token_path, e)
        return None

    # Check if credentials are valid
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Try to refresh
            try:
                logger.info("Refreshing expired access token")
                creds.refresh(Request())
                save_credentials(creds)
                logger.info("Access token refreshed successfully")
                return cast(Credentials, creds)
            except RefreshError as e:
                logger.error("Error refreshing token: %s", e)
                return None
            except Exception as e:
                logger.error("Unexpected error during token refresh: %s", e)
                return None
        else:
            logger.debug("Credentials invalid and cannot be refreshed")
            return None

    return cast(Credentials, creds)


def save_credentials(creds: Credentials) -> None:
    """Save credentials to file with secure permissions.

    Args:
        creds: Credentials to save

    Raises:
        OSError: If unable to write to the token file
    """
    token_path = get_token_path()

    # Ensure directory exists
    token_path.parent.mkdir(parents=True, exist_ok=True)

    # Save credentials
    with open(token_path, "w") as token_file:
        token_file.write(creds.to_json())

    # Set file permissions (owner read/write only) - 0o600
    try:
        os.chmod(token_path, 0o600)
    except OSError as e:
        # On Windows, chmod may not work as expected
        logger.warning("Could not set file permissions: %s", e)

    logger.info("Credentials saved to %s", token_path)


def delete_token_file() -> bool:
    """Delete the token file if it exists.

    Returns:
        True if file was deleted, False if it didn't exist
    """
    token_path = get_token_path()

    if token_path.exists():
        token_path.unlink()
        logger.info("Token file deleted: %s", token_path)
        return True

    return False


def is_authenticated() -> bool:
    """Check if user is authenticated with valid credentials.

    Returns:
        True if authenticated with valid credentials
    """
    creds = get_credentials()
    return creds is not None and creds.valid


def revoke_credentials() -> bool:
    """Revoke and delete stored credentials.

    This will attempt to revoke the token with Google's servers,
    then delete the local token file regardless of revocation success.

    Returns:
        True if credentials were deleted
    """
    creds = get_credentials()
    revoked = False

    if creds and creds.token:
        # Attempt to revoke the token with Google
        try:
            response = requests.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": creds.token},
                headers={"content-type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
            if response.status_code == 200:
                logger.info("Token revoked successfully with Google")
                revoked = True
            else:
                logger.warning(
                    "Token revocation returned status %s: %s",
                    response.status_code,
                    response.text,
                )
        except requests.RequestException as e:
            logger.error("Error revoking token: %s", e)

    # Delete token file regardless of revocation result
    deleted = delete_token_file()

    return deleted or revoked


def get_authorization_url(state: Optional[str] = None) -> tuple[str, str]:
    """Get the authorization URL to start OAuth flow.

    Generates a cryptographically secure state parameter and stores it for
    later validation to protect against CSRF attacks.

    Args:
        state: Optional custom data to associate with the state (e.g., redirect URI)

    Returns:
        Tuple of (authorization_url, generated_state)
    """
    flow = get_oauth_client()

    # Generate a secure random state parameter
    generated_state = _generate_state()

    # Store the state with optional custom data for CSRF validation
    _save_state(generated_state, custom_data=state)

    # Generate authorization URL with the state parameter
    authorization_url, _ = flow.authorization_url(
        access_type="offline",  # Request refresh token
        include_granted_scopes="true",
        prompt="consent",  # Force consent screen to ensure refresh token
        state=generated_state,  # Use our generated state for CSRF protection
    )

    return authorization_url, generated_state


def handle_oauth_callback(authorization_response: str) -> tuple[Credentials, Optional[str]]:
    """Handle OAuth callback and exchange code for tokens.

    Validates the state parameter for CSRF protection before exchanging
    the authorization code for tokens.

    Args:
        authorization_response: Full callback URL with auth code and state

    Returns:
        Tuple of (Credentials, custom_data) where custom_data is the optional
        data that was stored with the state (e.g., redirect URI)

    Raises:
        StateValidationError: If state validation fails
        TokenExchangeError: If token exchange fails
    """
    try:
        # Extract state from the authorization response for validation
        from urllib.parse import parse_qs, urlparse

        parsed_url = urlparse(authorization_response)
        query_params = parse_qs(parsed_url.query)
        state = query_params.get("state", [None])[0]

        if not state:
            raise StateValidationError("Missing state parameter in OAuth callback")

        # Validate and consume the state (CSRF protection)
        custom_data = _validate_and_consume_state(state)

        # State is valid, proceed with token exchange
        flow = get_oauth_client()
        flow.fetch_token(authorization_response=authorization_response)

        creds: Credentials = flow.credentials
        save_credentials(creds)

        logger.info("OAuth callback processed successfully")
        return creds, custom_data
    except StateValidationError:
        # Re-raise state validation errors as-is
        raise
    except Exception as e:
        logger.error("Token exchange failed: %s", e)
        raise TokenExchangeError(f"Token exchange failed: {e}") from e


def credentials_to_dict(creds: Credentials) -> dict:
    """Convert credentials to a dictionary for serialization.

    Args:
        creds: Credentials object

    Returns:
        Dictionary representation of credentials
    """
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else [],
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }


def get_auth_status() -> dict:
    """Get detailed authentication status.

    Returns:
        Dictionary with authentication status details
    """
    creds = get_credentials()

    if creds is None:
        return {
            "authenticated": False,
            "has_token_file": get_token_path().exists(),
            "credentials_valid": False,
            "credentials_expired": False,
            "has_refresh_token": False,
            "scopes": [],
        }

    return {
        "authenticated": True,
        "has_token_file": True,
        "credentials_valid": creds.valid,
        "credentials_expired": creds.expired if creds else False,
        "has_refresh_token": bool(creds.refresh_token),
        "scopes": list(creds.scopes) if creds.scopes else [],
    }

