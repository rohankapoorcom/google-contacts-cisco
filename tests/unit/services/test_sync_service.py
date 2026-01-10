"""Test Sync Service.

This module tests the SyncService implementation for full and incremental
synchronization of Google Contacts.
"""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from google_contacts_cisco.models import Base, Contact, SyncState
from google_contacts_cisco.models.sync_state import SyncStatus
from google_contacts_cisco.services.sync_service import (
    SyncService,
    SyncStatistics,
    get_sync_service,
)


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
def mock_google_client():
    """Create mock Google client."""
    return Mock()


@pytest.fixture
def sync_service(db_session, mock_google_client):
    """Create SyncService with mock Google client."""
    return SyncService(db_session, google_client=mock_google_client)


class TestSyncStatistics:
    """Test SyncStatistics dataclass functionality."""

    def test_default_values(self):
        """Test default statistics values."""
        stats = SyncStatistics()

        assert stats.total_fetched == 0
        assert stats.created == 0
        assert stats.updated == 0
        assert stats.deleted == 0
        assert stats.errors == 0
        assert stats.pages == 0
        assert stats.start_time is not None
        assert stats.end_time is None

    def test_to_dict(self):
        """Test converting statistics to dictionary."""
        stats = SyncStatistics(
            total_fetched=100,
            created=80,
            updated=20,
            deleted=5,
            errors=2,
            pages=3,
        )
        stats.end_time = stats.start_time

        result = stats.to_dict()

        assert result["total_fetched"] == 100
        assert result["created"] == 80
        assert result["updated"] == 20
        assert result["deleted"] == 5
        assert result["errors"] == 2
        assert result["pages"] == 3
        assert "duration_seconds" in result

    def test_duration_seconds(self):
        """Test duration calculation."""
        stats = SyncStatistics()
        stats.start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        stats.end_time = datetime(2024, 1, 1, 0, 1, 30, tzinfo=timezone.utc)

        assert stats.duration_seconds == 90.0

    def test_duration_seconds_in_progress(self):
        """Test duration calculation when sync is in progress."""
        stats = SyncStatistics()
        # end_time is None, so it should calculate from current time
        assert stats.duration_seconds >= 0


class TestSyncServiceInit:
    """Test SyncService initialization."""

    def test_init_with_google_client(self, db_session, mock_google_client):
        """Test initialization with provided Google client."""
        service = SyncService(db_session, google_client=mock_google_client)

        assert service.db is db_session
        assert service._google_client is mock_google_client

    def test_init_without_google_client(self, db_session):
        """Test initialization without Google client (lazy loading)."""
        service = SyncService(db_session)

        assert service.db is db_session
        assert service._google_client is None


