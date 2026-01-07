"""Authentication package.

This package provides OAuth 2.0 authentication with Google
for accessing Google Contacts API.
"""

from .oauth import (
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

__all__ = [
    # Exceptions
    "OAuthError",
    "CredentialsNotConfiguredError",
    "TokenExchangeError",
    "TokenRefreshError",
    # Functions
    "get_oauth_client",
    "get_credentials",
    "save_credentials",
    "is_authenticated",
    "revoke_credentials",
    "get_authorization_url",
    "handle_oauth_callback",
    "get_scopes",
    "get_token_path",
    "delete_token_file",
    "credentials_to_dict",
    "get_auth_status",
]
