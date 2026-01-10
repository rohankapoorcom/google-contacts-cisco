"""API routes for synchronization operations.

This module provides FastAPI endpoints for managing contact synchronization:
- /api/sync - Trigger auto synchronization
- /api/sync/full - Trigger full synchronization
- /api/sync/incremental - Trigger incremental synchronization
- /api/sync/safe - Trigger sync with concurrency protection
- /api/sync/status - Get current sync status
- /api/sync/statistics - Get comprehensive sync statistics
- /api/sync/history - Get sync history
- /api/sync/needs-sync - Check if full sync is required
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth.oauth import is_authenticated
from ..models import get_db
from ..services.google_client import CredentialsError
from ..services.sync_service import SyncInProgressError, get_sync_service

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
    statistics: Optional[dict[str, Any]] = None


class SyncErrorResponse(BaseModel):
    """Response model for sync errors."""

    error: str
    detail: str


class SyncHistoryEntry(BaseModel):
    """Model for a single sync history entry."""

    id: str
    status: str
    last_sync_at: Optional[str] = None
    has_sync_token: bool
    error_message: Optional[str] = None


class SyncHistoryResponse(BaseModel):
    """Response model for sync history."""

    history: list[SyncHistoryEntry]


class ContactStatistics(BaseModel):
    """Model for contact statistics."""

    total: int
    active: int
    deleted: int


class SyncInfo(BaseModel):
    """Model for sync info."""

    last_sync_at: Optional[str] = None
    status: str
    has_sync_token: bool
    error_message: Optional[str] = None


class SyncStatisticsResponse(BaseModel):
    """Response model for comprehensive sync statistics."""

    contacts: ContactStatistics
    phone_numbers: int
    sync: SyncInfo
    sync_history: dict[str, int]


class ClearHistoryResponse(BaseModel):
    """Response model for clear history operation."""

    status: str
    deleted_count: int


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

        # Perform full sync (lock is acquired inside the method)
        logger.info("Starting full sync triggered via API")
        stats = sync_service.full_sync()

        return SyncTriggerResponse(
            status="success",
            message="Full sync completed successfully",
            statistics=stats.to_dict(),
        )

    except SyncInProgressError as e:
        logger.warning("Full sync requested but sync already in progress")
        raise HTTPException(
            status_code=409,
            detail=str(e),
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


@router.post("/incremental", response_model=SyncTriggerResponse)
async def trigger_incremental_sync(
    db: Session = Depends(get_db),
) -> SyncTriggerResponse:
    """Trigger incremental synchronization of Google Contacts.

    Downloads only contacts that have changed since the last sync using
    the stored sync token. Falls back to full sync if no sync token is
    available or if the token has expired.

    Prerequisites:
    - User must be authenticated with Google OAuth
    - At least one full sync should have been completed (for sync token)

    Returns:
        SyncTriggerResponse with sync result and statistics

    Raises:
        HTTPException 401: If not authenticated with Google
        HTTPException 409: If a sync is already in progress
        HTTPException 500: If sync fails due to server error
    """
    # Check authentication
    if not is_authenticated():
        logger.warning("Incremental sync requested but user is not authenticated")
        raise HTTPException(
            status_code=401,
            detail="Not authenticated with Google. Please complete OAuth setup first.",
        )

    try:
        sync_service = get_sync_service(db)

        # Perform incremental sync (lock is acquired inside the method)
        logger.info("Starting incremental sync triggered via API")
        stats = sync_service.incremental_sync()

        return SyncTriggerResponse(
            status="success",
            message="Incremental sync completed successfully",
            statistics=stats.to_dict(),
        )

    except SyncInProgressError as e:
        logger.warning("Incremental sync requested but sync already in progress")
        raise HTTPException(
            status_code=409,
            detail=str(e),
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
        logger.exception("Incremental sync failed with unexpected error")
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {str(e)}",
        )


@router.post("", response_model=SyncTriggerResponse)
async def trigger_auto_sync(
    db: Session = Depends(get_db),
) -> SyncTriggerResponse:
    """Trigger automatic synchronization of Google Contacts.

    Automatically chooses between full and incremental sync based on
    the current state:
    - If a sync token exists: performs incremental sync
    - If no sync token: performs full sync

    This is the recommended endpoint for most use cases.

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
        logger.warning("Auto sync requested but user is not authenticated")
        raise HTTPException(
            status_code=401,
            detail="Not authenticated with Google. Please complete OAuth setup first.",
        )

    try:
        sync_service = get_sync_service(db)

        # Perform auto sync (lock is acquired inside the method)
        logger.info("Starting auto sync triggered via API")
        stats = sync_service.auto_sync()

        # Use explicit sync_type from stats
        sync_type_display = stats.sync_type.capitalize()

        return SyncTriggerResponse(
            status="success",
            message=f"{sync_type_display} sync completed successfully",
            statistics=stats.to_dict(),
        )

    except SyncInProgressError as e:
        logger.warning("Auto sync requested but sync already in progress")
        raise HTTPException(
            status_code=409,
            detail=str(e),
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
        logger.exception("Auto sync failed with unexpected error")
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {str(e)}",
        )