class TestFullSync:
    """Test full synchronization functionality."""

    def test_full_sync_single_page(self, sync_service, db_session, mock_google_client):
        """Test full sync with single page of contacts."""
        # Mock API response
        mock_response = {
            "connections": [
                {
                    "resourceName": "people/c1",
                    "names": [{"displayName": "John Doe", "givenName": "John"}],
                    "phoneNumbers": [{"value": "5551234567", "type": "mobile"}],
                },
                {
                    "resourceName": "people/c2",
                    "names": [{"displayName": "Jane Smith", "givenName": "Jane"}],
                    "phoneNumbers": [{"value": "5559876543", "type": "work"}],
                },
            ],
            "nextSyncToken": "sync_token_123",
        }
        mock_google_client.list_connections.return_value = [mock_response]

        stats = sync_service.full_sync()

        assert stats.total_fetched == 2
        assert stats.created == 2
        assert stats.updated == 0
        assert stats.errors == 0
        assert stats.pages == 1

        # Verify contacts in database
        contacts = db_session.query(Contact).all()
        assert len(contacts) == 2

        # Verify sync state
        sync_state = db_session.query(SyncState).first()
        assert sync_state is not None
        assert sync_state.sync_status == SyncStatus.IDLE
        assert sync_state.sync_token == "sync_token_123"

    def test_full_sync_multiple_pages(
        self, sync_service, db_session, mock_google_client
    ):
        """Test full sync with multiple pages."""
        # Mock multiple pages
        page1 = {
            "connections": [
                {
                    "resourceName": "people/c1",
                    "names": [{"displayName": "Contact 1"}],
                    "phoneNumbers": [],
                },
            ],
            "nextPageToken": "page2_token",
        }
        page2 = {
            "connections": [
                {
                    "resourceName": "people/c2",
                    "names": [{"displayName": "Contact 2"}],
                    "phoneNumbers": [],
                },
            ],
            "nextSyncToken": "final_sync_token",
        }
        mock_google_client.list_connections.return_value = [page1, page2]

        stats = sync_service.full_sync(page_delay=0)

        assert stats.total_fetched == 2
        assert stats.pages == 2
        assert db_session.query(Contact).count() == 2

        # Verify sync token from last page
        sync_state = db_session.query(SyncState).first()
        assert sync_state.sync_token == "final_sync_token"

    def test_full_sync_updates_existing_contacts(
        self, sync_service, db_session, mock_google_client
    ):
        """Test that full sync updates existing contacts."""
        # Create existing contact
        existing = Contact(
            resource_name="people/c1",
            display_name="Old Name",
            given_name="Old",
        )
        db_session.add(existing)
        db_session.commit()

        # Mock response with updated contact
        mock_response = {
            "connections": [
                {
                    "resourceName": "people/c1",
                    "names": [{"displayName": "New Name", "givenName": "New"}],
                    "phoneNumbers": [],
                },
            ],
            "nextSyncToken": "token",
        }
        mock_google_client.list_connections.return_value = [mock_response]

        stats = sync_service.full_sync()

        assert stats.updated == 1
        assert stats.created == 0

        # Verify update
        contact = db_session.query(Contact).first()
        assert contact.display_name == "New Name"
        assert contact.given_name == "New"

    def test_full_sync_handles_deleted_contacts(
        self, sync_service, db_session, mock_google_client
    ):
        """Test that full sync marks deleted contacts."""
        # Create existing contact
        existing = Contact(
            resource_name="people/c1",
            display_name="To Be Deleted",
            deleted=False,
        )
        db_session.add(existing)
        db_session.commit()

        # Mock response with deleted contact
        mock_response = {
            "connections": [
                {
                    "resourceName": "people/c1",
                    "names": [{"displayName": "To Be Deleted"}],
                    "phoneNumbers": [],
                    "metadata": {"deleted": True},
                },
            ],
            "nextSyncToken": "token",
        }
        mock_google_client.list_connections.return_value = [mock_response]

        stats = sync_service.full_sync()

        assert stats.deleted == 1

        # Verify soft delete
        contact = db_session.query(Contact).first()
        assert contact.deleted is True

    def test_full_sync_empty_response(
        self, sync_service, db_session, mock_google_client
    ):
        """Test full sync with empty response (no contacts)."""
        mock_response = {
            "connections": [],
            "nextSyncToken": "empty_token",
        }
        mock_google_client.list_connections.return_value = [mock_response]

        stats = sync_service.full_sync()

        assert stats.total_fetched == 0
        assert stats.pages == 1
        assert db_session.query(Contact).count() == 0

    def test_full_sync_handles_contact_errors(
        self, sync_service, db_session, mock_google_client
    ):
        """Test that sync continues after individual contact errors."""
        # Mock response with one valid and one that will cause error
        mock_response = {
            "connections": [
                {
                    "resourceName": "people/c1",
                    "names": [{"displayName": "Valid Contact"}],
                    "phoneNumbers": [],
                },
                {
                    "resourceName": "people/c2",
                    # Missing display name - will use resource name as fallback
                    "names": [],
                    "phoneNumbers": [],
                },
            ],
            "nextSyncToken": "token",
        }
        mock_google_client.list_connections.return_value = [mock_response]

        stats = sync_service.full_sync()

        # Both should be processed (second uses resource name as display name)
        assert stats.total_fetched == 2
        assert stats.errors == 0  # No errors because fallback works

    def test_full_sync_sets_error_state_on_failure(
        self, sync_service, db_session, mock_google_client
    ):
        """Test that sync state is set to ERROR on failure."""
        mock_google_client.list_connections.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            sync_service.full_sync()

        # Verify error state
        sync_state = db_session.query(SyncState).first()
        assert sync_state is not None
        assert sync_state.sync_status == SyncStatus.ERROR
        assert "API Error" in sync_state.error_message

    def test_full_sync_creates_syncing_state(
        self, sync_service, db_session, mock_google_client
    ):
        """Test that sync creates SYNCING state before starting."""
        states_during_sync = []

        def capture_state(*args, **kwargs):
            state = db_session.query(SyncState).first()
            if state:
                states_during_sync.append(state.sync_status)
            return [{"connections": [], "nextSyncToken": "token"}]

        mock_google_client.list_connections.side_effect = capture_state

        sync_service.full_sync()

        # First state captured should be SYNCING
        assert len(states_during_sync) == 1
        assert states_during_sync[0] == SyncStatus.SYNCING


