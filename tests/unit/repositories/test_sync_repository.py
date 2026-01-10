"""Test Sync Repository.

This module tests the SyncRepository implementation for managing
synchronization state in the database.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from google_contacts_cisco.models import Base
from google_contacts_cisco.models.sync_state import SyncStatus
from google_contacts_cisco.repositories.sync_repository import SyncRepository


@pytest.fixture
def db_session():
    """Create test database session with in-memory SQLite."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)  # noqa: N806
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sync_repo(db_session):
    """Create SyncRepository instance."""
    return SyncRepository(db_session)


class TestCreateSyncState:
    """Test sync state creation functionality."""

    def test_create_sync_state_default(self, sync_repo, db_session):
        """Test creating sync state with default values."""
        sync_state = sync_repo.create_sync_state()
        db_session.commit()

        assert sync_state.id is not None
        assert sync_state.sync_status == SyncStatus.IDLE
        assert sync_state.sync_token is None
        assert sync_state.error_message is None
        assert sync_state.last_sync_at is not None

    def test_create_sync_state_with_token(self, sync_repo, db_session):
        """Test creating sync state with sync token."""
        sync_state = sync_repo.create_sync_state(sync_token="test_token_123")
        db_session.commit()

        assert sync_state.sync_token == "test_token_123"
        assert sync_state.sync_status == SyncStatus.IDLE

    def test_create_sync_state_syncing(self, sync_repo, db_session):
        """Test creating sync state with SYNCING status."""
        sync_state = sync_repo.create_sync_state(status=SyncStatus.SYNCING)
        db_session.commit()

        assert sync_state.sync_status == SyncStatus.SYNCING

    def test_create_sync_state_with_error(self, sync_repo, db_session):
        """Test creating sync state with error status and message."""
        sync_state = sync_repo.create_sync_state(
            status=SyncStatus.ERROR,
            error_message="Connection failed",
        )
        db_session.commit()

        assert sync_state.sync_status == SyncStatus.ERROR
        assert sync_state.error_message == "Connection failed"


class TestGetSyncState:
    """Test sync state retrieval functionality."""

    def test_get_latest_sync_state_exists(self, sync_repo, db_session):
        """Test getting latest sync state when it exists."""
        # Create older sync state
        old_state = sync_repo.create_sync_state(sync_token="old_token")
        db_session.commit()

        # Ensure timestamp difference
        old_state.last_sync_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db_session.commit()

        # Create newer sync state
        new_state = sync_repo.create_sync_state(sync_token="new_token")
        db_session.commit()

        latest = sync_repo.get_latest_sync_state()

        assert latest is not None
        assert latest.id == new_state.id
        assert latest.sync_token == "new_token"

    def test_get_latest_sync_state_empty(self, sync_repo):
        """Test getting latest sync state when none exist."""
        latest = sync_repo.get_latest_sync_state()
        assert latest is None

    def test_get_sync_state_by_id(self, sync_repo, db_session):
        """Test getting sync state by ID."""
        created = sync_repo.create_sync_state(sync_token="test")
        db_session.commit()

        found = sync_repo.get_sync_state_by_id(str(created.id))
        assert found is not None
        assert found.sync_token == "test"

    def test_get_sync_state_by_id_not_found(self, sync_repo):
        """Test getting sync state by non-existent ID."""
        import uuid

        found = sync_repo.get_sync_state_by_id(str(uuid.uuid4()))
        assert found is None


