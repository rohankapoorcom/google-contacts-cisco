"""Google API routes.

This module provides FastAPI endpoints for interacting with the Google People API:
- /api/test-connection - Test connection to Google People API
"""

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
from ..utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["google"])


class TestConnectionResponse(BaseModel):
    """Response model for connection test."""

    status: str
    message: str
    total_contacts: Optional[int] = None


@router.get(
    "/test-connection",
    response_model=TestConnectionResponse,
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
        except Exception as e:
            logger.debug("Could not retrieve total contacts count: %s", e)
            total = None

        logger.info("Connection test successful")
        return TestConnectionResponse(
            status="success",
            message="Successfully connected to Google People API",
            total_contacts=total,
        )
    except CredentialsError as e:
        logger.exception("Credentials error during connection test")
        raise HTTPException(
            status_code=401,
            detail=str(e),
        ) from e
    except RateLimitError as e:
        logger.exception("Rate limit during connection test")
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {e}",
        ) from e
    except ServerError as e:
        logger.exception("Server error during connection test")
        raise HTTPException(
            status_code=502,
            detail=f"Google API server error: {e}",
        ) from e
    except Exception as e:
        logger.exception("Unexpected error during connection test")
        raise HTTPException(
            status_code=500,
            detail=f"Connection test failed: {e}",
        ) from e