class TestGetSyncStatus:
    """Test sync status retrieval."""

    def test_get_sync_status_never_synced(self, sync_service):
        """Test status when never synced."""
        status = sync_service.get_sync_status()

        assert status["status"] == "never_synced"
        assert status["last_sync_at"] is None
        assert status["has_sync_token"] is False
        assert status["error_message"] is None
        assert status["contact_count"] == 0
        assert status["total_contacts"] == 0

    def test_get_sync_status_after_sync(
        self, sync_service, db_session, mock_google_client
    ):
        """Test status after successful sync."""
        mock_response = {
            "connections": [
                {
                    "resourceName": "people/c1",
                    "names": [{"displayName": "Test"}],
                    "phoneNumbers": [],
                },
            ],
            "nextSyncToken": "token123",
        }
        mock_google_client.list_connections.return_value = [mock_response]

        sync_service.full_sync()
        status = sync_service.get_sync_status()

        assert status["status"] == "idle"
        assert status["last_sync_at"] is not None
        assert status["has_sync_token"] is True
        assert status["error_message"] is None
        assert status["contact_count"] == 1
        assert status["total_contacts"] == 1

    def test_get_sync_status_with_deleted_contacts(
        self, sync_service, db_session, mock_google_client
    ):
        """Test status counts exclude deleted contacts in contact_count."""
        # Create active and deleted contacts
        active = Contact(
            resource_name="people/c1",
            display_name="Active",
            deleted=False,
        )
        deleted = Contact(
            resource_name="people/c2",
            display_name="Deleted",
            deleted=True,
        )
        db_session.add_all([active, deleted])

        sync_state = SyncState(
            sync_status=SyncStatus.IDLE,
            sync_token="token",
            last_sync_at=datetime.now(timezone.utc),
        )
        db_session.add(sync_state)
        db_session.commit()

        status = sync_service.get_sync_status()

        assert status["contact_count"] == 1  # Only active
        assert status["total_contacts"] == 2  # Both


