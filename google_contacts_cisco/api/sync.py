"""API routes for synchronization operations.

This module provides FastAPI endpoints for managing contact synchronization:
- /api/sync/full - Trigger full synchronization
- /api/sync/status - Get current sync status
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth.oauth import is_authenticated
from ..models import get_db
from ..services.google_client import CredentialsError
from ..services.sync_service import get_sync_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sync", tags=["synchronization"])


class SyncStatusResponse(BaseModel):
    """Response model for sync status."""

    status: str
    last_sync_at: Optional[str] = None
    has_sync_token: bool
    error_message: Optional[str] = None
    contact_count: int
    total_contacts: int


class SyncTriggerResponse(BaseModel):
    """Response model for sync trigger."""

    status: str
    message: str
    statistics: Optional[dict] = None


class SyncErrorResponse(BaseModel):
    """Response model for sync errors."""

    error: str
    detail: str


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(db: Session = Depends(get_db)) -> SyncStatusResponse:
    """Get current synchronization status.

    Returns information about the last sync operation, including:
    - Current status (idle, syncing, error, never_synced)
    - When the last sync occurred
    - Whether a sync token is available for incremental sync
    - Any error messages from the last sync
    - Current contact counts

    Returns:
        SyncStatusResponse with sync status details
    """
    sync_service = get_sync_service(db)
    status = sync_service.get_sync_status()
    return SyncStatusResponse(**status)


@router.post("/full", response_model=SyncTriggerResponse)
async def trigger_full_sync(
    db: Session = Depends(get_db),
) -> SyncTriggerResponse:
    """Trigger full synchronization of Google Contacts.

    Downloads all contacts from the authenticated Google account and stores
    them in the local database. This operation may take a while depending
    on the number of contacts.

    Prerequisites:
    - User must be authenticated with Google OAuth

    Returns:
        SyncTriggerResponse with sync result and statistics

    Raises:
        HTTPException 401: If not authenticated with Google
        HTTPException 409: If a sync is already in progress
        HTTPException 500: If sync fails due to server error
    """
    # Check authentication
    if not is_authenticated():
        logger.warning("Full sync requested but user is not authenticated")
        raise HTTPException(
            status_code=401,
            detail="Not authenticated with Google. Please complete OAuth setup first.",
        )

    try:
        sync_service = get_sync_service(db)

        # Check if sync is already in progress
        if sync_service.is_sync_in_progress():
            logger.warning("Full sync requested but sync already in progress")
            raise HTTPException(
                status_code=409,
                detail="A sync is already in progress. Please wait for it to complete.",
            )

        # Perform full sync
        logger.info("Starting full sync triggered via API")
        stats = sync_service.full_sync()

        return SyncTriggerResponse(
            status="success",
            message="Full sync completed successfully",
            statistics=stats.to_dict(),
        )

    except CredentialsError as e:
        logger.error("Credentials error during sync: %s", e)
        raise HTTPException(
            status_code=401,
            detail=str(e),
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception("Full sync failed with unexpected error")
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {str(e)}",
        )


@router.get("/needs-sync")
async def check_needs_sync(db: Session = Depends(get_db)) -> dict:
    """Check if a full sync is required.

    A full sync is needed if:
    - No sync has ever been performed
    - The sync token has expired

    Returns:
        Dictionary with needs_full_sync boolean and reason
    """
    sync_service = get_sync_service(db)
    needs_sync = sync_service.needs_full_sync()

    if needs_sync:
        status = sync_service.get_sync_status()
        if status["status"] == "never_synced":
            reason = "No previous sync found"
        elif not status["has_sync_token"]:
            reason = "Sync token not available"
        else:
            reason = "Sync token may have expired"
    else:
        reason = "Incremental sync available"

    return {
        "needs_full_sync": needs_sync,
        "reason": reason,
    }

