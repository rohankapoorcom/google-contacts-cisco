"""Integration tests for concurrent sync operations.

This module tests the race condition fixes in the sync service,
ensuring that multiple simultaneous sync requests are handled properly.
"""

import threading
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from google_contacts_cisco.main import app
from google_contacts_cisco.models import Base, SyncState
from google_contacts_cisco.models.sync_state import SyncStatus
from google_contacts_cisco.services.sync_service import SyncInProgressError


class TestConcurrentSyncViaAPI:
    """Test concurrent sync operations via API endpoints."""

    @pytest.fixture
    def mock_auth(self):
        """Mock authentication."""
        with patch(
            "google_contacts_cisco.api.sync.is_authenticated",
            return_value=True,
        ):
            yield

    @pytest.fixture
    def mock_google_client(self):
        """Mock Google client for sync operations."""
        mock_client = Mock()
        # Simulate a slow sync operation
        def slow_list_connections(*args, **kwargs):
            time.sleep(0.5)  # Simulate API delay
            return [
                {
                    "connections": None,
                    "nextPageToken": None,
                    "nextSyncToken": "token123",
                }
            ]

        mock_client.list_connections.side_effect = slow_list_connections
        return mock_client

    def test_concurrent_full_sync_requests(
        self, test_db, mock_auth, mock_google_client
    ):
        """Test that concurrent full sync requests are properly serialized."""
        client = TestClient(app)

        with patch(
            "google_contacts_cisco.services.sync_service.get_google_client",
            return_value=mock_google_client,
        ):
            results = []
            errors = []

            def make_sync_request():
                try:
                    response = client.post("/api/sync/full")
                    results.append(response)
                except Exception as e:
                    errors.append(e)

            # Start two concurrent sync requests
            thread1 = threading.Thread(target=make_sync_request)
            thread2 = threading.Thread(target=make_sync_request)

            thread1.start()
            thread2.start()

            thread1.join(timeout=5)
            thread2.join(timeout=5)

            # One should succeed, one should get 409 Conflict
            assert len(results) == 2
            status_codes = [r.status_code for r in results]

            # Should have one success (200) and one conflict (409)
            assert 200 in status_codes
            assert 409 in status_codes

            # The 409 response should have the right error message
            conflict_response = [r for r in results if r.status_code == 409][0]
            assert "already in progress" in conflict_response.json()["detail"].lower()

    def test_concurrent_incremental_sync_requests(
        self, test_db, mock_auth, mock_google_client
    ):
        """Test concurrent incremental sync requests."""
        # Create initial sync state with token
        sync_state = SyncState(
            sync_status=SyncStatus.IDLE,
            sync_token="token123",
            last_sync_at=datetime.now(timezone.utc),
        )
        test_db.add(sync_state)
        test_db.commit()

        client = TestClient(app)

        with patch(
            "google_contacts_cisco.services.sync_service.get_google_client",
            return_value=mock_google_client,
        ):
            results = []

            def make_sync_request():
                response = client.post("/api/sync/incremental")
                results.append(response)

            # Start two concurrent requests
            thread1 = threading.Thread(target=make_sync_request)
            thread2 = threading.Thread(target=make_sync_request)

            thread1.start()
            thread2.start()

            thread1.join(timeout=5)
            thread2.join(timeout=5)

            # One success, one conflict
            assert len(results) == 2
            status_codes = [r.status_code for r in results]
            assert 200 in status_codes
            assert 409 in status_codes

    def test_concurrent_auto_sync_requests(
        self, test_db, mock_auth, mock_google_client
    ):
        """Test concurrent auto sync requests."""
        client = TestClient(app)

        with patch(
            "google_contacts_cisco.services.sync_service.get_google_client",
            return_value=mock_google_client,
        ):
            results = []

            def make_sync_request():
                response = client.post("/api/sync")
                results.append(response)

            # Start two concurrent requests
            thread1 = threading.Thread(target=make_sync_request)
            thread2 = threading.Thread(target=make_sync_request)

            thread1.start()
            thread2.start()

            thread1.join(timeout=5)
            thread2.join(timeout=5)

            # One success, one conflict
            assert len(results) == 2
            status_codes = [r.status_code for r in results]
            assert 200 in status_codes
            assert 409 in status_codes

    def test_safe_sync_with_concurrent_requests(
        self, test_db, mock_auth, mock_google_client
    ):
        """Test safe sync endpoint with concurrent requests."""
        client = TestClient(app)

        with patch(
            "google_contacts_cisco.services.sync_service.get_google_client",
            return_value=mock_google_client,
        ):
            results = []

            def make_sync_request():
                response = client.post("/api/sync/safe")
                results.append(response)

            # Start two concurrent safe sync requests
            thread1 = threading.Thread(target=make_sync_request)
            thread2 = threading.Thread(target=make_sync_request)

            thread1.start()
            thread2.start()

            thread1.join(timeout=5)
            thread2.join(timeout=5)

            # Both should return responses (one success, one skipped)
            assert len(results) == 2

            # One should be 200 (success), one should be 409 (conflict/skipped)
            status_codes = [r.status_code for r in results]
            assert 200 in status_codes
            assert 409 in status_codes

            # The 409 response should indicate sync was skipped
            conflict_response = [r for r in results if r.status_code == 409][0]
            data = conflict_response.json()
            assert data.get("status") == "skipped"

    def test_rapid_fire_sync_requests(
        self, test_db, mock_auth, mock_google_client
    ):
        """Test handling of many rapid sync requests."""
        client = TestClient(app)

        # Make sync faster for this test
        mock_google_client.list_connections.side_effect = lambda *a, **kw: [
            {
                "connections": None,
                "nextPageToken": None,
                "nextSyncToken": "token123",
            }
        ]

        with patch(
            "google_contacts_cisco.services.sync_service.get_google_client",
            return_value=mock_google_client,
        ):
            results = []

            def make_sync_request():
                response = client.post("/api/sync")
                results.append(response.status_code)

            # Start 5 concurrent requests
            threads = [threading.Thread(target=make_sync_request) for _ in range(5)]

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join(timeout=5)

            # Should have mix of successes and conflicts
            assert len(results) == 5
            assert 200 in results  # At least one success
            assert 409 in results  # At least one conflict
            assert results.count(200) >= 1  # At least one succeeded