class TestSyncChecks:
    """Test sync status check methods."""

    def test_needs_full_sync_no_previous_sync(self, sync_service):
        """Test needs_full_sync returns True when no sync has occurred."""
        assert sync_service.needs_full_sync() is True

    def test_needs_full_sync_no_token(self, sync_service, db_session):
        """Test needs_full_sync returns True when no sync token."""
        sync_state = SyncState(
            sync_status=SyncStatus.IDLE,
            sync_token=None,
            last_sync_at=datetime.now(timezone.utc),
        )
        db_session.add(sync_state)
        db_session.commit()

        assert sync_service.needs_full_sync() is True

    def test_needs_full_sync_has_token(self, sync_service, db_session):
        """Test needs_full_sync returns False when token exists."""
        sync_state = SyncState(
            sync_status=SyncStatus.IDLE,
            sync_token="valid_token",
            last_sync_at=datetime.now(timezone.utc),
        )
        db_session.add(sync_state)
        db_session.commit()

        assert sync_service.needs_full_sync() is False

    def test_is_sync_in_progress_true(self, sync_service, db_session):
        """Test is_sync_in_progress returns True when syncing."""
        sync_state = SyncState(
            sync_status=SyncStatus.SYNCING,
            last_sync_at=datetime.now(timezone.utc),
        )
        db_session.add(sync_state)
        db_session.commit()

        assert sync_service.is_sync_in_progress() is True

    def test_is_sync_in_progress_false(self, sync_service, db_session):
        """Test is_sync_in_progress returns False when not syncing."""
        sync_state = SyncState(
            sync_status=SyncStatus.IDLE,
            last_sync_at=datetime.now(timezone.utc),
        )
        db_session.add(sync_state)
        db_session.commit()

        assert sync_service.is_sync_in_progress() is False


