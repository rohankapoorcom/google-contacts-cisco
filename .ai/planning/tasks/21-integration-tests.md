# Task 7.2: Integration Tests

## Overview

Create integration tests that verify components work together correctly across the entire stack, including API endpoints, database operations, service interactions, and external dependencies (with mocking).

## Priority

**P1 (High)** - Required for production readiness

## Dependencies

- Task 7.1: Unit Tests
- All implementation tasks (1-19)

## Objectives

1. Test complete API endpoint workflows
2. Test database transactions and rollbacks
3. Test service integration (sync, search, XML)
4. Test OAuth flow with mocked Google API
5. Test error propagation across layers
6. Test concurrent operations
7. Test data persistence
8. Verify request/response contracts

## Technical Context

### Integration Test Scope
Integration tests verify:
- **API Layer**: HTTP requests/responses, routing, middleware
- **Service Layer**: Business logic coordination
- **Data Layer**: Database operations, transactions
- **External Services**: Mocked Google API responses

### Test Organization
```
tests/
├── integration/
│   ├── test_api_contacts.py
│   ├── test_api_search.py
│   ├── test_api_sync.py
│   ├── test_oauth_flow.py
│   ├── test_directory_xml.py
│   └── test_workflows.py
├── conftest.py
└── fixtures/
    └── mock_google_api.py
```

### Test Database
- Use separate test database (in-memory SQLite)
- Fresh database for each test class
- Automatic rollback after each test

## Acceptance Criteria

- [ ] All API endpoints are tested end-to-end
- [ ] Database transactions are verified
- [ ] Service integration is tested
- [ ] OAuth flow is tested with mocks
- [ ] Error handling is verified across layers
- [ ] Concurrent operations are tested
- [ ] Data persistence is verified
- [ ] Tests run in <2 minutes
- [ ] Tests are isolated and repeatable
- [ ] Mock data matches real API responses

## Implementation Steps

### 1. Create Integration Test Configuration

Update `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "slow: Slow running tests",
]

# Integration test specific settings
[tool.pytest.integration]
timeout = 300  # 5 minutes max for integration tests
```

### 2. Create Mock Google API Fixtures

Create `tests/fixtures/mock_google_api.py`:

```python
"""Mock Google People API responses."""
from typing import List, Dict, Any


def mock_people_connections_response(count: int = 10) -> Dict[str, Any]:
    """Generate mock connections response from Google People API.
    
    Args:
        count: Number of contacts to generate
        
    Returns:
        Mock API response matching Google People API format
    """
    connections = []
    
    for i in range(count):
        connection = {
            "resourceName": f"people/c{i:05d}",
            "etag": f"etag{i}",
            "names": [{
                "displayName": f"Contact {i}",
                "givenName": f"First{i}",
                "familyName": f"Last{i}",
                "displayNameLastFirst": f"Last{i}, First{i}"
            }],
            "phoneNumbers": [{
                "value": f"+1555{i:07d}",
                "canonicalForm": f"+1555{i:07d}",
                "type": "mobile",
                "formattedType": "Mobile"
            }],
            "emailAddresses": [{
                "value": f"contact{i}@example.com",
                "type": "work",
                "formattedType": "Work"
            }]
        }
        connections.append(connection)
    
    return {
        "connections": connections,
        "totalPeople": count,
        "totalItems": count
    }


def mock_single_person_response(resource_name: str = "people/c123") -> Dict[str, Any]:
    """Generate mock single person response.
    
    Args:
        resource_name: Resource name for the person
        
    Returns:
        Mock person data
    """
    return {
        "resourceName": resource_name,
        "etag": "etag123",
        "names": [{
            "displayName": "John Doe",
            "givenName": "John",
            "familyName": "Doe"
        }],
        "phoneNumbers": [{
            "value": "+15551234567",
            "formattedValue": "(555) 123-4567",
            "type": "mobile"
        }],
        "emailAddresses": [{
            "value": "john.doe@example.com",
            "type": "personal"
        }]
    }


def mock_oauth_token_response() -> Dict[str, Any]:
    """Generate mock OAuth token response."""
    return {
        "access_token": "mock_access_token_12345",
        "refresh_token": "mock_refresh_token_67890",
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "https://www.googleapis.com/auth/contacts.readonly"
    }
```

