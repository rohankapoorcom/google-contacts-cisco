# Task 2.1: OAuth 2.0 Implementation

## Overview

Implement OAuth 2.0 authentication flow with Google to enable access to the user's Google Contacts. This includes handling authorization, token storage, and automatic token refresh.

## Priority

**P0 (Critical)** - Required for MVP

## Dependencies

- Task 1.1: Environment Setup
- Task 1.3: Configuration Management

## Objectives

1. Implement OAuth 2.0 authorization flow with Google
2. Handle OAuth callback and token exchange
3. Store OAuth tokens securely in file system
4. Implement automatic token refresh
5. Handle token expiration gracefully
6. Create web interface for OAuth setup

## Technical Context

### OAuth 2.0 Flow
1. **Authorization Request**: Redirect user to Google's consent screen
2. **Authorization Grant**: User approves access, Google redirects back with authorization code
3. **Token Exchange**: Exchange authorization code for access token and refresh token
4. **Token Storage**: Save tokens to file system
5. **Token Usage**: Use access token to make API requests
6. **Token Refresh**: Automatically refresh expired access tokens using refresh token

### Google OAuth 2.0 Configuration
- **Scopes**: `https://www.googleapis.com/auth/contacts.readonly`
- **Redirect URI**: `http://localhost:8000/auth/callback` (configurable)
- **Token Storage**: File-based (`./data/token.json`)

