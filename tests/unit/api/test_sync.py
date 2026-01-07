"""Test Sync API Endpoints.

This module tests the FastAPI endpoints for contact synchronization.
These are unit tests that mock the sync service to test the API layer in isolation.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from google_contacts_cisco.main import app
from google_contacts_cisco.services.sync_service import SyncStatistics


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestSyncStatusEndpoint:
    """Test GET /api/sync/status endpoint."""

    @patch("google_contacts_cisco.api.sync.get_sync_service")
    def test_status_never_synced(self, mock_get_service, client):
        """Test status when no sync has occurred."""
        mock_service = Mock()
        mock_service.get_sync_status.return_value = {
            "status": "never_synced",
            "last_sync_at": None,
            "has_sync_token": False,
            "error_message": None,
            "contact_count": 0,
            "total_contacts": 0,
        }
        mock_get_service.return_value = mock_service

        response = client.get("/api/sync/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "never_synced"
        assert data["last_sync_at"] is None
        assert data["has_sync_token"] is False
        assert data["error_message"] is None
        assert data["contact_count"] == 0
        assert data["total_contacts"] == 0

    @patch("google_contacts_cisco.api.sync.get_sync_service")
    def test_status_after_successful_sync(self, mock_get_service, client):
        """Test status after a successful sync."""
        mock_service = Mock()
        mock_service.get_sync_status.return_value = {
            "status": "idle",
            "last_sync_at": "2024-01-15T10:30:00Z",
            "has_sync_token": True,
            "error_message": None,
            "contact_count": 100,
            "total_contacts": 105,
        }
        mock_get_service.return_value = mock_service

        response = client.get("/api/sync/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "idle"
        assert data["has_sync_token"] is True
        assert data["contact_count"] == 100
        assert data["total_contacts"] == 105

    @patch("google_contacts_cisco.api.sync.get_sync_service")
    def test_status_syncing(self, mock_get_service, client):
        """Test status while sync is in progress."""
        mock_service = Mock()
        mock_service.get_sync_status.return_value = {
            "status": "syncing",
            "last_sync_at": "2024-01-15T10:30:00Z",
            "has_sync_token": False,
            "error_message": None,
            "contact_count": 50,
            "total_contacts": 50,
        }
        mock_get_service.return_value = mock_service

        response = client.get("/api/sync/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "syncing"

    @patch("google_contacts_cisco.api.sync.get_sync_service")
    def test_status_error(self, mock_get_service, client):
        """Test status after sync error."""
        mock_service = Mock()
        mock_service.get_sync_status.return_value = {
            "status": "error",
            "last_sync_at": "2024-01-15T10:30:00Z",
            "has_sync_token": False,
            "error_message": "Connection failed",
            "contact_count": 0,
            "total_contacts": 0,
        }
        mock_get_service.return_value = mock_service

        response = client.get("/api/sync/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["error_message"] == "Connection failed"


class TestFullSyncEndpoint:
    """Test POST /api/sync/full endpoint."""

    @patch("google_contacts_cisco.api.sync.is_authenticated")
    def test_full_sync_not_authenticated(self, mock_auth, client):
        """Test full sync fails when not authenticated."""
        mock_auth.return_value = False

        response = client.post("/api/sync/full")

        assert response.status_code == 401
        data = response.json()
        assert "Not authenticated" in data["detail"]

    @patch("google_contacts_cisco.api.sync.is_authenticated")
    @patch("google_contacts_cisco.api.sync.get_sync_service")
    def test_full_sync_already_in_progress(
        self, mock_get_service, mock_auth, client
    ):
        """Test full sync fails when already in progress."""
        mock_auth.return_value = True
        mock_service = Mock()
        mock_service.is_sync_in_progress.return_value = True
        mock_get_service.return_value = mock_service

        response = client.post("/api/sync/full")

        assert response.status_code == 409
        data = response.json()
        assert "already in progress" in data["detail"]

    @patch("google_contacts_cisco.api.sync.is_authenticated")
    @patch("google_contacts_cisco.api.sync.get_sync_service")
    def test_full_sync_success(self, mock_get_service, mock_auth, client):
        """Test successful full sync."""
        mock_auth.return_value = True
        mock_service = Mock()
        mock_service.is_sync_in_progress.return_value = False
        mock_service.full_sync.return_value = SyncStatistics(
            total_fetched=100,
            created=80,
            updated=20,
            errors=0,
            pages=5,
        )
        mock_get_service.return_value = mock_service

        response = client.post("/api/sync/full")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Full sync completed successfully"
        assert data["statistics"]["total_fetched"] == 100
        assert data["statistics"]["created"] == 80
        assert data["statistics"]["updated"] == 20

    @patch("google_contacts_cisco.api.sync.is_authenticated")
    @patch("google_contacts_cisco.api.sync.get_sync_service")
    def test_full_sync_credentials_error(
        self, mock_get_service, mock_auth, client
    ):
        """Test full sync with credentials error."""
        from google_contacts_cisco.services.google_client import CredentialsError

        mock_auth.return_value = True
        mock_service = Mock()
        mock_service.is_sync_in_progress.return_value = False
        mock_service.full_sync.side_effect = CredentialsError("Invalid token")
        mock_get_service.return_value = mock_service

        response = client.post("/api/sync/full")

        assert response.status_code == 401
        data = response.json()
        assert "Invalid token" in data["detail"]

    @patch("google_contacts_cisco.api.sync.is_authenticated")
    @patch("google_contacts_cisco.api.sync.get_sync_service")
    def test_full_sync_server_error(
        self, mock_get_service, mock_auth, client
    ):
        """Test full sync with unexpected error."""
        mock_auth.return_value = True
        mock_service = Mock()
        mock_service.is_sync_in_progress.return_value = False
        mock_service.full_sync.side_effect = Exception("Database error")
        mock_get_service.return_value = mock_service

        response = client.post("/api/sync/full")

        assert response.status_code == 500
        data = response.json()
        assert "Database error" in data["detail"]


class TestIncrementalSyncEndpoint:
    """Test POST /api/sync/incremental endpoint."""

    @patch("google_contacts_cisco.api.sync.is_authenticated")
    def test_incremental_sync_not_authenticated(self, mock_auth, client):
        """Test incremental sync fails when not authenticated."""
        mock_auth.return_value = False

        response = client.post("/api/sync/incremental")

        assert response.status_code == 401
        data = response.json()
        assert "Not authenticated" in data["detail"]

    @patch("google_contacts_cisco.api.sync.is_authenticated")
    @patch("google_contacts_cisco.api.sync.get_sync_service")
    def test_incremental_sync_already_in_progress(
        self, mock_get_service, mock_auth, client
    ):
        """Test incremental sync fails when already in progress."""
        mock_auth.return_value = True
        mock_service = Mock()
        mock_service.is_sync_in_progress.return_value = True
        mock_get_service.return_value = mock_service

        response = client.post("/api/sync/incremental")

        assert response.status_code == 409
        data = response.json()
        assert "already in progress" in data["detail"]

    @patch("google_contacts_cisco.api.sync.is_authenticated")
    @patch("google_contacts_cisco.api.sync.get_sync_service")
    def test_incremental_sync_success(self, mock_get_service, mock_auth, client):
        """Test successful incremental sync."""
        mock_auth.return_value = True
        mock_service = Mock()
        mock_service.is_sync_in_progress.return_value = False
        mock_service.incremental_sync.return_value = SyncStatistics(
            total_fetched=10,
            created=2,
            updated=8,
            deleted=3,
            errors=0,
            pages=1,
        )
        mock_get_service.return_value = mock_service

        response = client.post("/api/sync/incremental")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Incremental sync completed successfully"
        assert data["statistics"]["total_fetched"] == 10
        assert data["statistics"]["created"] == 2
        assert data["statistics"]["updated"] == 8
        assert data["statistics"]["deleted"] == 3

    @patch("google_contacts_cisco.api.sync.is_authenticated")
    @patch("google_contacts_cisco.api.sync.get_sync_service")
    def test_incremental_sync_with_no_changes(
        self, mock_get_service, mock_auth, client
    ):
        """Test incremental sync when no changes."""
        mock_auth.return_value = True
        mock_service = Mock()
        mock_service.is_sync_in_progress.return_value = False
        mock_service.incremental_sync.return_value = SyncStatistics(
            total_fetched=0,
            created=0,
            updated=0,
            deleted=0,
            errors=0,
            pages=1,
        )
        mock_get_service.return_value = mock_service

        response = client.post("/api/sync/incremental")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["statistics"]["total_fetched"] == 0

    @patch("google_contacts_cisco.api.sync.is_authenticated")
    @patch("google_contacts_cisco.api.sync.get_sync_service")
    def test_incremental_sync_credentials_error(
        self, mock_get_service, mock_auth, client
    ):
        """Test incremental sync with credentials error."""
        from google_contacts_cisco.services.google_client import CredentialsError

        mock_auth.return_value = True
        mock_service = Mock()
        mock_service.is_sync_in_progress.return_value = False
        mock_service.incremental_sync.side_effect = CredentialsError("Token expired")
        mock_get_service.return_value = mock_service

        response = client.post("/api/sync/incremental")

        assert response.status_code == 401
        data = response.json()
        assert "Token expired" in data["detail"]

    @patch("google_contacts_cisco.api.sync.is_authenticated")
    @patch("google_contacts_cisco.api.sync.get_sync_service")
    def test_incremental_sync_server_error(
        self, mock_get_service, mock_auth, client
    ):
        """Test incremental sync with unexpected error."""
        mock_auth.return_value = True
        mock_service = Mock()
        mock_service.is_sync_in_progress.return_value = False
        mock_service.incremental_sync.side_effect = Exception("API failure")
        mock_get_service.return_value = mock_service

        response = client.post("/api/sync/incremental")

        assert response.status_code == 500
        data = response.json()
        assert "API failure" in data["detail"]


class TestAutoSyncEndpoint:
    """Test POST /api/sync endpoint."""

    @patch("google_contacts_cisco.api.sync.is_authenticated")
    def test_auto_sync_not_authenticated(self, mock_auth, client):
        """Test auto sync fails when not authenticated."""
        mock_auth.return_value = False

        response = client.post("/api/sync")

        assert response.status_code == 401
        data = response.json()
        assert "Not authenticated" in data["detail"]

    @patch("google_contacts_cisco.api.sync.is_authenticated")
    @patch("google_contacts_cisco.api.sync.get_sync_service")
    def test_auto_sync_already_in_progress(
        self, mock_get_service, mock_auth, client
    ):
        """Test auto sync fails when already in progress."""
        mock_auth.return_value = True
        mock_service = Mock()
        mock_service.is_sync_in_progress.return_value = True
        mock_get_service.return_value = mock_service

        response = client.post("/api/sync")

        assert response.status_code == 409
        data = response.json()
        assert "already in progress" in data["detail"]

    @patch("google_contacts_cisco.api.sync.is_authenticated")
    @patch("google_contacts_cisco.api.sync.get_sync_service")
    def test_auto_sync_success_incremental(
        self, mock_get_service, mock_auth, client
    ):
        """Test successful auto sync (incremental)."""
        mock_auth.return_value = True
        mock_service = Mock()
        mock_service.is_sync_in_progress.return_value = False
        # Incremental sync stats (no created, only updated)
        mock_service.auto_sync.return_value = SyncStatistics(
            total_fetched=5,
            created=0,
            updated=5,
            deleted=0,
            errors=0,
            pages=1,
        )
        mock_get_service.return_value = mock_service

        response = client.post("/api/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "sync completed successfully" in data["message"]
        assert data["statistics"]["total_fetched"] == 5

    @patch("google_contacts_cisco.api.sync.is_authenticated")
    @patch("google_contacts_cisco.api.sync.get_sync_service")
    def test_auto_sync_success_full(
        self, mock_get_service, mock_auth, client
    ):
        """Test successful auto sync (full)."""
        mock_auth.return_value = True
        mock_service = Mock()
        mock_service.is_sync_in_progress.return_value = False
        # Full sync stats (created contacts)
        mock_service.auto_sync.return_value = SyncStatistics(
            total_fetched=100,
            created=100,
            updated=0,
            deleted=0,
            errors=0,
            pages=5,
        )
        mock_get_service.return_value = mock_service

        response = client.post("/api/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["statistics"]["created"] == 100

    @patch("google_contacts_cisco.api.sync.is_authenticated")
    @patch("google_contacts_cisco.api.sync.get_sync_service")
    def test_auto_sync_no_changes(
        self, mock_get_service, mock_auth, client
    ):
        """Test auto sync with no changes."""
        mock_auth.return_value = True
        mock_service = Mock()
        mock_service.is_sync_in_progress.return_value = False
        mock_service.auto_sync.return_value = SyncStatistics(
            total_fetched=0,
            created=0,
            updated=0,
            deleted=0,
            errors=0,
            pages=1,
        )
        mock_get_service.return_value = mock_service

        response = client.post("/api/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["statistics"]["total_fetched"] == 0

    @patch("google_contacts_cisco.api.sync.is_authenticated")
    @patch("google_contacts_cisco.api.sync.get_sync_service")
    def test_auto_sync_credentials_error(
        self, mock_get_service, mock_auth, client
    ):
        """Test auto sync with credentials error."""
        from google_contacts_cisco.services.google_client import CredentialsError

        mock_auth.return_value = True
        mock_service = Mock()
        mock_service.is_sync_in_progress.return_value = False
        mock_service.auto_sync.side_effect = CredentialsError("Invalid credentials")
        mock_get_service.return_value = mock_service

        response = client.post("/api/sync")

        assert response.status_code == 401
        data = response.json()
        assert "Invalid credentials" in data["detail"]

    @patch("google_contacts_cisco.api.sync.is_authenticated")
    @patch("google_contacts_cisco.api.sync.get_sync_service")
    def test_auto_sync_server_error(
        self, mock_get_service, mock_auth, client
    ):
        """Test auto sync with unexpected error."""
        mock_auth.return_value = True
        mock_service = Mock()
        mock_service.is_sync_in_progress.return_value = False
        mock_service.auto_sync.side_effect = Exception("Connection error")
        mock_get_service.return_value = mock_service

        response = client.post("/api/sync")

        assert response.status_code == 500
        data = response.json()
        assert "Connection error" in data["detail"]


class TestNeedsSyncEndpoint:
    """Test GET /api/sync/needs-sync endpoint."""

    @patch("google_contacts_cisco.api.sync.get_sync_service")
    def test_needs_sync_never_synced(self, mock_get_service, client):
        """Test needs sync when never synced before."""
        mock_service = Mock()
        mock_service.needs_full_sync.return_value = True
        mock_service.get_sync_status.return_value = {
            "status": "never_synced",
            "has_sync_token": False,
        }
        mock_get_service.return_value = mock_service

        response = client.get("/api/sync/needs-sync")

        assert response.status_code == 200
        data = response.json()
        assert data["needs_full_sync"] is True
        assert data["reason"] == "No previous sync found"

    @patch("google_contacts_cisco.api.sync.get_sync_service")
    def test_needs_sync_no_token(self, mock_get_service, client):
        """Test needs sync when no sync token available."""
        mock_service = Mock()
        mock_service.needs_full_sync.return_value = True
        mock_service.get_sync_status.return_value = {
            "status": "idle",
            "has_sync_token": False,
        }
        mock_get_service.return_value = mock_service

        response = client.get("/api/sync/needs-sync")

        assert response.status_code == 200
        data = response.json()
        assert data["needs_full_sync"] is True
        assert data["reason"] == "Sync token not available"

    @patch("google_contacts_cisco.api.sync.get_sync_service")
    def test_no_sync_needed(self, mock_get_service, client):
        """Test when incremental sync is available."""
        mock_service = Mock()
        mock_service.needs_full_sync.return_value = False
        mock_get_service.return_value = mock_service

        response = client.get("/api/sync/needs-sync")

        assert response.status_code == 200
        data = response.json()
        assert data["needs_full_sync"] is False
        assert data["reason"] == "Incremental sync available"
