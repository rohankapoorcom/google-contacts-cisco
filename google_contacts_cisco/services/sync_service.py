"""Sync service for Google Contacts synchronization.

This module provides the SyncService class which handles full and incremental
synchronization of contacts from Google to the local database.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..api.schemas import GoogleConnectionsResponse, GooglePerson
from ..config import settings
from ..models.phone_number import PhoneNumber
from ..models.sync_state import SyncState, SyncStatus
from ..repositories.contact_repository import ContactRepository
from ..repositories.sync_repository import SyncRepository
from ..services.contact_transformer import transform_google_person_to_contact
from ..services.google_client import (
    GoogleContactsClient,
    SyncTokenExpiredError,
    get_google_client,
)
from ..utils.datetime_utils import format_timestamp_for_display
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Module-level lock for preventing concurrent syncs
_sync_lock = Lock()


@dataclass
class SyncStatistics:
    """Statistics from a sync operation.

    Tracks the number of contacts processed, created, updated, and any errors
    encountered during synchronization.
    """

    total_fetched: int = 0
    created: int = 0
    updated: int = 0
    deleted: int = 0
    errors: int = 0
    pages: int = 0
    sync_type: str = "full"  # "full" or "incremental"
    start_time: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    end_time: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert statistics to dictionary.

        Returns:
            Dictionary representation of sync statistics
        """
        return {
            "total_fetched": self.total_fetched,
            "created": self.created,
            "updated": self.updated,
            "deleted": self.deleted,
            "errors": self.errors,
            "pages": self.pages,
            "sync_type": self.sync_type,
            "duration_seconds": self.duration_seconds,
        }

    @property
    def duration_seconds(self) -> float:
        """Calculate sync duration in seconds.

        Returns:
            Duration of sync operation in seconds
        """
        end = self.end_time or datetime.now(timezone.utc)
        return (end - self.start_time).total_seconds()