### 3. Test Contact API Integration

Create `tests/integration/test_api_contacts.py`:

```python
"""Integration tests for contacts API."""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from google_contacts_cisco.main import app
from google_contacts_cisco.models.contact import Contact
from google_contacts_cisco.models.phone_number import PhoneNumber


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def populated_db(db_session):
    """Populate database with test contacts."""
    contacts = []
    
    for i in range(25):
        contact = Contact(
            id=uuid4(),
            resource_name=f"people/c{i:05d}",
            display_name=f"Contact {chr(65 + (i % 26))} {i}",
            given_name=f"First{i}",
            family_name=f"Last{i}"
        )
        
        # Add phone numbers
        contact.phone_numbers.append(
            PhoneNumber(
                id=uuid4(),
                contact_id=contact.id,
                value=f"+1555{i:07d}",
                display_value=f"(555) {i:03d}-0000",
                type="mobile",
                primary=True
            )
        )
        
        contacts.append(contact)
        db_session.add(contact)
    
    db_session.commit()
    return contacts


class TestContactsAPIIntegration:
    """Test contacts API integration."""
    
    def test_list_contacts_with_pagination(self, client, populated_db):
        """Test listing contacts with pagination."""
        # First page
        response = client.get("/api/contacts?limit=10&offset=0")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 25
        assert len(data["contacts"]) == 10
        assert data["has_more"] is True
        assert data["offset"] == 0
        assert data["limit"] == 10
        
        # Second page
        response = client.get("/api/contacts?limit=10&offset=10")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["contacts"]) == 10
        assert data["offset"] == 10
        
        # Last page
        response = client.get("/api/contacts?limit=10&offset=20")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["contacts"]) == 5
        assert data["has_more"] is False
    
    def test_filter_contacts_by_letter(self, client, populated_db):
        """Test filtering contacts by first letter."""
        response = client.get("/api/contacts?group=A")
        
        assert response.status_code == 200
        data = response.json()
        
        # All contacts should start with A
        for contact in data["contacts"]:
            assert contact["display_name"].startswith("Contact A")
    
    def test_sort_contacts_by_name(self, client, populated_db):
        """Test sorting contacts by name."""
        response = client.get("/api/contacts?sort=name&limit=100")
        
        assert response.status_code == 200
        data = response.json()
        
        names = [c["display_name"] for c in data["contacts"]]
        assert names == sorted(names)
    
    def test_get_contact_with_relations(self, client, populated_db):
        """Test getting single contact with phone numbers."""
        contact = populated_db[0]
        
        response = client.get(f"/api/contacts/{contact.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(contact.id)
        assert data["display_name"] == contact.display_name
        assert len(data["phone_numbers"]) > 0
        
        # Verify phone number structure
        phone = data["phone_numbers"][0]
        assert "value" in phone
        assert "display_value" in phone
        assert "type" in phone
        assert "primary" in phone
    
    def test_get_contact_stats(self, client, populated_db):
        """Test getting contact statistics."""
        response = client.get("/api/contacts/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data
        assert "by_letter" in data
        assert data["total"] == 25
        
        # Should have counts for multiple letters
        assert len(data["by_letter"]) > 0


class TestContactsAPIErrors:
    """Test error handling in contacts API."""
    
    def test_get_nonexistent_contact(self, client):
        """Test getting contact that doesn't exist."""
        fake_id = uuid4()
        response = client.get(f"/api/contacts/{fake_id}")
        
        assert response.status_code == 404
    
    def test_invalid_contact_id_format(self, client):
        """Test invalid UUID format."""
        response = client.get("/api/contacts/invalid-uuid")
        
        assert response.status_code == 400
    
    def test_invalid_pagination_params(self, client):
        """Test invalid pagination parameters."""
        # Negative offset
        response = client.get("/api/contacts?offset=-1")
        assert response.status_code == 422
        
        # Limit too large
        response = client.get("/api/contacts?limit=1000")
        assert response.status_code == 422
        
        # Invalid sort value
        response = client.get("/api/contacts?sort=invalid")
        assert response.status_code == 422


class TestContactsAPIConcurrency:
    """Test concurrent operations."""
    
    def test_concurrent_reads(self, client, populated_db):
        """Test multiple concurrent read operations."""
        import concurrent.futures
        
        def get_contacts():
            response = client.get("/api/contacts?limit=10")
            return response.status_code == 200
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(get_contacts) for _ in range(10)]
            results = [f.result() for f in futures]
        
        # All requests should succeed
        assert all(results)
```