@router.get("/needs-sync")
async def check_needs_sync(db: Session = Depends(get_db)) -> dict[str, Any]:
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


@router.post("/safe", response_model=SyncTriggerResponse)
async def trigger_safe_sync(
    db: Session = Depends(get_db),
) -> SyncTriggerResponse | JSONResponse:
    """Trigger sync with concurrency protection.

    Uses a lock to prevent multiple simultaneous sync operations.
    If a sync is already in progress, returns HTTP 409 Conflict.

    This is the recommended endpoint for triggering syncs from background
    jobs or scheduled tasks.

    Prerequisites:
    - User must be authenticated with Google OAuth

    Returns:
        SyncTriggerResponse with sync result and statistics

    Raises:
        HTTPException 401: If not authenticated with Google
        JSONResponse 409: If a sync is already in progress
        HTTPException 500: If sync fails due to server error
    """
    # Check authentication
    if not is_authenticated():
        logger.warning("Safe sync requested but user is not authenticated")
        raise HTTPException(
            status_code=401,
            detail="Not authenticated with Google. Please complete OAuth setup first.",
        )

    try:
        sync_service = get_sync_service(db)
        result = sync_service.safe_auto_sync()

        if result.get("status") == "skipped":
            return JSONResponse(
                status_code=409,  # Conflict
                content=result,
            )

        return SyncTriggerResponse(
            status=result["status"],
            message=result["message"],
            statistics=result.get("statistics"),
        )

    except CredentialsError as e:
        logger.exception("Credentials error during safe sync")
        raise HTTPException(
            status_code=401,
            detail=str(e),
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Safe sync failed with unexpected error")
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {e!s}",
        ) from e


@router.get("/history", response_model=SyncHistoryResponse)
async def get_sync_history(
    limit: int = Query(default=10, ge=1, le=100, description="Number of records"),
    db: Session = Depends(get_db),
) -> SyncHistoryResponse:
    """Get sync history.

    Returns a list of recent sync operations with their status,
    timestamps, and any error messages.

    Args:
        limit: Number of sync records to return (1-100, default 10)

    Returns:
        SyncHistoryResponse with list of sync history entries
    """
    sync_service = get_sync_service(db)
    history = sync_service.get_sync_history(limit)
    return SyncHistoryResponse(
        history=[SyncHistoryEntry(**entry) for entry in history]
    )


@router.get("/statistics", response_model=SyncStatisticsResponse)
async def get_sync_statistics(
    db: Session = Depends(get_db),
) -> SyncStatisticsResponse:
    """Get comprehensive sync statistics.

    Returns detailed statistics about:
    - Contacts: total, active, and deleted counts
    - Phone numbers: total count
    - Sync: last sync info, status, token availability
    - Sync history: count by status

    Returns:
        SyncStatisticsResponse with all statistics
    """
    sync_service = get_sync_service(db)
    stats = sync_service.get_sync_statistics()
    return SyncStatisticsResponse(
        contacts=ContactStatistics(**stats["contacts"]),
        phone_numbers=stats["phone_numbers"],
        sync=SyncInfo(**stats["sync"]),
        sync_history=stats["sync_history"],
    )


@router.delete("/history", response_model=ClearHistoryResponse)
async def clear_sync_history(
    keep_latest: bool = Query(
        default=True,
        description="Keep the most recent sync state",
    ),
    db: Session = Depends(get_db),
) -> ClearHistoryResponse:
    """Clear sync history.

    Removes old sync state records from the database.
    Optionally keeps the most recent sync state.

    Prerequisites:
    - User must be authenticated with Google OAuth

    Args:
        keep_latest: If True, keep the most recent sync state (default True)

    Returns:
        ClearHistoryResponse with number of deleted records

    Raises:
        HTTPException 401: If not authenticated with Google
    """
    # Check authentication
    if not is_authenticated():
        logger.warning("Clear sync history requested but user is not authenticated")
        raise HTTPException(
            status_code=401,
            detail="Not authenticated with Google. Please complete OAuth setup first.",
        )

    sync_service = get_sync_service(db)
    deleted_count = sync_service.clear_sync_history(keep_latest)
    return ClearHistoryResponse(
        status="success",
        deleted_count=deleted_count,
    )

