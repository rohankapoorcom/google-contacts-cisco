"""API routes for OAuth authentication.

This module provides FastAPI endpoints for the OAuth 2.0 flow:
- /auth/google - Initiate OAuth flow
- /auth/callback - Handle OAuth callback
- /auth/status - Check authentication status
- /auth/revoke - Revoke credentials
"""

import logging
from html import escape
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from ..auth.oauth import (
    CredentialsNotConfiguredError,
    TokenExchangeError,
    get_auth_status,
    get_authorization_url,
    handle_oauth_callback,
    is_authenticated,
    revoke_credentials,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


class AuthStatusResponse(BaseModel):
    """Response model for authentication status."""

    authenticated: bool
    has_token_file: bool
    credentials_valid: bool
    credentials_expired: bool
    has_refresh_token: bool
    scopes: list[str]


class RevokeResponse(BaseModel):
    """Response model for credential revocation."""

    success: bool
    message: str


class AuthErrorResponse(BaseModel):
    """Response model for authentication errors."""

    error: str
    detail: str


@router.get("/google", response_class=RedirectResponse)
async def auth_google(
    request: Request,
    redirect_uri: Optional[str] = Query(
        None, description="Optional custom redirect URI after auth"
    ),
) -> RedirectResponse:
    """Initiate Google OAuth flow.

    Redirects the user to Google's consent screen to authorize the application.

    Args:
        request: FastAPI request object
        redirect_uri: Optional URI to redirect to after successful auth

    Returns:
        Redirect to Google's authorization URL

    Raises:
        HTTPException: If OAuth credentials are not configured
    """
    try:
        # Store redirect URI in state if provided (for post-auth redirect)
        state = redirect_uri if redirect_uri else None
        auth_url, _ = get_authorization_url(state=state)
        logger.info("Redirecting user to Google OAuth consent screen")
        return RedirectResponse(url=auth_url, status_code=307)
    except CredentialsNotConfiguredError as e:
        logger.error("OAuth credentials not configured: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Google OAuth credentials not configured. "
            "Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )


@router.get("/callback", response_class=HTMLResponse)
async def auth_callback(
    request: Request,
    code: Optional[str] = Query(None, description="Authorization code"),
    error: Optional[str] = Query(None, description="Error code"),
    error_description: Optional[str] = Query(None, description="Error description"),
    state: Optional[str] = Query(None, description="State parameter for CSRF"),
) -> HTMLResponse:
    """Handle OAuth callback from Google.

    Exchanges the authorization code for access and refresh tokens,
    then displays a success or error page.

    Args:
        request: FastAPI request object
        code: Authorization code from Google
        error: Error code if user denied access
        error_description: Human-readable error description
        state: State parameter (may contain redirect URI)

    Returns:
        HTML page indicating success or failure
    """
    # Check for error response
    if error:
        error_msg = error_description or error
        logger.warning(
            "OAuth callback received error: %s - %s", error, error_description
        )
        return HTMLResponse(
            content=_render_error_page(error, error_msg),
            status_code=400,
        )

    if not code:
        logger.error("OAuth callback received without authorization code")
        return HTMLResponse(
            content=_render_error_page(
                "missing_code", "No authorization code received from Google"
            ),
            status_code=400,
        )

    try:
        # Get full URL for token exchange
        authorization_response = str(request.url)
        handle_oauth_callback(authorization_response)

        logger.info("OAuth authentication completed successfully")

        # Validate redirect is a safe relative path (not protocol-relative)
        redirect_to = "/"
        if state and state.startswith("/") and not state.startswith("//"):
            redirect_to = state

        return HTMLResponse(
            content=_render_success_page(redirect_to),
            status_code=200,
        )
    except TokenExchangeError as e:
        logger.error("Token exchange failed: %s", e)
        return HTMLResponse(
            content=_render_error_page("token_exchange_failed", str(e)),
            status_code=500,
        )
    except CredentialsNotConfiguredError as e:
        logger.error("OAuth credentials not configured: %s", e)
        return HTMLResponse(
            content=_render_error_page("not_configured", str(e)),
            status_code=500,
        )
    except Exception as e:
        logger.exception("Unexpected error during OAuth callback")
        return HTMLResponse(
            content=_render_error_page("unexpected_error", str(e)),
            status_code=500,
        )


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status() -> AuthStatusResponse:
    """Check authentication status.

    Returns detailed information about the current authentication state,
    including whether credentials are valid, expired, and what scopes are granted.

    Returns:
        AuthStatusResponse with authentication details
    """
    status = get_auth_status()
    return AuthStatusResponse(**status)


@router.post("/revoke", response_model=RevokeResponse)
async def auth_revoke() -> RevokeResponse:
    """Revoke authentication and delete tokens.

    Attempts to revoke the OAuth token with Google's servers,
    then deletes the local token file.

    Returns:
        RevokeResponse indicating success or failure
    """
    if not is_authenticated():
        logger.info("Revoke requested but no active credentials")
        return RevokeResponse(
            success=False,
            message="No credentials to revoke",
        )

    success = revoke_credentials()

    if success:
        logger.info("Credentials revoked successfully")
        return RevokeResponse(
            success=True,
            message="Credentials revoked and deleted successfully",
        )
    else:
        logger.warning("Credential revocation may have failed")
        return RevokeResponse(
            success=False,
            message="Credential revocation may have failed",
        )


def _render_success_page(redirect_to: str = "/") -> str:
    """Render HTML success page after OAuth completion.

    Args:
        redirect_to: URL to redirect to from the success page

    Returns:
        HTML content string
    """
    # Escape for safe use in HTML attribute (URL-encode for href)
    safe_redirect = quote(redirect_to, safe="/")

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Authentication Successful</title>
    <style>
        body {{
            font-family: system-ui, -apple-system, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        .container {{
            background: white;
            padding: 2rem 3rem;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 400px;
        }}
        .success-icon {{
            font-size: 4rem;
            margin-bottom: 1rem;
        }}
        h1 {{
            color: #22c55e;
            margin: 0 0 1rem 0;
            font-size: 1.5rem;
        }}
        p {{
            color: #64748b;
            margin: 0 0 1.5rem 0;
            line-height: 1.6;
        }}
        a {{
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 0.75rem 1.5rem;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 500;
            transition: background 0.2s;
        }}
        a:hover {{
            background: #5a67d8;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="success-icon">✅</div>
        <h1>Authentication Successful!</h1>
        <p>Your Google account has been connected. You can now sync contacts.</p>
        <a href="{safe_redirect}">Continue to Application</a>
    </div>
</body>
</html>
"""


def _render_error_page(error: str, detail: str) -> str:
    """Render HTML error page after OAuth failure.

    Args:
        error: Error code
        detail: Human-readable error description

    Returns:
        HTML content string
    """
    # Escape user-controlled content to prevent XSS
    safe_error = escape(error)
    safe_detail = escape(detail)

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Authentication Error</title>
    <style>
        body {{
            font-family: system-ui, -apple-system, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #f87171 0%, #dc2626 100%);
        }}
        .container {{
            background: white;
            padding: 2rem 3rem;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 450px;
        }}
        .error-icon {{
            font-size: 4rem;
            margin-bottom: 1rem;
        }}
        h1 {{
            color: #dc2626;
            margin: 0 0 1rem 0;
            font-size: 1.5rem;
        }}
        p {{
            color: #64748b;
            margin: 0 0 0.5rem 0;
            line-height: 1.6;
        }}
        .error-code {{
            background: #fef2f2;
            color: #991b1b;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            font-family: monospace;
            font-size: 0.875rem;
            margin: 1rem 0;
        }}
        a {{
            display: inline-block;
            background: #64748b;
            color: white;
            padding: 0.75rem 1.5rem;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 500;
            margin-top: 1rem;
            transition: background 0.2s;
        }}
        a:hover {{
            background: #475569;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="error-icon">❌</div>
        <h1>Authentication Failed</h1>
        <p>{safe_detail}</p>
        <div class="error-code">Error: {safe_error}</div>
        <a href="/">Return to Home</a>
    </div>
</body>
</html>
"""
