"""Google API routes.

This module provides FastAPI endpoints for interacting with the Google People API:
- /api/test-connection - Test connection to Google People API
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..auth.oauth import is_authenticated
from ..services.google_client import (
    CredentialsError,
    RateLimitError,
    ServerError,
    get_google_client,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["google"])


class TestConnectionResponse(BaseModel):
    """Response model for connection test."""

    status: str
    message: str
    total_contacts: Optional[int] = None


class ErrorResponse(BaseModel):
    """Response model for errors."""

    status: str
    message: str
    error_type: str


@router.get(
    "/test-connection",
    response_model=TestConnectionResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        500: {"model": ErrorResponse, "description": "Connection test failed"},
    },
)
async def test_google_connection() -> TestConnectionResponse:
    """Test connection to Google People API.

    Verifies that the application can successfully connect to
    Google People API with the stored credentials.

    Returns:
        TestConnectionResponse with status and connection details

    Raises:
        HTTPException: If not authenticated or connection fails
    """
    if not is_authenticated():
        logger.warning("Connection test attempted without authentication")
        raise HTTPException(
            status_code=401,
            detail="Not authenticated. Please connect your Google account first.",
        )

    try:
        client = get_google_client()
        client.test_connection()

        # Try to get connection count
        try:
            total = client.get_total_connections_count()
        except Exception:
            total = None

        logger.info("Connection test successful")
        return TestConnectionResponse(
            status="success",
            message="Successfully connected to Google People API",
            total_contacts=total,
        )
    except CredentialsError as e:
        logger.error("Credentials error during connection test: %s", e)
        raise HTTPException(
            status_code=401,
            detail=str(e),
        )
    except RateLimitError as e:
        logger.error("Rate limit during connection test: %s", e)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {e}",
        )
    except ServerError as e:
        logger.error("Server error during connection test: %s", e)
        raise HTTPException(
            status_code=502,
            detail=f"Google API server error: {e}",
        )
    except Exception as e:
        logger.exception("Unexpected error during connection test")
        raise HTTPException(
            status_code=500,
            detail=f"Connection test failed: {e}",
        )

