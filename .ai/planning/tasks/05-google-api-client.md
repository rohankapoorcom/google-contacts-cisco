# Task 2.2: Google API Client

## Task Status

**Status**: ✅ Completed  
**Completed Date**: January 6, 2026  
**Actual Time**: ~4 hours  
**Implemented By**: AI Assistant  
**Notes**: Implementation completed as specified with 98% test coverage. Added custom exceptions for better error handling. All 71 tests for this task pass.

## Overview

Create a wrapper around the Google People API client to handle contact retrieval, pagination, error handling, and rate limiting. This client will be used by the sync service to fetch contacts from Google.

## Priority

**P0 (Critical)** - Required for MVP

## Dependencies

- Task 2.1: OAuth 2.0 Implementation
- Task 1.2: Database Setup (for testing)

## Objectives

1. Create Google People API client wrapper
2. Implement contact list retrieval with pagination
3. Implement error handling with retries and exponential backoff
4. Implement rate limit handling
5. Follow Google API best practices (sequential requests)
6. Create connection testing functionality

## Technical Context

### Google People API v1
- **Base URL**: `https://people.googleapis.com/v1`
- **Endpoint**: `/people/me/connections`
- **Person Fields**: names, emailAddresses, phoneNumbers, organizations, metadata
- **Page Size**: Up to 1000 contacts per page (recommended: 100-500)
- **Pagination**: Use `pageToken` from response
- **Sync Token**: For incremental updates

### Rate Limits and Quotas
- **Critical Read Requests**: 300 per minute per user
- **Best Practice**: Send requests sequentially, not in parallel
- **Backoff**: Use exponential backoff on 429 (rate limit) errors

### Error Handling
- **401 Unauthorized**: Token expired, needs refresh
- **403 Forbidden**: Insufficient permissions
- **429 Too Many Requests**: Rate limit, retry with backoff
- **500+ Server Errors**: Retry with exponential backoff

## Acceptance Criteria

- [x] Client successfully connects to Google People API
- [x] Client retrieves person fields correctly
- [x] Pagination handles multiple pages of contacts
- [x] Pagination stops when no more pages exist
- [x] Rate limit errors (429) trigger exponential backoff
- [x] Server errors (500+) trigger retries
- [x] Auth errors (401) are handled properly
- [x] Client respects Google's sequential request recommendation
- [x] Connection can be tested without syncing data
- [x] All API errors are logged with context

## Implementation Steps

### 1. Create Google API Client Service

Create `google_contacts_cisco/services/google_client.py`:

```python
"""Google People API client."""
import time
from typing import Iterator, Optional, List, Dict, Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

from ..auth.oauth import get_credentials
from ..utils.logger import get_logger

logger = get_logger(__name__)


# Person fields to retrieve from Google Contacts
PERSON_FIELDS = [
    "names",
    "emailAddresses",
    "phoneNumbers",
    "organizations",
    "metadata",
]


class GoogleContactsClient:
    """Client for Google People API."""
    
    def __init__(self, credentials: Optional[Credentials] = None):
        """Initialize Google Contacts client.
        
        Args:
            credentials: OAuth credentials (if None, loads from storage)
        """
        self.credentials = credentials or get_credentials()
        if not self.credentials:
            raise ValueError("No valid credentials available. Please authenticate first.")
        
        self.service = build('people', 'v1', credentials=self.credentials)
        self.max_retries = 5
        self.initial_backoff = 1.0  # seconds
    
    def list_connections(
        self,
        page_size: int = 100,
        sync_token: Optional[str] = None,
    ) -> Iterator[Dict[str, Any]]:
        """List all connections with pagination.
        
        Args:
            page_size: Number of contacts per page (max 1000)
            sync_token: Token for incremental sync (if available)
            
        Yields:
            Dictionary containing 'connections' list and 'syncToken'
            
        Raises:
            HttpError: If API request fails after retries
        """
        page_token = None
        request_count = 0
        
        while True:
            try:
                # Build request
                request_params = {
                    'resourceName': 'people/me',
                    'pageSize': page_size,
                    'personFields': ','.join(PERSON_FIELDS),
                }
                
                if sync_token:
                    request_params['syncToken'] = sync_token
                    request_params['requestSyncToken'] = True
                else:
                    request_params['requestSyncToken'] = True
                
                if page_token:
                    request_params['pageToken'] = page_token
                
                # Make request with retry logic
                response = self._make_request_with_retry(
                    lambda: self.service.people().connections().list(**request_params).execute()
                )
                
                request_count += 1
                logger.info(f"Retrieved page {request_count} ({len(response.get('connections', []))} contacts)")
                
                yield response
                
                # Check if there are more pages
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
                
                # Small delay between requests (sequential, as recommended by Google)
                time.sleep(0.1)
                
            except HttpError as e:
                if e.resp.status == 410:
                    # Sync token expired
                    logger.warning("Sync token expired, need to do full sync")
                    raise
                else:
                    logger.error(f"Error listing connections: {e}")
                    raise
    
    def get_person(self, resource_name: str) -> Dict[str, Any]:
        """Get a single person by resource name.
        
        Args:
            resource_name: Person's resource name (e.g., 'people/12345')
            
        Returns:
            Person data dictionary
            
        Raises:
            HttpError: If API request fails
        """
        try:
            person = self._make_request_with_retry(
                lambda: self.service.people().get(
                    resourceName=resource_name,
                    personFields=','.join(PERSON_FIELDS)
                ).execute()
            )
            return person
        except HttpError as e:
            logger.error(f"Error getting person {resource_name}: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test connection to Google People API.
        
        Returns:
            True if connection successful
            
        Raises:
            Exception: If connection fails
        """
        try:
            # Try to get just one contact
            result = self.service.people().connections().list(
                resourceName='people/me',
                pageSize=1,
                personFields='names'
            ).execute()
            
            logger.info("Successfully connected to Google People API")
            return True
        except HttpError as e:
            logger.error(f"Connection test failed: {e}")
            raise
    
    def _make_request_with_retry(self, request_func, retry_count: int = 0):
        """Make API request with retry logic.
        
        Args:
            request_func: Function that makes the API request
            retry_count: Current retry attempt
            
        Returns:
            API response
            
        Raises:
            HttpError: If request fails after all retries
        """
        try:
            return request_func()
        except HttpError as e:
            if e.resp.status == 429:  # Rate limit
                if retry_count < self.max_retries:
                    backoff = self.initial_backoff * (2 ** retry_count)
                    logger.warning(f"Rate limit hit, backing off for {backoff} seconds")
                    time.sleep(backoff)
                    return self._make_request_with_retry(request_func, retry_count + 1)
                else:
                    logger.error("Max retries exceeded for rate limit")
                    raise
            elif e.resp.status >= 500:  # Server error
                if retry_count < self.max_retries:
                    backoff = self.initial_backoff * (2 ** retry_count)
                    logger.warning(f"Server error {e.resp.status}, retrying in {backoff} seconds")
                    time.sleep(backoff)
                    return self._make_request_with_retry(request_func, retry_count + 1)
                else:
                    logger.error("Max retries exceeded for server error")
                    raise
            elif e.resp.status == 401:  # Unauthorized
                logger.error("Unauthorized - credentials may have expired")
                raise
            else:
                # Other errors, don't retry
                raise


def get_google_client(credentials: Optional[Credentials] = None) -> GoogleContactsClient:
    """Get Google Contacts client instance.
    
    Args:
        credentials: OAuth credentials (if None, loads from storage)
        
    Returns:
        GoogleContactsClient instance
    """
    return GoogleContactsClient(credentials)
```

### 2. Create Logger Utility

Create `google_contacts_cisco/utils/logger.py`:

```python
"""Logging utilities."""
import logging
import sys
from typing import Optional

from ..config import settings


def get_logger(name: str) -> logging.Logger:
    """Get logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(getattr(logging, settings.log_level.upper()))
        
        # Console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, settings.log_level.upper()))
        
        # Format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
    
    return logger
```

### 3. Add API Test Endpoint

Update `google_contacts_cisco/api/routes.py`:

```python
# Add this endpoint

@router.get("/api/test-connection")
async def test_google_connection():
    """Test connection to Google People API."""
    from ..services.google_client import get_google_client
    from ..auth.oauth import is_authenticated
    
    if not is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated. Please connect Google account first.")
    
    try:
        client = get_google_client()
        client.test_connection()
        return {"status": "success", "message": "Successfully connected to Google People API"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")
```

### 4. Create Tests

Create `tests/test_google_client.py`:

```python
"""Test Google API client."""
from unittest.mock import Mock, MagicMock, patch
import pytest
from googleapiclient.errors import HttpError

from google_contacts_cisco.services.google_client import GoogleContactsClient


@pytest.fixture
def mock_credentials():
    """Create mock credentials."""
    creds = Mock()
    creds.valid = True
    creds.expired = False
    return creds


@pytest.fixture
def mock_service():
    """Create mock Google API service."""
    service = MagicMock()
    return service


def test_client_initialization(mock_credentials):
    """Test client initialization."""
    with patch('google_contacts_cisco.services.google_client.build') as mock_build:
        client = GoogleContactsClient(mock_credentials)
        assert client.credentials == mock_credentials
        mock_build.assert_called_once()


def test_list_connections_single_page(mock_credentials, mock_service):
    """Test listing connections with single page."""
    # Mock response
    mock_response = {
        'connections': [
            {'resourceName': 'people/1', 'names': [{'displayName': 'John Doe'}]},
            {'resourceName': 'people/2', 'names': [{'displayName': 'Jane Doe'}]},
        ],
        'nextSyncToken': 'sync123'
    }
    
    mock_service.people().connections().list().execute.return_value = mock_response
    
    with patch('google_contacts_cisco.services.google_client.build', return_value=mock_service):
        client = GoogleContactsClient(mock_credentials)
        
        results = list(client.list_connections(page_size=100))
        
        assert len(results) == 1
        assert len(results[0]['connections']) == 2
        assert results[0]['nextSyncToken'] == 'sync123'


def test_list_connections_multiple_pages(mock_credentials, mock_service):
    """Test listing connections with multiple pages."""
    # Mock responses
    page1 = {
        'connections': [{'resourceName': 'people/1'}],
        'nextPageToken': 'page2',
        'nextSyncToken': 'sync123'
    }
    page2 = {
        'connections': [{'resourceName': 'people/2'}],
        'nextSyncToken': 'sync123'
    }
    
    mock_service.people().connections().list().execute.side_effect = [page1, page2]
    
    with patch('google_contacts_cisco.services.google_client.build', return_value=mock_service):
        with patch('time.sleep'):  # Skip sleep in tests
            client = GoogleContactsClient(mock_credentials)
            
            results = list(client.list_connections(page_size=1))
            
            assert len(results) == 2


def test_retry_on_rate_limit(mock_credentials, mock_service):
    """Test retry logic on rate limit error."""
    # First call fails with 429, second succeeds
    error_response = Mock()
    error_response.status = 429
    
    mock_service.people().connections().list().execute.side_effect = [
        HttpError(error_response, b'Rate limit'),
        {'connections': [], 'nextSyncToken': 'sync123'}
    ]
    
    with patch('google_contacts_cisco.services.google_client.build', return_value=mock_service):
        with patch('time.sleep'):  # Skip sleep in tests
            client = GoogleContactsClient(mock_credentials)
            
            results = list(client.list_connections())
            
            # Should succeed after retry
            assert len(results) == 1


def test_sync_token_expired(mock_credentials, mock_service):
    """Test handling of expired sync token (410 error)."""
    error_response = Mock()
    error_response.status = 410
    
    mock_service.people().connections().list().execute.side_effect = HttpError(error_response, b'Sync token expired')
    
    with patch('google_contacts_cisco.services.google_client.build', return_value=mock_service):
        client = GoogleContactsClient(mock_credentials)
        
        with pytest.raises(HttpError) as exc_info:
            list(client.list_connections(sync_token='expired_token'))
        
        assert exc_info.value.resp.status == 410


def test_test_connection_success(mock_credentials, mock_service):
    """Test successful connection test."""
    mock_service.people().connections().list().execute.return_value = {
        'connections': [{'resourceName': 'people/1'}]
    }
    
    with patch('google_contacts_cisco.services.google_client.build', return_value=mock_service):
        client = GoogleContactsClient(mock_credentials)
        
        result = client.test_connection()
        
        assert result is True
```


## Testing Requirements

**⚠️ Critical**: This task is not complete until comprehensive unit tests are written and passing.

### Test Coverage Requirements
- All functions and methods must have tests
- Both success and failure paths must be covered
- Edge cases and boundary conditions must be tested
- **Minimum coverage: 80% for this module**
- **Target coverage: 85%+ for services, 90%+ for utilities**

### Test Files to Create
Create test file(s) in `tests/unit/` matching your implementation structure:

```
Implementation File              →  Test File
─────────────────────────────────────────────────────────────
[implementation path]            →  tests/unit/[same structure]/test_[filename].py
```

