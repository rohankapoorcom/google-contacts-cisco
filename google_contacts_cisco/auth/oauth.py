"""OAuth 2.0 authentication with Google.

This module handles the complete OAuth 2.0 flow for Google authentication:
- Creating OAuth clients
- Generating authorization URLs
- Handling callbacks and token exchange
- Storing and retrieving credentials
- Automatic token refresh
- Credential revocation
"""

import logging
import os
import time
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


class PermanentTokenRefreshError(TokenRefreshError):
    """Raised when token refresh fails permanently (e.g., revoked token).
    
    This indicates that the token cannot be recovered and the user
    must re-authenticate.
    """

    pass


class TransientTokenRefreshError(TokenRefreshError):
    """Raised when token refresh fails temporarily (e.g., network error).
    
    This indicates that the refresh might succeed if retried.
    """

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


def _is_permanent_refresh_error(error: RefreshError) -> bool:
    """Determine if a RefreshError is permanent or transient.
    
    Permanent errors indicate that the token cannot be recovered and
    the user must re-authenticate. Transient errors may succeed if retried.
    
    Args:
        error: The RefreshError to classify
        
    Returns:
        True if the error is permanent, False if it's transient
    """
    error_str = str(error).lower()
    error_description = getattr(error, "error_details", "").lower()
    
    # Permanent error indicators
    permanent_indicators = [
        "invalid_grant",  # Token revoked or expired refresh token
        "invalid_client",  # Invalid client credentials
        "unauthorized_client",  # Client not authorized
        "revoked",  # Token explicitly revoked
        "deleted",  # Refresh token deleted
        "disabled",  # Account disabled
        "malformed",  # Malformed request (likely bad credentials)
    ]
    
    # Check if any permanent indicators are in the error message
    for indicator in permanent_indicators:
        if indicator in error_str or indicator in error_description:
            return True
    
    # If we can't determine, treat as transient (safer - allows retry)
    return False


def _refresh_token_with_retry(
    creds: Credentials,
    max_retries: int = 3,
    initial_backoff: float = 1.0,
) -> tuple[bool, Optional[Exception]]:
    """Attempt to refresh token with exponential backoff retry.
    
    Args:
        creds: Credentials to refresh
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff delay in seconds
        
    Returns:
        Tuple of (success: bool, error: Optional[Exception])
    """
    backoff = initial_backoff
    last_error: Optional[Exception] = None
    
    for attempt in range(max_retries):
        try:
            logger.info(
                "Attempting token refresh (attempt %d/%d)", attempt + 1, max_retries
            )
            creds.refresh(Request())
            logger.info("Access token refreshed successfully")
            return True, None
            
        except RefreshError as e:
            last_error = e
            
            # Check if this is a permanent error
            if _is_permanent_refresh_error(e):
                logger.error("Permanent token refresh error: %s", e)
                return False, e
            
            # Transient error - retry if we have attempts left
            if attempt < max_retries - 1:
                logger.warning(
                    "Transient token refresh error (attempt %d/%d): %s. "
                    "Retrying in %.1f seconds...",
                    attempt + 1,
                    max_retries,
                    e,
                    backoff,
                )
                time.sleep(backoff)
                backoff *= 2  # Exponential backoff
            else:
                logger.error(
                    "Token refresh failed after %d attempts: %s", max_retries, e
                )
                return False, e
                
        except Exception as e:
            # Unexpected errors are treated as transient
            last_error = e
            
            if attempt < max_retries - 1:
                logger.warning(
                    "Unexpected error during token refresh (attempt %d/%d): %s. "
                    "Retrying in %.1f seconds...",
                    attempt + 1,
                    max_retries,
                    e,
                    backoff,
                )
                time.sleep(backoff)
                backoff *= 2
            else:
                logger.error(
                    "Token refresh failed after %d attempts: %s", max_retries, e
                )
                return False, e
    
    return False, last_error


def get_credentials() -> Optional[Credentials]:
    """Get stored credentials or None if not authenticated.

    This function attempts to load credentials from the token file,
    and will automatically refresh them if expired. It distinguishes
    between permanent failures (e.g., revoked token) and transient
    failures (e.g., network issues) and handles them appropriately.

    For permanent failures, the token file is deleted to prevent
    the user from being stuck in an auth limbo state.

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
        # If we can't load the file, it may be corrupted - delete it
        logger.info("Deleting corrupted token file")
        delete_token_file()
        return None

    # Check if credentials are valid
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Try to refresh with retry logic
            success, error = _refresh_token_with_retry(creds)
            
            if success:
                # Save the refreshed credentials
                save_credentials(creds)
                return cast(Credentials, creds)
            
            # Refresh failed - check if it's permanent
            if error and isinstance(error, RefreshError):
                if _is_permanent_refresh_error(error):
                    logger.error(
                        "Permanent token refresh failure. Deleting token file. "
                        "User must re-authenticate."
                    )
                    delete_token_file()
                else:
                    logger.error(
                        "Token refresh failed after retries. "
                        "This may be a transient issue. User should try again later."
                    )
            else:
                logger.error(
                    "Token refresh failed with unexpected error. "
                    "User may need to re-authenticate."
                )
            
            return None
        else:
            logger.debug("Credentials invalid and cannot be refreshed")
            # If credentials are invalid and can't be refreshed, delete the token
            if creds and not creds.refresh_token:
                logger.info("No refresh token available. Deleting token file.")
                delete_token_file()
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

    Args:
        state: Optional state parameter for CSRF protection

    Returns:
        Tuple of (authorization_url, state)
    """
    flow = get_oauth_client()
    authorization_url, generated_state = flow.authorization_url(
        access_type="offline",  # Request refresh token
        include_granted_scopes="true",
        prompt="consent",  # Force consent screen to ensure refresh token
        state=state,
    )
    return authorization_url, generated_state


def handle_oauth_callback(authorization_response: str) -> Credentials:
    """Handle OAuth callback and exchange code for tokens.

    Args:
        authorization_response: Full callback URL with auth code

    Returns:
        Credentials with access and refresh tokens

    Raises:
        TokenExchangeError: If token exchange fails
    """
    try:
        flow = get_oauth_client()
        flow.fetch_token(authorization_response=authorization_response)

        creds: Credentials = flow.credentials
        save_credentials(creds)

        logger.info("OAuth callback processed successfully")
        return creds
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