### 4. Test Search API Integration

Create `tests/integration/test_api_search.py`:

```python
"""Integration tests for search API."""
import pytest
from fastapi.testclient import TestClient

from google_contacts_cisco.main import app
from tests.fixtures.mock_google_api import mock_people_connections_response


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def searchable_contacts(db_session):
    """Create contacts optimized for search testing."""
    from google_contacts_cisco.models.contact import Contact
    from google_contacts_cisco.models.phone_number import PhoneNumber
    from uuid import uuid4
    
    test_data = [
        ("John Smith", "+15551111111"),
        ("Jane Smith", "+15552222222"),
        ("John Doe", "+15553333333"),
        ("Bob Johnson", "+15554444444"),
    ]
    
    contacts = []
    for name, phone in test_data:
        contact = Contact(
            id=uuid4(),
            resource_name=f"people/{name.replace(' ', '')}",
            display_name=name,
            given_name=name.split()[0],
            family_name=name.split()[1]
        )
        
        contact.phone_numbers.append(
            PhoneNumber(
                id=uuid4(),
                contact_id=contact.id,
                value=phone,
                display_value=phone,
                type="mobile",
                primary=True
            )
        )
        
        contacts.append(contact)
        db_session.add(contact)
    
    db_session.commit()
    return contacts


class TestSearchAPIIntegration:
    """Test search API integration."""
    
    def test_search_by_name_integration(self, client, searchable_contacts):
        """Test full search workflow by name."""
        response = client.get("/api/search?q=John")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] >= 2
        assert data["query"] == "John"
        assert "elapsed_ms" in data
        assert data["elapsed_ms"] < 250  # Performance requirement
        
        # Verify result structure
        results = data["results"]
        assert all("id" in r for r in results)
        assert all("match_type" in r for r in results)
        assert all("match_field" in r for r in results)
    
    def test_search_by_phone_integration(self, client, searchable_contacts):
        """Test search by phone number."""
        response = client.get("/api/search?q=555-111-1111")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] >= 1
        assert data["results"][0]["display_name"] == "John Smith"
        assert data["results"][0]["match_type"] == "phone"
    
    def test_search_result_ranking(self, client, searchable_contacts):
        """Test that results are ranked correctly."""
        response = client.get("/api/search?q=Smith")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should find both Smiths
        assert data["count"] >= 2
        
        # Results should include both contacts with "Smith"
        names = [r["display_name"] for r in data["results"]]
        assert "John Smith" in names
        assert "Jane Smith" in names
    
    def test_search_with_special_characters(self, client, searchable_contacts):
        """Test search handles special characters safely."""
        # SQL injection attempt
        response = client.get("/api/search?q=John' OR '1'='1")
        assert response.status_code == 200
        
        # Should return safely (no SQL injection)
        data = response.json()
        # Results may be 0 or legitimate matches, but should not error
        assert "results" in data


class TestSearchAPIPerformance:
    """Test search API performance."""
    
    def test_search_performance_target(self, client, searchable_contacts):
        """Test search meets performance target."""
        import time
        
        start = time.time()
        response = client.get("/api/search?q=John")
        elapsed = (time.time() - start) * 1000
        
        assert response.status_code == 200
        assert elapsed < 250  # Must complete in under 250ms
        
        # Also check reported time in response
        data = response.json()
        assert data["elapsed_ms"] < 250


class TestSearchAPIErrors:
    """Test search API error handling."""
    
    def test_search_empty_query(self, client):
        """Test search with empty query."""
        response = client.get("/api/search?q=")
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
    
    def test_search_missing_parameter(self, client):
        """Test search without required parameter."""
        response = client.get("/api/search")
        
        assert response.status_code == 400
    
    def test_search_with_multiple_parameters(self, client):
        """Test search rejects multiple search params."""
        response = client.get("/api/search?q=John&name=Smith")
        
        assert response.status_code == 400
```