class TestUpdateSyncState:
    """Test sync state update functionality."""

    def test_update_sync_token(self, sync_repo, db_session):
        """Test updating sync token."""
        sync_state = sync_repo.create_sync_state()
        db_session.commit()

        sync_repo.update_sync_state(sync_state, sync_token="updated_token")
        db_session.commit()

        assert sync_state.sync_token == "updated_token"

    def test_update_status(self, sync_repo, db_session):
        """Test updating sync status."""
        sync_state = sync_repo.create_sync_state(status=SyncStatus.SYNCING)
        db_session.commit()

        sync_repo.update_sync_state(sync_state, status=SyncStatus.IDLE)
        db_session.commit()

        assert sync_state.sync_status == SyncStatus.IDLE

    def test_update_error_message(self, sync_repo, db_session):
        """Test updating error message."""
        sync_state = sync_repo.create_sync_state(status=SyncStatus.ERROR)
        db_session.commit()

        sync_repo.update_sync_state(
            sync_state,
            error_message="API rate limit exceeded",
        )
        db_session.commit()

        assert sync_state.error_message == "API rate limit exceeded"

    def test_update_multiple_fields(self, sync_repo, db_session):
        """Test updating multiple fields at once."""
        sync_state = sync_repo.create_sync_state(status=SyncStatus.SYNCING)
        db_session.commit()
        original_time = sync_state.last_sync_at

        sync_repo.update_sync_state(
            sync_state,
            sync_token="new_token",
            status=SyncStatus.IDLE,
        )
        db_session.commit()

        assert sync_state.sync_token == "new_token"
        assert sync_state.sync_status == SyncStatus.IDLE
        assert sync_state.last_sync_at >= original_time

    def test_update_preserves_unspecified_fields(self, sync_repo, db_session):
        """Test that update doesn't change unspecified fields."""
        sync_state = sync_repo.create_sync_state(
            sync_token="original_token",
            status=SyncStatus.IDLE,
        )
        db_session.commit()

        # Only update status, token should remain
        sync_repo.update_sync_state(sync_state, status=SyncStatus.SYNCING)
        db_session.commit()

        assert sync_state.sync_token == "original_token"
        assert sync_state.sync_status == SyncStatus.SYNCING


class TestSyncTokenOperations:
    """Test sync token specific operations."""

    def test_get_current_sync_token_exists(self, sync_repo, db_session):
        """Test getting current sync token when successful sync exists."""
        sync_repo.create_sync_state(
            sync_token="valid_token",
            status=SyncStatus.IDLE,
        )
        db_session.commit()

        token = sync_repo.get_current_sync_token()
        assert token == "valid_token"

    def test_get_current_sync_token_no_syncs(self, sync_repo):
        """Test getting sync token when no syncs have occurred."""
        token = sync_repo.get_current_sync_token()
        assert token is None

    def test_get_current_sync_token_after_error(self, sync_repo, db_session):
        """Test that sync token is not returned after error state."""
        sync_repo.create_sync_state(
            sync_token="token_before_error",
            status=SyncStatus.ERROR,
            error_message="Sync failed",
        )
        db_session.commit()

        token = sync_repo.get_current_sync_token()
        assert token is None


class TestSyncStatusChecks:
    """Test sync status check functionality."""

    def test_has_completed_sync_true(self, sync_repo, db_session):
        """Test has_completed_sync returns True after successful sync."""
        sync_repo.create_sync_state(
            sync_token="token",
            status=SyncStatus.IDLE,
        )
        db_session.commit()

        assert sync_repo.has_completed_sync() is True

    def test_has_completed_sync_false_no_syncs(self, sync_repo):
        """Test has_completed_sync returns False with no syncs."""
        assert sync_repo.has_completed_sync() is False

    def test_has_completed_sync_false_in_progress(self, sync_repo, db_session):
        """Test has_completed_sync returns False while syncing."""
        sync_repo.create_sync_state(status=SyncStatus.SYNCING)
        db_session.commit()

        assert sync_repo.has_completed_sync() is False

    def test_has_completed_sync_false_after_error(self, sync_repo, db_session):
        """Test has_completed_sync returns False after error."""
        sync_repo.create_sync_state(status=SyncStatus.ERROR)
        db_session.commit()

        assert sync_repo.has_completed_sync() is False

    def test_is_sync_in_progress_true(self, sync_repo, db_session):
        """Test is_sync_in_progress returns True when syncing."""
        sync_repo.create_sync_state(status=SyncStatus.SYNCING)
        db_session.commit()

        assert sync_repo.is_sync_in_progress() is True

    def test_is_sync_in_progress_false_idle(self, sync_repo, db_session):
        """Test is_sync_in_progress returns False when idle."""
        sync_repo.create_sync_state(status=SyncStatus.IDLE)
        db_session.commit()

        assert sync_repo.is_sync_in_progress() is False

    def test_is_sync_in_progress_false_no_syncs(self, sync_repo):
        """Test is_sync_in_progress returns False with no syncs."""
        assert sync_repo.is_sync_in_progress() is False


class TestDeleteAllSyncStates:
    """Test bulk delete functionality."""

    def test_delete_all(self, sync_repo, db_session):
        """Test deleting all sync states."""
        for _ in range(3):
            sync_repo.create_sync_state()
        db_session.commit()

        count = sync_repo.delete_all()
        db_session.commit()

        assert count == 3
        assert sync_repo.get_latest_sync_state() is None

    def test_delete_all_empty(self, sync_repo, db_session):
        """Test deleting when no sync states exist."""
        count = sync_repo.delete_all()
        assert count == 0
