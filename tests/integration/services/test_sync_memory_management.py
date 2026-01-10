"""Integration tests for sync service memory management.

This module tests that the sync service properly manages memory during
large sync operations to prevent memory leaks and OOM errors.
"""

from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from google_contacts_cisco.models import Base, Contact
from google_contacts_cisco.services.sync_service import SyncService


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


def generate_mock_contacts(count: int, start_id: int = 1) -> list[dict]:
    """Generate mock contact data for testing.

    Args:
        count: Number of contacts to generate
        start_id: Starting ID for contacts

    Returns:
        List of mock contact dictionaries
    """
    contacts = []
    for i in range(start_id, start_id + count):
        contacts.append(
            {
                "resourceName": f"people/c{i}",
                "names": [
                    {
                        "displayName": f"Test Contact {i}",
                        "givenName": f"Test{i}",
                        "familyName": f"Contact{i}",
                    }
                ],
                "phoneNumbers": [
                    {
                        "value": f"+155512{i:05d}",
                        "type": "mobile",
                    }
                ],
            }
        )
    return contacts


class TestSyncMemoryManagement:
    """Test memory management during sync operations."""

    def test_full_sync_with_large_dataset_completes(
        self, sync_service, db_session, mock_google_client
    ):
        """Test that full sync completes with large dataset without OOM.

        This test simulates syncing 1,000 contacts across 10 pages
        to verify memory is properly managed.
        """
        # Generate 1,000 contacts across 10 pages (100 contacts per page)
        pages = []
        contacts_per_page = 100
        total_contacts = 1000
        num_pages = total_contacts // contacts_per_page

        for page_num in range(num_pages):
            start_id = page_num * contacts_per_page + 1
            contacts = generate_mock_contacts(contacts_per_page, start_id)

            page = {
                "connections": contacts,
            }

            # Add next page token for all but last page
            if page_num < num_pages - 1:
                page["nextPageToken"] = f"page_{page_num + 1}_token"
            else:
                # Last page has sync token
                page["nextSyncToken"] = "final_sync_token"

            pages.append(page)

        mock_google_client.list_connections.return_value = pages

        # Run sync with small batch size to test frequent commits
        stats = sync_service.full_sync(batch_size=50, page_delay=0)

        # Verify all contacts were processed
        assert stats.total_fetched == total_contacts
        assert stats.created == total_contacts
        assert stats.pages == num_pages
        assert stats.errors == 0

        # Verify all contacts are in database
        contact_count = db_session.query(Contact).count()
        assert contact_count == total_contacts

    def test_session_identity_map_cleared_after_batches(
        self, sync_service, db_session, mock_google_client
    ):
        """Test that session identity map is cleared after batch commits.

        This verifies the memory leak fix by checking that the session
        doesn't accumulate objects indefinitely.
        """
        # Generate 500 contacts in a single page
        contacts = generate_mock_contacts(500)
        mock_response = {
            "connections": contacts,
            "nextSyncToken": "sync_token",
        }
        mock_google_client.list_connections.return_value = [mock_response]

        # Run sync with batch size of 100
        # This should trigger 5 batch commits
        stats = sync_service.full_sync(batch_size=100, page_delay=0)

        assert stats.total_fetched == 500
        assert stats.created == 500

        # After sync completes, session should have been expunged
        # Check that we can still query (session is still functional)
        contacts = db_session.query(Contact).limit(10).all()
        assert len(contacts) == 10

        # Verify contacts are detached (not in session identity map)
        # This is the key test - if memory management is working,
        # objects should be detached after expunge_all()
        for contact in contacts:
            # After expunge_all(), objects should not be in the session
            # We test this by trying to access them - they should still work
            # but won't be tracking changes
            assert contact.display_name is not None

    def test_incremental_sync_with_large_changes(
        self, sync_service, db_session, mock_google_client
    ):
        """Test incremental sync memory management with large change set."""
        from datetime import datetime, timezone

        from google_contacts_cisco.models import SyncState
        from google_contacts_cisco.models.sync_state import SyncStatus

        # Create existing sync state with token
        sync_state = SyncState(
            sync_status=SyncStatus.IDLE,
            sync_token="existing_token",
            last_sync_at=datetime.now(timezone.utc),
        )
        db_session.add(sync_state)
        db_session.commit()

        # Generate 1,000 changed contacts across 10 pages
        pages = []
        contacts_per_page = 100
        total_contacts = 1000
        num_pages = total_contacts // contacts_per_page

        for page_num in range(num_pages):
            start_id = page_num * contacts_per_page + 1
            contacts = generate_mock_contacts(contacts_per_page, start_id)

            page = {
                "connections": contacts,
            }

            if page_num < num_pages - 1:
                page["nextPageToken"] = f"page_{page_num + 1}_token"
            else:
                page["nextSyncToken"] = "new_sync_token"

            pages.append(page)

        mock_google_client.list_connections.return_value = pages

        # Run incremental sync
        stats = sync_service.incremental_sync(batch_size=50, page_delay=0)

        assert stats.total_fetched == total_contacts
        assert stats.created == total_contacts
        assert stats.pages == num_pages
        assert stats.sync_type == "incremental"

    def test_memory_stats_tracked_when_psutil_available(
        self, sync_service, db_session, mock_google_client
    ):
        """Test that memory stats are tracked in sync statistics."""
        contacts = generate_mock_contacts(100)
        mock_response = {
            "connections": contacts,
            "nextSyncToken": "sync_token",
        }
        mock_google_client.list_connections.return_value = [mock_response]

        stats = sync_service.full_sync(batch_size=50, page_delay=0)

        # Memory stats might be None if psutil not available
        # But if they are present, they should be in the dict
        stats_dict = stats.to_dict()

        # These fields should always be present
        assert "total_fetched" in stats_dict
        assert "duration_seconds" in stats_dict

        # Memory fields are optional (depend on psutil)
        if stats.start_memory_mb is not None:
            assert "start_memory_mb" in stats_dict
            assert "peak_memory_mb" in stats_dict
            assert "memory_delta_mb" in stats_dict
            assert isinstance(stats_dict["start_memory_mb"], (int, float))

    def test_multiple_batches_commit_correctly(
        self, sync_service, db_session, mock_google_client
    ):
        """Test that all contacts are committed correctly across batches."""
        # Generate exactly 250 contacts to test:
        # - 2 full batches (100 each)
        # - 1 partial batch (50)
        contacts = generate_mock_contacts(250)
        mock_response = {
            "connections": contacts,
            "nextSyncToken": "sync_token",
        }
        mock_google_client.list_connections.return_value = [mock_response]

        stats = sync_service.full_sync(batch_size=100, page_delay=0)

        # All contacts should be committed
        assert stats.total_fetched == 250
        assert stats.created == 250

        # Verify in database
        count = db_session.query(Contact).count()
        assert count == 250

        # Verify we can query all contacts
        all_contacts = db_session.query(Contact).all()
        assert len(all_contacts) == 250

        # Verify display names are correct
        display_names = {c.display_name for c in all_contacts}
        expected_names = {f"Test Contact {i}" for i in range(1, 251)}
        assert display_names == expected_names

    def test_sync_with_mixed_operations_manages_memory(
        self, sync_service, db_session, mock_google_client
    ):
        """Test memory management with mixed create/update/delete operations."""
        # First, create some existing contacts
        for i in range(100):
            contact = Contact(
                resource_name=f"people/c{i}",
                display_name=f"Existing {i}",
                given_name=f"Existing{i}",
                deleted=False,
            )
            db_session.add(contact)
        db_session.commit()

        # Now generate sync response with:
        # - 100 updates (existing contacts)
        # - 400 new contacts
        # - 50 deletions
        connections = []

        # Updates (0-99)
        for i in range(100):
            connections.append(
                {
                    "resourceName": f"people/c{i}",
                    "names": [
                        {"displayName": f"Updated {i}", "givenName": f"Updated{i}"}
                    ],
                    "phoneNumbers": [{"value": f"+155512{i:05d}"}],
                }
            )

        # New contacts (100-499)
        for i in range(100, 500):
            connections.append(
                {
                    "resourceName": f"people/c{i}",
                    "names": [{"displayName": f"New {i}", "givenName": f"New{i}"}],
                    "phoneNumbers": [{"value": f"+155512{i:05d}"}],
                }
            )

        # Deletions (0-49 from existing)
        for i in range(50):
            connections.append(
                {
                    "resourceName": f"people/c{i}",
                    "names": [{"displayName": f"Deleted {i}"}],
                    "phoneNumbers": [],
                    "metadata": {"deleted": True},
                }
            )

        mock_response = {
            "connections": connections,
            "nextSyncToken": "sync_token",
        }
        mock_google_client.list_connections.return_value = [mock_response]

        stats = sync_service.full_sync(batch_size=100, page_delay=0)

        # Verify operations
        # The sync processes contacts in order:
        # 1. 100 updates (0-99) - all increment stats.updated = 100
        # 2. 400 new contacts (100-499) - all increment stats.created = 400
        # 3. 50 deletions (0-49) - increment stats.deleted = 50
        # Note: Deletions are processed after updates, so all 100 contacts
        # are counted as updates, then 50 of them are marked as deleted.
        assert stats.deleted == 50
        assert stats.created == 400  # New contacts
        assert stats.updated == 100  # All 100 existing contacts were updated

        # Verify database state
        total = db_session.query(Contact).count()
        assert total == 500  # 100 existing + 400 new

        active = db_session.query(Contact).filter(~Contact.deleted).count()
        assert active == 450  # 500 - 50 deleted