### 5. Test Sync Workflow Integration

Create `tests/integration/test_sync_workflow.py`:

```python
"""Integration tests for sync workflow."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from google_contacts_cisco.main import app
from tests.fixtures.mock_google_api import (
    mock_people_connections_response,
    mock_oauth_token_response
)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_google_api():
    """Mock Google People API client."""
    with patch('google_contacts_cisco.services.google_api_client.build') as mock_build:
        # Setup mock API client
        mock_service = Mock()
        mock_people = Mock()
        mock_connections = Mock()
        
        # Configure mock responses
        mock_connections.list.return_value.execute.return_value = mock_people_connections_response(10)
        mock_people.connections.return_value = mock_connections
        mock_service.people.return_value = mock_people
        
        mock_build.return_value = mock_service
        
        yield mock_service


class TestSyncWorkflowIntegration:
    """Test complete sync workflow."""
    
    def test_full_sync_workflow(self, client, mock_google_api, db_session):
        """Test complete full sync workflow."""
        # Trigger sync
        response = client.post("/api/sync/trigger?force_full=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Sync started"
        
        # Check sync status
        response = client.get("/api/sync/status")
        
        assert response.status_code == 200
        status = response.json()
        
        # Should be running or completed
        assert status["status"] in ["running", "completed"]
    
    def test_incremental_sync_workflow(self, client, mock_google_api, db_session):
        """Test incremental sync workflow."""
        # First full sync
        response = client.post("/api/sync/trigger?force_full=true")
        assert response.status_code == 200
        
        # Wait a moment (in real test, would poll status)
        import time
        time.sleep(0.5)
        
        # Then incremental
        response = client.post("/api/sync/trigger?force_full=false")
        assert response.status_code == 200
    
    def test_sync_updates_database(self, client, mock_google_api, db_session):
        """Test that sync actually updates database."""
        from google_contacts_cisco.models.contact import Contact
        
        # Count before sync
        before_count = db_session.query(Contact).count()
        
        # Trigger sync
        client.post("/api/sync/trigger?force_full=true")
        
        # Wait for sync to complete
        import time
        time.sleep(1)
        
        # Count after sync
        after_count = db_session.query(Contact).count()
        
        # Should have more contacts
        assert after_count > before_count
    
    def test_concurrent_sync_prevention(self, client, mock_google_api):
        """Test that concurrent syncs are prevented."""
        # Start first sync
        response1 = client.post("/api/sync/trigger")
        assert response1.status_code == 200
        
        # Try to start second sync immediately
        response2 = client.post("/api/sync/trigger")
        
        # Should be rejected
        assert response2.status_code == 409
        assert "already running" in response2.json()["detail"].lower()


class TestSyncErrorHandling:
    """Test sync error handling."""
    
    def test_sync_with_api_error(self, client):
        """Test sync handles Google API errors."""
        with patch('google_contacts_cisco.services.google_api_client.build') as mock_build:
            # Make API raise error
            mock_build.side_effect = Exception("API Error")
            
            response = client.post("/api/sync/trigger")
            
            # Should handle error gracefully
            # May return 200 (started) but status will show error
            # Or may return 500 if error occurs immediately
            assert response.status_code in [200, 500]
    
    def test_sync_rollback_on_error(self, client, db_session):
        """Test database rollback on sync error."""
        from google_contacts_cisco.models.contact import Contact
        
        # Count before
        before_count = db_session.query(Contact).count()
        
        with patch('google_contacts_cisco.services.sync_service.SyncService.full_sync') as mock_sync:
            # Make sync fail midway
            mock_sync.side_effect = Exception("Sync error")
            
            try:
                client.post("/api/sync/trigger?force_full=true")
            except:
                pass
            
            # Database should be rolled back
            after_count = db_session.query(Contact).count()
            assert after_count == before_count
```