### Security Considerations
- Store tokens securely with appropriate file permissions
- Never log or expose tokens
- Handle refresh token carefully (it's long-lived)
- Validate redirect URI to prevent token theft

## Acceptance Criteria

- [ ] OAuth authorization flow redirects to Google correctly
- [ ] Authorization callback handles the auth code properly
- [ ] Tokens are exchanged successfully
- [ ] Tokens are stored in file system with proper permissions
- [ ] Token file is loaded on subsequent requests
- [ ] Expired access tokens are refreshed automatically
- [ ] Refresh token failures trigger re-authorization
- [ ] Web page shows OAuth connection status
- [ ] OAuth errors are handled gracefully with clear messages

## Implementation Steps

### 1. Create OAuth Configuration

Update `google_contacts_cisco/auth/__init__.py`:

```python
"""Authentication module."""
from .oauth import (
    get_oauth_client,
    get_credentials,
    is_authenticated,
    revoke_credentials,
)

__all__ = [
    "get_oauth_client",
    "get_credentials",
    "is_authenticated",
    "revoke_credentials",
]
```

### 2. Implement OAuth Client

Create `google_contacts_cisco/auth/oauth.py`:

```python
"""OAuth 2.0 authentication with Google."""
import json
import os
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from ..config import settings


# OAuth 2.0 scopes
SCOPES = settings.google_oauth_scopes


def get_oauth_client() -> Flow:
    """Create OAuth 2.0 client.
    
    Returns:
        Flow: OAuth flow instance
        
    Raises:
        ValueError: If client credentials are not configured
    """
    if not settings.google_client_id or not settings.google_client_secret:
        raise ValueError(
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
        scopes=SCOPES,
        redirect_uri=settings.google_redirect_uri
    )
    
    return flow


def get_credentials() -> Optional[Credentials]:
    """Get stored credentials or None if not authenticated.
    
    Returns:
        Credentials or None if not authenticated or tokens expired beyond refresh
    """
    token_path = settings.token_path
    
    if not token_path.exists():
        return None
    
    try:
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return None
    
    # Check if credentials are valid
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Try to refresh
            try:
                creds.refresh(Request())
                save_credentials(creds)
                return creds
            except Exception as e:
                print(f"Error refreshing token: {e}")
                return None
        else:
            return None
    
    return creds


def save_credentials(creds: Credentials) -> None:
    """Save credentials to file.
    
    Args:
        creds: Credentials to save
    """
    token_path = settings.token_path
    
    # Ensure directory exists
    token_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save credentials
    with open(token_path, 'w') as token_file:
        token_file.write(creds.to_json())
    
    # Set file permissions (owner read/write only)
    os.chmod(token_path, 0o600)


def is_authenticated() -> bool:
    """Check if user is authenticated with valid credentials.
    
    Returns:
        True if authenticated with valid credentials
    """
    creds = get_credentials()
    return creds is not None and creds.valid


def revoke_credentials() -> bool:
    """Revoke and delete stored credentials.
    
    Returns:
        True if credentials were revoked/deleted
    """
    creds = get_credentials()
    
    if creds and creds.valid:
        # Revoke the token
        try:
            import requests
            requests.post(
                'https://oauth2.googleapis.com/revoke',
                params={'token': creds.token},
                headers={'content-type': 'application/x-www-form-urlencoded'}
            )
        except Exception as e:
            print(f"Error revoking token: {e}")
    
    # Delete token file
    token_path = settings.token_path
    if token_path.exists():
        token_path.unlink()
        return True
    
    return False


def get_authorization_url() -> str:
    """Get the authorization URL to start OAuth flow.
    
    Returns:
        Authorization URL to redirect user to
    """
    flow = get_oauth_client()
    authorization_url, state = flow.authorization_url(
        access_type='offline',  # Request refresh token
        include_granted_scopes='true',
        prompt='consent'  # Force consent screen to get refresh token
    )
    return authorization_url


def handle_oauth_callback(authorization_response: str) -> Credentials:
    """Handle OAuth callback and exchange code for tokens.
    
    Args:
        authorization_response: Full callback URL with auth code
        
    Returns:
        Credentials with access and refresh tokens
        
    Raises:
        Exception: If token exchange fails
    """
    flow = get_oauth_client()
    flow.fetch_token(authorization_response=authorization_response)
    
    creds = flow.credentials
    save_credentials(creds)
    
    return creds
```

### 3. Create OAuth API Endpoints

Update `google_contacts_cisco/api/routes.py`:

```python
"""API routes."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse

from ..auth.oauth import (
    get_authorization_url,
    handle_oauth_callback,
    is_authenticated,
    revoke_credentials,
)

router = APIRouter()


@router.get("/auth/google")
async def auth_google():
    """Initiate Google OAuth flow."""
    try:
        auth_url = get_authorization_url()
        return RedirectResponse(url=auth_url)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/callback")
async def auth_callback(request: Request):
    """Handle OAuth callback from Google."""
    # Get full URL including query parameters
    authorization_response = str(request.url)
    
    # Check for error
    if "error" in request.query_params:
        error = request.query_params.get("error")
        return HTMLResponse(
            content=f"""
            <html>
                <head><title>Authentication Error</title></head>
                <body>
                    <h1>Authentication Failed</h1>
                    <p>Error: {error}</p>
                    <p><a href="/">Go back to home</a></p>
                </body>
            </html>
            """,
            status_code=400
        )
    
    try:
        # Exchange code for tokens
        handle_oauth_callback(authorization_response)
        
        return HTMLResponse(
            content="""
            <html>
                <head><title>Authentication Successful</title></head>
                <body>
                    <h1>Authentication Successful!</h1>
                    <p>You have successfully connected your Google account.</p>
                    <p><a href="/">Go to home page</a></p>
                </body>
            </html>
            """
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token exchange failed: {str(e)}")


@router.get("/auth/status")
async def auth_status():
    """Check authentication status."""
    return {
        "authenticated": is_authenticated()
    }


@router.post("/auth/revoke")
async def auth_revoke():
    """Revoke authentication and delete tokens."""
    success = revoke_credentials()
    return {
        "success": success,
        "message": "Credentials revoked" if success else "No credentials to revoke"
    }
```

### 4. Register Routes in Main App

Update `google_contacts_cisco/main.py`:

```python
"""Main application entry point."""
from fastapi import FastAPI
from ._version import __version__
from .api.routes import router

app = FastAPI(
    title="Google Contacts Cisco Directory",
    description="Web application for syncing Google Contacts to Cisco IP Phones",
    version=__version__
)

# Include API routes
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Google Contacts Cisco Directory API"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
```

### 5. Create Tests

Create `tests/test_oauth.py`:

```python
"""Test OAuth functionality."""
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
from google.oauth2.credentials import Credentials

from google_contacts_cisco.auth.oauth import (
    get_oauth_client,
    save_credentials,
    get_credentials,
    is_authenticated,
    revoke_credentials,
)


@pytest.fixture
def mock_credentials():
    """Create mock credentials."""
    return Credentials(
        token="test_access_token",
        refresh_token="test_refresh_token",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="test_client_id",
        client_secret="test_client_secret",
        scopes=["https://www.googleapis.com/auth/contacts.readonly"]
    )


@pytest.fixture
def temp_token_file(tmp_path, monkeypatch):
    """Create temporary token file path."""
    token_path = tmp_path / "token.json"
    
    # Mock settings to use temp path
    from google_contacts_cisco import config
    monkeypatch.setattr(config.settings, "token_path", token_path)
    
    return token_path


def test_get_oauth_client(monkeypatch):
    """Test OAuth client creation."""
    from google_contacts_cisco import config
    monkeypatch.setattr(config.settings, "google_client_id", "test_id")
    monkeypatch.setattr(config.settings, "google_client_secret", "test_secret")
    
    flow = get_oauth_client()
    assert flow is not None


def test_save_and_load_credentials(temp_token_file, mock_credentials):
    """Test saving and loading credentials."""
    # Save credentials
    save_credentials(mock_credentials)
    
    # Check file exists
    assert temp_token_file.exists()
    
    # Load credentials
    loaded_creds = Credentials.from_authorized_user_file(str(temp_token_file))
    assert loaded_creds.token == mock_credentials.token
    assert loaded_creds.refresh_token == mock_credentials.refresh_token


def test_is_authenticated_no_token(temp_token_file):
    """Test authentication check when no token exists."""
    assert not is_authenticated()


def test_revoke_credentials(temp_token_file, mock_credentials):
    """Test credential revocation."""
    # Save credentials
    save_credentials(mock_credentials)
    assert temp_token_file.exists()
    
    # Revoke
    with patch('google_contacts_cisco.auth.oauth.requests.post'):
        success = revoke_credentials()
    
    assert success
    assert not temp_token_file.exists()
```

Create `tests/test_oauth_api.py`:

```python
"""Test OAuth API endpoints."""
from unittest.mock import patch

from fastapi.testclient import TestClient

from google_contacts_cisco.main import app

client = TestClient(app)


def test_auth_status_not_authenticated():
    """Test auth status when not authenticated."""
    with patch('google_contacts_cisco.api.routes.is_authenticated', return_value=False):
        response = client.get("/auth/status")
        assert response.status_code == 200
        assert response.json() == {"authenticated": False}


def test_auth_google_redirect():
    """Test Google OAuth initiation."""
    with patch('google_contacts_cisco.api.routes.get_authorization_url', return_value="https://google.com/auth"):
        response = client.get("/auth/google", follow_redirects=False)
        assert response.status_code == 307  # Redirect
        assert "google.com" in response.headers["location"]


def test_auth_callback_success():
    """Test successful OAuth callback."""
    with patch('google_contacts_cisco.api.routes.handle_oauth_callback'):
        response = client.get("/auth/callback?code=test_code&state=test_state")
        assert response.status_code == 200
        assert "Successful" in response.text


def test_auth_callback_error():
    """Test OAuth callback with error."""
    response = client.get("/auth/callback?error=access_denied")
    assert response.status_code == 400
    assert "Failed" in response.text
```


## Testing Requirements

**⚠️ Critical**: This task is not complete until comprehensive unit tests are written and passing.

### Test Coverage Requirements
- All functions and methods must have tests
- Both success and failure paths must be covered
- Edge cases and boundary conditions must be tested
- **Minimum coverage: 80% for this module**
- **Target coverage: 85%+ for services, 90%+ for utilities**

### Test Files to Create
Create test file(s) in `tests/unit/` matching your implementation structure:

```
Implementation File              →  Test File
─────────────────────────────────────────────────────────────
[implementation path]            →  tests/unit/[same structure]/test_[filename].py
```

### Test Structure Template
```python
"""Test [module name].

This module tests the [feature] implementation from this task.
"""
import pytest
from google_contacts_cisco.[module] import [Component]


class Test[FeatureName]:
    """Test [feature] functionality."""
    
    def test_typical_use_case(self):
        """Test the main success path."""
        # Arrange
        input_data = ...
        
        # Act
        result = component.method(input_data)
        
        # Assert
        assert result == expected
    
    def test_handles_invalid_input(self):
        """Test error handling for invalid input."""
        with pytest.raises(ValueError):
            component.method(invalid_input)
    
    def test_edge_case_empty_data(self):
        """Test behavior with empty/null data."""
        result = component.method([])
        assert result == []
    
    def test_edge_case_boundary_values(self):
        """Test boundary conditions."""
        ...
```

### What to Test
- ✅ **Success paths**: Typical use cases and expected inputs
- ✅ **Error paths**: Invalid inputs, exceptions, error conditions
- ✅ **Edge cases**: Empty data, null values, boundary conditions, large datasets
- ✅ **Side effects**: Database changes, file operations, API calls
- ✅ **Return values**: Correct types, formats, and values
- ✅ **State changes**: Object state, system state

### Testing Best Practices
- Use descriptive test names that explain what is being tested
- Follow Arrange-Act-Assert pattern
- Use fixtures from `tests/conftest.py` for common test data
- Mock external dependencies (APIs, databases, file system)
- Keep tests independent (no shared state)
- Make tests fast (< 5 seconds per test file)
- Test behavior, not implementation details

### Running Your Tests
```bash
# Run tests for this specific module
uv run pytest tests/unit/[your_test_file].py -v

# Run with coverage report
uv run pytest tests/unit/[your_test_file].py \
    --cov=google_contacts_cisco.[your_module] \
    --cov-report=term-missing

# Run in watch mode (re-run on file changes)
uv run pytest-watch tests/unit/[your_directory]/ -v
```

### Acceptance Criteria Additions
- [ ] All new code has corresponding tests
- [ ] Tests cover success cases, error cases, and edge cases
- [ ] All tests pass (`pytest tests/unit/[module]/ -v`)
- [ ] Coverage is >80% for this module
- [ ] Tests are independent and can run in any order
- [ ] External dependencies are properly mocked
- [ ] Test names clearly describe what is being tested

### Example Test Scenarios for This Task
- Test OAuth authorization URL generation
- Test token exchange from authorization code
- Test token refresh logic
- Test token storage and retrieval
- Test error handling for invalid tokens


## Verification

After completing this task:

1. **Manual Testing**:
   ```bash
   # Start the application
   uvicorn google_contacts_cisco.main:app --reload
   
   # Visit http://localhost:8000/auth/google
   # - Should redirect to Google consent screen
   # - Grant access
   # - Should redirect back with success message
   
   # Check auth status
   curl http://localhost:8000/auth/status
   # Should return {"authenticated": true}
   
   # Check token file
   ls -la data/token.json
   # File should exist with 600 permissions
   ```

2. **Automated Tests**:
   ```bash
   pytest tests/test_oauth.py tests/test_oauth_api.py -v
   ```

3. **Token File Format**:
   ```bash
   cat data/token.json
   # Should contain valid JSON with token, refresh_token, etc.
   ```

## Notes

- **Refresh Token**: Google only provides refresh token on first authorization with `prompt=consent`
- **Token Expiration**: Access tokens expire after 1 hour, refresh tokens are long-lived
- **File Permissions**: Token file has 600 permissions (owner read/write only)
- **Offline Access**: Using `access_type='offline'` to get refresh token
- **Scope Changes**: If scopes change, user must re-authorize
- **Error Handling**: Clear error messages guide users when OAuth fails

## Security Best Practices

1. Never log or expose tokens
2. Store tokens with restricted file permissions (600)
3. Validate redirect URI matches configuration
4. Use HTTPS in production
5. Handle token refresh before they expire
6. Revoke tokens when no longer needed

## Related Documentation

- Google OAuth 2.0: https://developers.google.com/identity/protocols/oauth2
- Google Python Auth Library: https://google-auth.readthedocs.io/
- OAuth 2.0 RFC: https://tools.ietf.org/html/rfc6749
- FastAPI OAuth: https://fastapi.tiangolo.com/advanced/security/

## Estimated Time

4-6 hours