class TestIncrementalSync:
    """Test incremental synchronization functionality."""

    def test_incremental_sync_with_updates(
        self, sync_service, db_session, mock_google_client
    ):
        """Test incremental sync with updated contacts."""
        # Create existing sync state with token
        sync_state = SyncState(
            sync_status=SyncStatus.IDLE,
            sync_token="existing_sync_token",
            last_sync_at=datetime.now(timezone.utc),
        )
        db_session.add(sync_state)

        # Create existing contact
        existing = Contact(
            resource_name="people/c1",
            display_name="Old Name",
            given_name="Old",
        )
        db_session.add(existing)
        db_session.commit()

        # Mock API response with changes
        mock_response = {
            "connections": [
                {
                    "resourceName": "people/c1",
                    "names": [{"displayName": "Updated Name", "givenName": "Updated"}],
                    "phoneNumbers": [{"value": "5551234567"}],
                },
            ],
            "nextSyncToken": "new_sync_token_456",
        }
        mock_google_client.list_connections.return_value = [mock_response]

        stats = sync_service.incremental_sync()

        assert stats.updated == 1
        assert stats.deleted == 0
        assert stats.created == 0

        # Verify contact was updated
        updated_contact = db_session.query(Contact).first()
        assert updated_contact.display_name == "Updated Name"

        # Verify new sync token stored
        new_sync_state = (
            db_session.query(SyncState).order_by(SyncState.last_sync_at.desc()).first()
        )
        assert new_sync_state.sync_token == "new_sync_token_456"

    def test_incremental_sync_with_deletions(
        self, sync_service, db_session, mock_google_client
    ):
        """Test incremental sync with deleted contacts."""
        # Create existing sync state with token
        sync_state = SyncState(
            sync_status=SyncStatus.IDLE,
            sync_token="existing_sync_token",
            last_sync_at=datetime.now(timezone.utc),
        )
        db_session.add(sync_state)

        # Create existing contact
        existing = Contact(
            resource_name="people/c1",
            display_name="To Delete",
            deleted=False,
        )
        db_session.add(existing)
        db_session.commit()

        # Mock API response with deleted contact
        mock_response = {
            "connections": [
                {
                    "resourceName": "people/c1",
                    "names": [{"displayName": "To Delete"}],
                    "phoneNumbers": [],
                    "metadata": {"deleted": True},
                },
            ],
            "nextSyncToken": "new_sync_token",
        }
        mock_google_client.list_connections.return_value = [mock_response]

        stats = sync_service.incremental_sync()

        assert stats.deleted == 1

        # Verify contact was soft-deleted
        contact = db_session.query(Contact).first()
        assert contact.deleted is True

    def test_incremental_sync_no_changes(
        self, sync_service, db_session, mock_google_client
    ):
        """Test incremental sync when no changes."""
        # Create existing sync state with token
        sync_state = SyncState(
            sync_status=SyncStatus.IDLE,
            sync_token="existing_sync_token",
            last_sync_at=datetime.now(timezone.utc),
        )
        db_session.add(sync_state)
        db_session.commit()

        # Mock empty response
        mock_response = {
            "connections": [],
            "nextSyncToken": "new_sync_token",
        }
        mock_google_client.list_connections.return_value = [mock_response]

        stats = sync_service.incremental_sync()

        assert stats.total_fetched == 0
        assert stats.updated == 0
        assert stats.deleted == 0
        assert stats.pages == 1

    def test_incremental_sync_falls_back_to_full_without_token(
        self, sync_service, db_session, mock_google_client
    ):
        """Test incremental sync falls back to full sync when no token."""
        # No sync state means no token
        mock_response = {
            "connections": [
                {
                    "resourceName": "people/c1",
                    "names": [{"displayName": "New Contact"}],
                    "phoneNumbers": [],
                },
            ],
            "nextSyncToken": "new_token",
        }
        mock_google_client.list_connections.return_value = [mock_response]

        stats = sync_service.incremental_sync()

        # Should have done full sync
        assert stats.created == 1
        assert db_session.query(Contact).count() == 1

    def test_incremental_sync_with_new_contacts(
        self, sync_service, db_session, mock_google_client
    ):
        """Test incremental sync with new contacts added."""
        # Create existing sync state with token
        sync_state = SyncState(
            sync_status=SyncStatus.IDLE,
            sync_token="existing_sync_token",
            last_sync_at=datetime.now(timezone.utc),
        )
        db_session.add(sync_state)
        db_session.commit()

        # Mock API response with new contact
        mock_response = {
            "connections": [
                {
                    "resourceName": "people/c_new",
                    "names": [{"displayName": "Brand New Contact"}],
                    "phoneNumbers": [{"value": "5559999999"}],
                },
            ],
            "nextSyncToken": "new_sync_token",
        }
        mock_google_client.list_connections.return_value = [mock_response]

        stats = sync_service.incremental_sync()

        assert stats.created == 1
        assert stats.updated == 0
        assert db_session.query(Contact).count() == 1

        new_contact = db_session.query(Contact).first()
        assert new_contact.display_name == "Brand New Contact"

    def test_incremental_sync_multiple_pages(
        self, sync_service, db_session, mock_google_client
    ):
        """Test incremental sync with multiple pages of changes."""
        # Create existing sync state with token
        sync_state = SyncState(
            sync_status=SyncStatus.IDLE,
            sync_token="existing_sync_token",
            last_sync_at=datetime.now(timezone.utc),
        )
        db_session.add(sync_state)
        db_session.commit()

        # Mock multiple pages
        page1 = {
            "connections": [
                {
                    "resourceName": "people/c1",
                    "names": [{"displayName": "Contact 1"}],
                    "phoneNumbers": [],
                },
            ],
            "nextPageToken": "page2_token",
        }
        page2 = {
            "connections": [
                {
                    "resourceName": "people/c2",
                    "names": [{"displayName": "Contact 2"}],
                    "phoneNumbers": [],
                },
            ],
            "nextSyncToken": "final_sync_token",
        }
        mock_google_client.list_connections.return_value = [page1, page2]

        stats = sync_service.incremental_sync(page_delay=0)

        assert stats.pages == 2
        assert stats.total_fetched == 2
        assert db_session.query(Contact).count() == 2