class SyncService:
    """Service for syncing Google Contacts to local database.

    Provides methods for full synchronization, incremental synchronization,
    and querying sync status. Handles pagination, error recovery, and
    progress tracking.

    Attributes:
        db: Database session
        contact_repo: Contact repository for database operations
        sync_repo: Sync repository for sync state management
        google_client: Google API client for fetching contacts
    """

    def __init__(
        self,
        db: Session,
        google_client: Optional[GoogleContactsClient] = None,
    ):
        """Initialize sync service.

        Args:
            db: Database session for all operations
            google_client: Optional Google client (creates one if not provided)
        """
        self.db = db
        self.contact_repo = ContactRepository(db)
        self.sync_repo = SyncRepository(db)
        self._google_client = google_client

    @property
    def google_client(self) -> GoogleContactsClient:
        """Get or create Google client.

        Lazily initializes the Google client on first access.

        Returns:
            GoogleContactsClient instance

        Raises:
            CredentialsError: If no valid credentials available
        """
        if self._google_client is None:
            self._google_client = get_google_client()
        return self._google_client

    def full_sync(
        self,
        batch_size: int = 100,
        page_delay: float = 0.1,
    ) -> SyncStatistics:
        """Perform full sync of all contacts from Google.

        Downloads all contacts from Google, transforms them, and stores them
        in the local database. Handles pagination automatically and stores
        the sync token for future incremental syncs.

        Args:
            batch_size: Number of contacts to commit per batch (default 100)
            page_delay: Delay between API page requests in seconds (default 0.1)

        Returns:
            SyncStatistics with details about the sync operation

        Raises:
            Exception: If sync fails (sync state will be marked as error)
        """
        logger.info("Starting full sync")
        stats = SyncStatistics()

        # Create sync state record
        sync_state = self.sync_repo.create_sync_state(status=SyncStatus.SYNCING)
        self.db.commit()

        try:
            # Fetch all contacts from Google
            for response_data in self.google_client.list_connections(
                page_size=100
            ):
                stats.pages += 1

                # Parse response
                response = GoogleConnectionsResponse(**response_data)

                if not response.connections:
                    logger.debug("Page %d: No contacts", stats.pages)
                    continue

                logger.info(
                    "Page %d: Processing %d contacts",
                    stats.pages,
                    len(response.connections),
                )

                # Process contacts in this page
                self._process_contacts_page(
                    response.connections, stats, batch_size
                )

                # Store sync token if this is the last page
                if not response.next_page_token and response.next_sync_token:
                    self.sync_repo.update_sync_state(
                        sync_state,
                        sync_token=response.next_sync_token,
                    )
                    self.db.commit()
                    logger.info(
                        "Stored sync token: %s...",
                        response.next_sync_token[:20],
                    )

                # Small delay between pages to avoid rate limits
                if response.next_page_token:
                    time.sleep(page_delay)

            # Mark sync as complete
            stats.end_time = datetime.now(timezone.utc)
            self.sync_repo.update_sync_state(sync_state, status=SyncStatus.IDLE)
            self.db.commit()

            logger.info("Full sync completed: %s", stats.to_dict())
            return stats

        except Exception as e:
            logger.exception("Full sync failed")
            stats.end_time = datetime.now(timezone.utc)
            self.sync_repo.update_sync_state(
                sync_state,
                status=SyncStatus.ERROR,
                error_message=str(e),
            )
            self.db.commit()
            raise

    def _process_contacts_page(
        self,
        connections: list[GooglePerson],
        stats: SyncStatistics,
        batch_size: int,
    ) -> None:
        """Process a page of contacts from Google.

        Args:
            connections: List of GooglePerson from the API response
            stats: Statistics object to update
            batch_size: Number of contacts between commits
        """
        for person in connections:
            try:
                # Transform Google contact to internal format
                contact_data = transform_google_person_to_contact(person)

                # Check if contact exists
                existing = self.contact_repo.get_by_resource_name(
                    contact_data.resource_name
                )

                # Handle deleted contacts
                if contact_data.deleted:
                    if existing:
                        self.contact_repo.mark_as_deleted(
                            contact_data.resource_name
                        )
                        stats.deleted += 1
                    # Skip creating deleted contacts that don't exist locally
                    continue

                # Upsert contact
                self.contact_repo.upsert_contact(contact_data)

                if existing:
                    stats.updated += 1
                else:
                    stats.created += 1

                stats.total_fetched += 1

                # Commit in batches for performance
                if stats.total_fetched % batch_size == 0:
                    self.db.commit()
                    logger.debug(
                        "Committed batch: %d contacts processed",
                        stats.total_fetched,
                    )

            except Exception as e:
                logger.error(
                    "Error processing contact %s: %s",
                    person.resource_name,
                    e,
                )
                stats.errors += 1
                continue

        # Commit remaining contacts in page
        self.db.commit()

    def get_sync_status(self) -> dict:
        """Get current sync status.

        Returns detailed information about the sync state, including
        whether a sync is in progress, when the last sync occurred,
        and contact counts.

        Returns:
            Dictionary with sync status information
        """
        sync_state = self.sync_repo.get_latest_sync_state()
        contact_count = self.contact_repo.count_active()
        total_count = self.contact_repo.count_all()

        if sync_state:
            return {
                "status": sync_state.sync_status.value,
                "last_sync_at": format_timestamp_for_display(
                    sync_state.last_sync_at,
                    settings.timezone
                ),
                "has_sync_token": sync_state.sync_token is not None,
                "error_message": sync_state.error_message,
                "contact_count": contact_count,
                "total_contacts": total_count,
            }
        else:
            return {
                "status": "never_synced",
                "last_sync_at": None,
                "has_sync_token": False,
                "error_message": None,
                "contact_count": contact_count,
                "total_contacts": total_count,
            }

    def needs_full_sync(self) -> bool:
        """Check if a full sync is required.

        A full sync is needed if no sync has ever been performed or
        if the sync token has expired.

        Returns:
            True if full sync is required
        """
        sync_state = self.sync_repo.get_latest_sync_state()
        return sync_state is None or sync_state.sync_token is None

    def is_sync_in_progress(self) -> bool:
        """Check if a sync is currently in progress.

        Returns:
            True if a sync is currently running
        """
        return self.sync_repo.is_sync_in_progress()

    def incremental_sync(
        self,
        batch_size: int = 100,
        page_delay: float = 0.1,
    ) -> SyncStatistics:
        """Perform incremental sync using sync token.

        Downloads only changes (new, modified, deleted contacts) since the last
        sync using the stored sync token. Falls back to full sync if no token
        is available or if the token has expired.

        Args:
            batch_size: Number of contacts to commit per batch (default 100)
            page_delay: Delay between API page requests in seconds (default 0.1)

        Returns:
            SyncStatistics with details about the sync operation

        Raises:
            Exception: If sync fails (sync state will be marked as error)
        """
        logger.info("Starting incremental sync")

        # Get latest sync state
        sync_state = self.sync_repo.get_latest_sync_state()

        if not sync_state or not sync_state.sync_token:
            logger.warning(
                "No sync token available, performing full sync instead"
            )
            return self.full_sync(batch_size, page_delay)

        sync_token = sync_state.sync_token
        logger.info("Using sync token: %s...", sync_token[:20])

        stats = SyncStatistics(sync_type="incremental")

        # Create new sync state record
        new_sync_state = self.sync_repo.create_sync_state(
            status=SyncStatus.SYNCING
        )
        self.db.commit()

        try:
            # Fetch changes from Google using sync token
            for response_data in self.google_client.list_connections(
                page_size=100,
                sync_token=sync_token,
            ):
                stats.pages += 1

                # Parse response
                response = GoogleConnectionsResponse(**response_data)

                if not response.connections:
                    logger.debug("Page %d: No changes", stats.pages)
                else:
                    logger.info(
                        "Page %d: Processing %d changes",
                        stats.pages,
                        len(response.connections),
                    )

                    # Process contacts in this page
                    self._process_contacts_page(
                        response.connections, stats, batch_size
                    )

                # Store new sync token if this is the last page
                if not response.next_page_token and response.next_sync_token:
                    self.sync_repo.update_sync_state(
                        new_sync_state,
                        sync_token=response.next_sync_token,
                    )
                    self.db.commit()
                    logger.info(
                        "Stored new sync token: %s...",
                        response.next_sync_token[:20],
                    )

                # Small delay between pages to avoid rate limits
                if response.next_page_token:
                    time.sleep(page_delay)

            # Mark sync as complete
            stats.end_time = datetime.now(timezone.utc)
            self.sync_repo.update_sync_state(
                new_sync_state, status=SyncStatus.IDLE
            )
            self.db.commit()

            logger.info("Incremental sync completed: %s", stats.to_dict())
            return stats

        except SyncTokenExpiredError:
            # Sync token expired, perform full sync
            logger.warning(
                "Sync token expired (410), falling back to full sync"
            )
            self.sync_repo.update_sync_state(
                new_sync_state,
                status=SyncStatus.ERROR,
                error_message="Sync token expired, performing full sync",
            )
            self.db.commit()
            return self.full_sync(batch_size, page_delay)

        except Exception as e:
            logger.exception("Incremental sync failed")
            stats.end_time = datetime.now(timezone.utc)
            self.sync_repo.update_sync_state(
                new_sync_state,
                status=SyncStatus.ERROR,
                error_message=str(e),
            )
            self.db.commit()
            raise

    def auto_sync(
        self,
        batch_size: int = 100,
        page_delay: float = 0.1,
    ) -> SyncStatistics:
        """Automatically choose between full and incremental sync.

        Checks if a valid sync token exists and performs incremental sync if
        available, otherwise falls back to full sync.

        Args:
            batch_size: Number of contacts to commit per batch (default 100)
            page_delay: Delay between API page requests in seconds (default 0.1)

        Returns:
            SyncStatistics with details about the sync operation
        """
        sync_state = self.sync_repo.get_latest_sync_state()

        if sync_state and sync_state.sync_token:
            logger.info("Sync token available, performing incremental sync")
            return self.incremental_sync(batch_size, page_delay)
        else:
            logger.info("No sync token available, performing full sync")
            return self.full_sync(batch_size, page_delay)

    def safe_auto_sync(
        self,
        batch_size: int = 100,
        page_delay: float = 0.1,
    ) -> dict[str, Any]:
        """Perform auto sync with locking to prevent concurrent syncs.

        Uses a thread-safe lock to ensure only one sync operation runs at a time.
        If a sync is already in progress, returns immediately with a skipped status.

        Args:
            batch_size: Number of contacts to commit per batch
            page_delay: Delay between API page requests in seconds

        Returns:
            Dict with status, message, and statistics (if sync was performed)
        """
        if not _sync_lock.acquire(blocking=False):
            logger.warning("Sync already in progress, skipping")
            return {
                "status": "skipped",
                "message": "Sync already in progress",
                "statistics": {},
            }

        try:
            stats = self.auto_sync(batch_size, page_delay)
            sync_type = stats.sync_type.capitalize()
            return {
                "status": "success",
                "message": f"{sync_type} sync completed successfully",
                "statistics": stats.to_dict(),
            }
        except Exception as e:
            logger.exception("Safe auto sync failed")
            return {
                "status": "error",
                "message": str(e),
                "statistics": {},
            }
        finally:
            _sync_lock.release()

    def get_sync_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get sync history.

        Returns a list of recent sync operations with their status and timestamps.

        Args:
            limit: Number of sync records to return (default 10)

        Returns:
            List of sync history records as dictionaries
        """
        sync_states = (
            self.db.query(SyncState)
            .order_by(SyncState.last_sync_at.desc())
            .limit(limit)
            .all()
        )

        history = []
        for state in sync_states:
            history.append({
                "id": str(state.id),
                "status": state.sync_status.value,
                "last_sync_at": format_timestamp_for_display(
                    state.last_sync_at,
                    settings.timezone
                ),
                "has_sync_token": state.sync_token is not None,
                "error_message": state.error_message,
            })

        return history

    def get_sync_statistics(self) -> dict[str, Any]:
        """Get comprehensive sync statistics.

        Provides detailed statistics about contacts, phone numbers, and sync status.

        Returns:
            Dictionary with sync statistics including:
            - contacts: total, active, deleted counts
            - phone_numbers: total count
            - sync: last sync info, status, token availability
            - sync_history: count by status
        """
        contact_count = self.contact_repo.count_active()
        total_count = self.contact_repo.count_all()
        deleted_count = total_count - contact_count

        # Get phone number count
        phone_count = self.db.query(PhoneNumber).count()

        # Get latest sync
        latest_sync = self.sync_repo.get_latest_sync_state()

        # Count syncs by status
        sync_counts = dict(
            self.db.query(
                SyncState.sync_status,
                func.count(SyncState.id),
            )
            .group_by(SyncState.sync_status)
            .all()
        )
        # Convert enum keys to string values
        sync_counts_str = {k.value: v for k, v in sync_counts.items()}

        return {
            "contacts": {
                "total": total_count,
                "active": contact_count,
                "deleted": deleted_count,
            },
            "phone_numbers": phone_count,
            "sync": {
                "last_sync_at": format_timestamp_for_display(
                    latest_sync.last_sync_at if latest_sync else None,
                    settings.timezone
                ),
                "status": (
                    latest_sync.sync_status.value if latest_sync else "never_synced"
                ),
                "has_sync_token": (
                    latest_sync.sync_token is not None if latest_sync else False
                ),
                "error_message": latest_sync.error_message if latest_sync else None,
            },
            "sync_history": sync_counts_str,
        }

    def clear_sync_history(self, keep_latest: bool = True) -> int:
        """Clear old sync history.

        Removes sync state records from the database, optionally keeping
        the most recent one.

        Args:
            keep_latest: If True, keep the most recent sync state (default True)

        Returns:
            Number of sync states deleted
        """
        if keep_latest:
            # Keep only the latest sync state
            latest = self.sync_repo.get_latest_sync_state()
            if latest:
                count = (
                    self.db.query(SyncState)
                    .filter(SyncState.id != latest.id)
                    .delete()
                )
            else:
                count = 0
        else:
            # Delete all sync states
            count = self.db.query(SyncState).delete()

        self.db.commit()
        logger.info("Cleared %d sync history records", count)
        return count


def get_sync_service(
    db: Session,
    google_client: Optional[GoogleContactsClient] = None,
) -> SyncService:
    """Get sync service instance.

    Factory function to create a configured SyncService.

    Args:
        db: Database session
        google_client: Optional Google client (creates one if not provided)

    Returns:
        SyncService instance
    """
    return SyncService(db, google_client)

