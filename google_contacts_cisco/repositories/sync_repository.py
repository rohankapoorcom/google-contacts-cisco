"""Sync state repository.

This module provides data access operations for SyncState entities,
including CRUD operations and query methods for tracking synchronization state.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ..models.sync_state import SyncState, SyncStatus
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SyncRepository:
    """Repository for sync state operations.

    Provides methods for managing synchronization state records,
    including creating new sync states, updating existing ones,
    and querying the current sync status.
    """

    def __init__(self, db: Session):
        """Initialize repository.

        Args:
            db: Database session for all operations
        """
        self.db = db

    def get_latest_sync_state(self) -> Optional[SyncState]:
        """Get the most recent sync state.

        Returns:
            Latest sync state or None if no syncs have occurred
        """
        return self.db.query(SyncState).order_by(SyncState.last_sync_at.desc()).first()

    def get_sync_state_by_id(self, sync_id) -> Optional[SyncState]:
        """Get sync state by ID.

        Args:
            sync_id: Sync state UUID (can be UUID object or string)

        Returns:
            SyncState or None if not found
        """
        from uuid import UUID

        # Convert string to UUID if needed
        if isinstance(sync_id, str):
            try:
                sync_id = UUID(sync_id)
            except ValueError:
                return None
        return self.db.query(SyncState).filter(SyncState.id == sync_id).first()

    def create_sync_state(
        self,
        sync_token: Optional[str] = None,
        status: SyncStatus = SyncStatus.IDLE,
        error_message: Optional[str] = None,
    ) -> SyncState:
        """Create new sync state.

        Args:
            sync_token: Sync token from Google for incremental sync
            status: Initial sync status (defaults to IDLE)
            error_message: Error message if status is ERROR

        Returns:
            Created sync state entity
        """
        sync_state = SyncState(
            sync_token=sync_token,
            last_sync_at=datetime.now(timezone.utc),
            sync_status=status,
            error_message=error_message,
        )
        self.db.add(sync_state)
        logger.debug("Created sync state with status: %s", status.value)
        return sync_state

    def update_sync_state(
        self,
        sync_state: SyncState,
        sync_token: Optional[str] = None,
        status: Optional[SyncStatus] = None,
        error_message: Optional[str] = None,
    ) -> SyncState:
        """Update existing sync state.

        Only non-None parameters will be updated.

        Args:
            sync_state: Sync state to update
            sync_token: New sync token (if provided)
            status: New status (if provided)
            error_message: New error message (if provided)

        Returns:
            Updated sync state entity
        """
        if sync_token is not None:
            sync_state.sync_token = sync_token  # type: ignore[assignment]
        if status is not None:
            sync_state.sync_status = status  # type: ignore[assignment]
        if error_message is not None:
            sync_state.error_message = error_message  # type: ignore[assignment]

        sync_state.last_sync_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        logger.debug(
            "Updated sync state: status=%s, has_token=%s",
            sync_state.sync_status.value,
            sync_state.sync_token is not None,
        )
        return sync_state

    def get_current_sync_token(self) -> Optional[str]:
        """Get the current sync token for incremental sync.

        Returns:
            Sync token or None if no successful sync has occurred
        """
        latest = self.get_latest_sync_state()
        if latest and latest.sync_status != SyncStatus.ERROR:
            return latest.sync_token  # type: ignore[return-value]
        return None

    def has_completed_sync(self) -> bool:
        """Check if a successful sync has ever been completed.

        Returns:
            True if at least one successful sync has completed
        """
        latest = self.get_latest_sync_state()
        return latest is not None and latest.sync_status == SyncStatus.IDLE  # type: ignore[return-value]

    def is_sync_in_progress(self) -> bool:
        """Check if a sync is currently in progress.

        Returns:
            True if a sync is currently running
        """
        latest = self.get_latest_sync_state()
        return latest is not None and latest.sync_status == SyncStatus.SYNCING  # type: ignore[return-value]

    def delete_all(self) -> int:
        """Delete all sync states (for testing).

        Returns:
            Number of sync states deleted
        """
        count = self.db.query(SyncState).delete()
        logger.info("Deleted all sync states: %d", count)
        return count