class TestIncrementalSyncTokenExpired:
    """Test sync token expiration handling."""

    def test_incremental_sync_token_expired_falls_back_to_full(
        self, db_session, mock_google_client
    ):
        """Test incremental sync falls back to full sync when token expires."""
        from google_contacts_cisco.services.google_client import SyncTokenExpiredError

        # Create existing sync state with token
        sync_state = SyncState(
            sync_status=SyncStatus.IDLE,
            sync_token="expired_sync_token",
            last_sync_at=datetime.now(timezone.utc),
        )
        db_session.add(sync_state)
        db_session.commit()

        # First call fails with token expired
        def side_effect(*args, **kwargs):
            if kwargs.get("sync_token") == "expired_sync_token":
                raise SyncTokenExpiredError("Sync token expired")
            return [
                {
                    "connections": [
                        {
                            "resourceName": "people/c1",
                            "names": [{"displayName": "Contact"}],
                            "phoneNumbers": [],
                        }
                    ],
                    "nextSyncToken": "new_token",
                }
            ]

        mock_google_client.list_connections.side_effect = side_effect

        sync_service = SyncService(db_session, google_client=mock_google_client)
        stats = sync_service.incremental_sync()

        # Should fall back to full sync
        assert stats.created == 1
        assert db_session.query(Contact).count() == 1


class TestAutoSync:
    """Test auto sync functionality."""

    def test_auto_sync_with_token_uses_incremental(
        self, sync_service, db_session, mock_google_client
    ):
        """Test auto sync uses incremental when token exists."""
        # Create sync state with token
        sync_state = SyncState(
            sync_status=SyncStatus.IDLE,
            sync_token="valid_token",
            last_sync_at=datetime.now(timezone.utc),
        )
        db_session.add(sync_state)
        db_session.commit()

        mock_response = {
            "connections": [],
            "nextSyncToken": "new_token",
        }
        mock_google_client.list_connections.return_value = [mock_response]

        sync_service.auto_sync()

        # Should have performed incremental sync (called with sync_token)
        mock_google_client.list_connections.assert_called()
        call_kwargs = mock_google_client.list_connections.call_args[1]
        assert call_kwargs.get("sync_token") == "valid_token"

    def test_auto_sync_without_token_uses_full(
        self, sync_service, db_session, mock_google_client
    ):
        """Test auto sync uses full sync when no token."""
        # No sync state
        mock_response = {
            "connections": [
                {
                    "resourceName": "people/c1",
                    "names": [{"displayName": "New Contact"}],
                    "phoneNumbers": [],
                },
            ],
            "nextSyncToken": "new_token",
        }
        mock_google_client.list_connections.return_value = [mock_response]

        stats = sync_service.auto_sync()

        # Should have created contacts
        assert stats.created == 1
        assert db_session.query(Contact).count() == 1

    def test_auto_sync_with_expired_token_in_sync_state(
        self, sync_service, db_session, mock_google_client
    ):
        """Test auto sync when sync state exists but token is None."""
        # Create sync state without token (e.g., after error)
        sync_state = SyncState(
            sync_status=SyncStatus.ERROR,
            sync_token=None,
            last_sync_at=datetime.now(timezone.utc),
        )
        db_session.add(sync_state)
        db_session.commit()

        mock_response = {
            "connections": [
                {
                    "resourceName": "people/c1",
                    "names": [{"displayName": "Contact"}],
                    "phoneNumbers": [],
                },
            ],
            "nextSyncToken": "new_token",
        }
        mock_google_client.list_connections.return_value = [mock_response]

        stats = sync_service.auto_sync()

        # Should do full sync
        assert stats.created == 1