### 6. Test OAuth Flow Integration

Create `tests/integration/test_oauth_flow.py`:

```python
"""Integration tests for OAuth flow."""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from google_contacts_cisco.main import app
from tests.fixtures.mock_google_api import mock_oauth_token_response


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestOAuthFlowIntegration:
    """Test OAuth authentication flow."""
    
    def test_oauth_initiation(self, client):
        """Test OAuth flow initiation."""
        response = client.get("/auth/google", follow_redirects=False)
        
        # Should redirect to Google
        assert response.status_code in [302, 307]
        assert "location" in response.headers
    
    def test_oauth_callback_success(self, client):
        """Test successful OAuth callback."""
        with patch('google_contacts_cisco.services.oauth_service.OAuthService.handle_callback'):
            response = client.get(
                "/auth/callback?code=mock_auth_code&state=mock_state"
            )
            
            assert response.status_code == 200
            # Should show success page
            assert b"success" in response.content.lower()
    
    def test_oauth_callback_error(self, client):
        """Test OAuth callback with error."""
        response = client.get("/auth/callback?error=access_denied")
        
        assert response.status_code == 200
        # Should show error page
        assert b"error" in response.content.lower()
    
    def test_oauth_status_check(self, client):
        """Test checking OAuth status."""
        response = client.get("/auth/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "authenticated" in data
        assert isinstance(data["authenticated"], bool)
    
    def test_token_refresh_flow(self, client):
        """Test token refresh."""
        with patch('google_contacts_cisco.services.oauth_service.OAuthService.refresh_token'):
            response = client.post("/auth/refresh")
            
            # May succeed or fail depending on auth state
            assert response.status_code in [200, 401, 500]


class TestOAuthSecurity:
    """Test OAuth security features."""
    
    def test_csrf_state_validation(self, client):
        """Test CSRF state parameter validation."""
        # Callback without state should fail
        response = client.get("/auth/callback?code=mock_code")
        
        # Should handle missing state
        assert response.status_code in [200, 400]
    
    def test_oauth_without_code(self, client):
        """Test callback without authorization code."""
        response = client.get("/auth/callback")
        
        assert response.status_code == 200
        # Should show error
        assert b"error" in response.content.lower() or b"no" in response.content.lower()
```

## Verification

After completing this task:

1. **Run Integration Tests**:
   ```bash
   uv run pytest tests/integration -v
   ```

2. **Run With Coverage**:
   ```bash
   uv run pytest tests/integration --cov=google_contacts_cisco --cov-report=term
   ```

3. **Run Specific Test File**:
   ```bash
   uv run pytest tests/integration/test_api_contacts.py -v
   ```

4. **Run Only Integration Tests**:
   ```bash
   uv run pytest -m integration -v
   ```

5. **Check Test Duration**:
   ```bash
   uv run pytest tests/integration --durations=10
   # Shows slowest 10 tests
   ```

## Notes

- **Test Database**: Use in-memory SQLite for speed
- **Mocking**: Mock external APIs (Google), not internal code
- **Transactions**: Each test runs in a transaction, rolled back after
- **Fixtures**: Share fixtures via conftest.py
- **Performance**: Integration tests should complete in <2 minutes total
- **Isolation**: Tests should not depend on each other
- **Real HTTP**: Use TestClient for actual HTTP requests

## Common Issues

1. **Slow Tests**: Check database queries, add indexes
2. **Flaky Tests**: Avoid time-dependent assertions
3. **Mock Leaks**: Ensure mocks are cleaned up between tests
4. **Database Locks**: Use separate connection pools
5. **Port Conflicts**: Use random ports for test servers

## Best Practices

- Test happy path and error cases
- Use realistic mock data
- Test API contracts (request/response schemas)
- Verify database state after operations
- Test concurrent operations
- Clean up resources after tests
- Use descriptive test names
- Group related tests in classes

## Related Documentation

- FastAPI Testing: https://fastapi.tiangolo.com/tutorial/testing/
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/
- TestClient: https://www.starlette.io/testclient/

## Estimated Time

6-8 hours