class TestConcurrentSyncDatabaseIntegrity:
    """Test that concurrent syncs maintain database integrity."""

    def test_no_duplicate_sync_states_from_concurrent_syncs(
        self, test_db, mock_google_client
    ):
        """Test that concurrent syncs don't create duplicate sync states improperly."""
        from google_contacts_cisco.services.sync_service import SyncService

        # Create two service instances sharing the same DB session
        # (simulating what happens in the real application)
        service1 = SyncService(test_db, google_client=mock_google_client)
        service2 = SyncService(test_db, google_client=mock_google_client)

        mock_google_client.list_connections.return_value = [
            {
                "connections": None,
                "nextPageToken": None,
                "nextSyncToken": "token123",
            }
        ]

        # Try to run both syncs concurrently
        results = []
        exceptions = []

        def run_sync(service):
            try:
                stats = service.full_sync()
                results.append(stats)
            except SyncInProgressError as e:
                exceptions.append(e)
            except Exception as e:
                exceptions.append(e)

        thread1 = threading.Thread(target=run_sync, args=(service1,))
        thread2 = threading.Thread(target=run_sync, args=(service2,))

        thread1.start()
        thread2.start()

        thread1.join(timeout=5)
        thread2.join(timeout=5)

        # One should succeed, one should raise SyncInProgressError
        assert len(results) == 1  # One successful sync
        assert len(exceptions) == 1  # One blocked sync
        assert isinstance(exceptions[0], SyncInProgressError)

        # Verify database has the expected number of sync states
        sync_states = test_db.query(SyncState).all()
        # Should have exactly one sync state (from the successful sync)
        assert len(sync_states) == 1
        assert sync_states[0].sync_status == SyncStatus.IDLE

    def test_sync_state_consistency_with_concurrent_attempts(self, test_db):
        """Test sync state remains consistent with concurrent sync attempts."""
        from google_contacts_cisco.services.sync_service import SyncService

        mock_client = Mock()
        # Make the sync operation take some time
        def slow_list(*args, **kwargs):
            time.sleep(0.2)
            return [
                {
                    "connections": None,
                    "nextPageToken": None,
                    "nextSyncToken": "token123",
                }
            ]

        mock_client.list_connections.side_effect = slow_list

        service = SyncService(test_db, google_client=mock_client)

        completed = []
        blocked = []

        def attempt_sync():
            try:
                service.full_sync()
                completed.append(1)
            except SyncInProgressError:
                blocked.append(1)

        # Launch 3 concurrent sync attempts
        threads = [threading.Thread(target=attempt_sync) for _ in range(3)]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=5)

        # Exactly one should complete, two should be blocked
        assert len(completed) == 1
        assert len(blocked) == 2

        # Final database state should be consistent
        latest_state = (
            test_db.query(SyncState)
            .order_by(SyncState.last_sync_at.desc())
            .first()
        )
        assert latest_state is not None
        assert latest_state.sync_status == SyncStatus.IDLE
        assert latest_state.sync_token == "token123"