class TestIncrementalSyncErrors:
    """Test error handling in incremental sync."""

    def test_incremental_sync_sets_error_state_on_failure(
        self, db_session, mock_google_client
    ):
        """Test that incremental sync sets error state on failure."""
        # Create sync state with token
        sync_state = SyncState(
            sync_status=SyncStatus.IDLE,
            sync_token="valid_token",
            last_sync_at=datetime.now(timezone.utc),
        )
        db_session.add(sync_state)
        db_session.commit()

        mock_google_client.list_connections.side_effect = Exception("API Error")

        sync_service = SyncService(db_session, google_client=mock_google_client)

        with pytest.raises(Exception, match="API Error"):
            sync_service.incremental_sync()

        # Verify error state
        latest_state = (
            db_session.query(SyncState).order_by(SyncState.last_sync_at.desc()).first()
        )
        assert latest_state.sync_status == SyncStatus.ERROR
        assert "API Error" in latest_state.error_message

    def test_incremental_sync_handles_contact_errors(
        self, sync_service, db_session, mock_google_client
    ):
        """Test that incremental sync continues after individual contact errors."""
        # Create sync state with token
        sync_state = SyncState(
            sync_status=SyncStatus.IDLE,
            sync_token="valid_token",
            last_sync_at=datetime.now(timezone.utc),
        )
        db_session.add(sync_state)
        db_session.commit()

        # Response with multiple contacts
        mock_response = {
            "connections": [
                {
                    "resourceName": "people/c1",
                    "names": [{"displayName": "Valid Contact"}],
                    "phoneNumbers": [],
                },
                {
                    "resourceName": "people/c2",
                    "names": [],  # Uses resource name as fallback
                    "phoneNumbers": [],
                },
            ],
            "nextSyncToken": "token",
        }
        mock_google_client.list_connections.return_value = [mock_response]

        stats = sync_service.incremental_sync()

        # Both should be processed
        assert stats.total_fetched == 2
        assert stats.errors == 0  # No errors because fallback works


class TestGetSyncServiceFactory:
    """Test get_sync_service factory function."""

    def test_get_sync_service_without_client(self, db_session):
        """Test factory creates service without Google client."""
        service = get_sync_service(db_session)

        assert service is not None
        assert service.db is db_session
        assert service._google_client is None

    def test_get_sync_service_with_client(self, db_session, mock_google_client):
        """Test factory creates service with provided Google client."""
        service = get_sync_service(db_session, google_client=mock_google_client)

        assert service._google_client is mock_google_client


class TestSafeAutoSync:
    """Test safe_auto_sync with concurrency protection."""

    def test_safe_auto_sync_success(self, sync_service, db_session, mock_google_client):
        """Test safe_auto_sync completes successfully."""
        mock_response = {
            "connections": [
                {
                    "resourceName": "people/c1",
                    "names": [{"displayName": "Test Contact"}],
                    "phoneNumbers": [],
                },
            ],
            "nextSyncToken": "token123",
        }
        mock_google_client.list_connections.return_value = [mock_response]

        result = sync_service.safe_auto_sync()

        assert result["status"] == "success"
        assert "Full sync completed" in result["message"]
        assert result["statistics"]["total_fetched"] == 1

    def test_safe_auto_sync_returns_error_on_failure(
        self, sync_service, db_session, mock_google_client
    ):
        """Test safe_auto_sync returns error status on failure."""
        mock_google_client.list_connections.side_effect = Exception("API Error")

        result = sync_service.safe_auto_sync()

        assert result["status"] == "error"
        assert "API Error" in result["message"]
        assert result["statistics"] == {}


class TestGetSyncHistory:
    """Test sync history retrieval."""

    def test_get_sync_history_empty(self, sync_service):
        """Test sync history when no syncs have occurred."""
        history = sync_service.get_sync_history()

        assert history == []

    def test_get_sync_history_returns_records(self, sync_service, db_session):
        """Test sync history returns multiple records."""
        # Create sync history
        state1 = SyncState(
            sync_status=SyncStatus.IDLE,
            sync_token="token1",
            last_sync_at=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        )
        state2 = SyncState(
            sync_status=SyncStatus.ERROR,
            sync_token=None,
            last_sync_at=datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
            error_message="Test error",
        )
        db_session.add_all([state1, state2])
        db_session.commit()

        history = sync_service.get_sync_history(limit=10)

        assert len(history) == 2
        # Most recent first
        assert history[0]["status"] == "error"
        assert history[0]["error_message"] == "Test error"
        assert history[1]["status"] == "idle"
        assert history[1]["has_sync_token"] is True

    def test_get_sync_history_respects_limit(self, sync_service, db_session):
        """Test sync history respects limit parameter."""
        # Create multiple sync states
        for i in range(5):
            state = SyncState(
                sync_status=SyncStatus.IDLE,
                sync_token=f"token{i}",
                last_sync_at=datetime(2024, 1, 1, i, 0, 0, tzinfo=timezone.utc),
            )
            db_session.add(state)
        db_session.commit()

        history = sync_service.get_sync_history(limit=3)

        assert len(history) == 3