### Test Structure Template
```python
"""Test [module name].

This module tests the [feature] implementation from this task.
"""
import pytest
from google_contacts_cisco.[module] import [Component]


class Test[FeatureName]:
    """Test [feature] functionality."""
    
    def test_typical_use_case(self):
        """Test the main success path."""
        # Arrange
        input_data = ...
        
        # Act
        result = component.method(input_data)
        
        # Assert
        assert result == expected
    
    def test_handles_invalid_input(self):
        """Test error handling for invalid input."""
        with pytest.raises(ValueError):
            component.method(invalid_input)
    
    def test_edge_case_empty_data(self):
        """Test behavior with empty/null data."""
        result = component.method([])
        assert result == []
    
    def test_edge_case_boundary_values(self):
        """Test boundary conditions."""
        ...
```

### What to Test
- ✅ **Success paths**: Typical use cases and expected inputs
- ✅ **Error paths**: Invalid inputs, exceptions, error conditions
- ✅ **Edge cases**: Empty data, null values, boundary conditions, large datasets
- ✅ **Side effects**: Database changes, file operations, API calls
- ✅ **Return values**: Correct types, formats, and values
- ✅ **State changes**: Object state, system state

### Testing Best Practices
- Use descriptive test names that explain what is being tested
- Follow Arrange-Act-Assert pattern
- Use fixtures from `tests/conftest.py` for common test data
- Mock external dependencies (APIs, databases, file system)
- Keep tests independent (no shared state)
- Make tests fast (< 5 seconds per test file)
- Test behavior, not implementation details

### Running Your Tests
```bash
# Run tests for this specific module
uv run pytest tests/unit/[your_test_file].py -v

# Run with coverage report
uv run pytest tests/unit/[your_test_file].py \
    --cov=google_contacts_cisco.[your_module] \
    --cov-report=term-missing

# Run in watch mode (re-run on file changes)
uv run pytest-watch tests/unit/[your_directory]/ -v
```

### Acceptance Criteria Additions
- [ ] All new code has corresponding tests
- [ ] Tests cover success cases, error cases, and edge cases
- [ ] All tests pass (`pytest tests/unit/[module]/ -v`)
- [ ] Coverage is >80% for this module
- [ ] Tests are independent and can run in any order
- [ ] External dependencies are properly mocked
- [ ] Test names clearly describe what is being tested

### Example Test Scenarios for This Task
- Test contact list retrieval with pagination
- Test single contact fetch by resource name
- Test error handling for API errors
- Test retry logic for transient failures
- Test authentication token usage


## Verification

After completing this task:

1. **Test Connection**:
   ```bash
   # Start app
   uvicorn google_contacts_cisco.main:app --reload
   
   # Authenticate first
   curl http://localhost:8000/auth/google
   
   # Test connection
   curl http://localhost:8000/api/test-connection
   # Should return success
   ```

2. **Run Tests**:
   ```bash
   pytest tests/test_google_client.py -v
   ```

3. **Manual API Test** (with Python):
   ```python
   from google_contacts_cisco.services.google_client import get_google_client
   
   client = get_google_client()
   
   # Test connection
   client.test_connection()
   
   # Get first page of contacts
   for response in client.list_connections(page_size=10):
       print(f"Got {len(response['connections'])} contacts")
       break
   ```

## Notes

- **Sequential Requests**: Google recommends sequential (not parallel) requests to avoid rate limits
- **Pagination**: Use `nextPageToken` to get subsequent pages
- **Sync Token**: Store and use for incremental updates (Task 3.2)
- **Person Fields**: Only request fields you need to reduce response size
- **Rate Limits**: Implement exponential backoff for 429 errors
- **Error Logging**: Log all errors with context for debugging

## Common Issues

1. **401 Unauthorized**: Credentials expired, need to re-authenticate
2. **429 Rate Limit**: Sending requests too fast, increase delays
3. **410 Sync Token Expired**: Need to do full sync, can't use incremental
4. **500 Server Errors**: Google's temporary issue, retry with backoff

## Related Documentation

- Google People API: https://developers.google.com/people
- People API Reference: https://developers.google.com/people/api/rest/v1/people.connections/list
- API Quotas: https://developers.google.com/people/v1/how-tos/quota
- Error Handling: https://developers.google.com/people/v1/how-tos/errors

## Estimated Time

4-5 hours