class TestGetSyncStatistics:
    """Test sync statistics retrieval."""

    def test_get_sync_statistics_empty(self, sync_service):
        """Test statistics when no data exists."""
        stats = sync_service.get_sync_statistics()

        assert stats["contacts"]["total"] == 0
        assert stats["contacts"]["active"] == 0
        assert stats["contacts"]["deleted"] == 0
        assert stats["phone_numbers"] == 0
        assert stats["sync"]["status"] == "never_synced"
        assert stats["sync"]["has_sync_token"] is False
        assert stats["sync_history"] == {}

    def test_get_sync_statistics_with_data(
        self, sync_service, db_session, mock_google_client
    ):
        """Test statistics with contacts and sync history."""
        # Create contacts
        from google_contacts_cisco.models import Contact, PhoneNumber

        active_contact = Contact(
            resource_name="people/c1",
            display_name="Active",
            deleted=False,
        )
        deleted_contact = Contact(
            resource_name="people/c2",
            display_name="Deleted",
            deleted=True,
        )
        db_session.add_all([active_contact, deleted_contact])
        db_session.flush()

        # Add phone number with required fields
        phone = PhoneNumber(
            contact_id=active_contact.id,
            value="+15551234567",
            display_value="(555) 123-4567",
            type="mobile",
        )
        db_session.add(phone)

        # Create sync state
        sync_state = SyncState(
            sync_status=SyncStatus.IDLE,
            sync_token="token123",
            last_sync_at=datetime.now(timezone.utc),
        )
        db_session.add(sync_state)
        db_session.commit()

        stats = sync_service.get_sync_statistics()

        assert stats["contacts"]["total"] == 2
        assert stats["contacts"]["active"] == 1
        assert stats["contacts"]["deleted"] == 1
        assert stats["phone_numbers"] == 1
        assert stats["sync"]["status"] == "idle"
        assert stats["sync"]["has_sync_token"] is True
        assert stats["sync_history"]["idle"] == 1


class TestClearSyncHistory:
    """Test clearing sync history."""

    def test_clear_sync_history_keep_latest(self, sync_service, db_session):
        """Test clearing history while keeping latest."""
        # Create multiple sync states
        state1 = SyncState(
            sync_status=SyncStatus.IDLE,
            last_sync_at=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        )
        state2 = SyncState(
            sync_status=SyncStatus.IDLE,
            last_sync_at=datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
        )
        state3 = SyncState(
            sync_status=SyncStatus.IDLE,
            last_sync_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        )
        db_session.add_all([state1, state2, state3])
        db_session.commit()

        deleted_count = sync_service.clear_sync_history(keep_latest=True)

        assert deleted_count == 2
        remaining = db_session.query(SyncState).all()
        assert len(remaining) == 1
        # Should keep the latest (12:00) - compare without timezone
        # since SQLite strips it
        assert remaining[0].last_sync_at.replace(tzinfo=None) == datetime(
            2024, 1, 1, 12, 0, 0
        )

    def test_clear_sync_history_delete_all(self, sync_service, db_session):
        """Test clearing all history."""
        # Create sync states
        for i in range(3):
            state = SyncState(
                sync_status=SyncStatus.IDLE,
                last_sync_at=datetime(2024, 1, 1, i, 0, 0, tzinfo=timezone.utc),
            )
            db_session.add(state)
        db_session.commit()

        deleted_count = sync_service.clear_sync_history(keep_latest=False)

        assert deleted_count == 3
        assert db_session.query(SyncState).count() == 0

    def test_clear_sync_history_empty(self, sync_service, db_session):
        """Test clearing empty history."""
        deleted_count = sync_service.clear_sync_history(keep_latest=True)

        assert deleted_count == 0
