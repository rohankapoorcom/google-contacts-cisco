# Task 3.1: Full Sync Implementation

## Overview

Implement the initial full synchronization of contacts from Google to the local database. This includes downloading all contacts, parsing them, and storing them in the database with proper error handling.

## Priority

**P0 (Critical)** - Required for MVP

## Dependencies

- Task 2.2: Google API Client
- Task 2.3: Contact Data Models
- Task 1.2: Database Setup

## Objectives

1. Implement full contact download from Google
2. Handle pagination for large contact lists
3. Parse and transform contact data
4. Store contacts in database
5. Store sync token for future incremental syncs
6. Handle errors gracefully
7. Track sync progress and status
8. Test with real Google account

## Technical Context

### Full Sync Process
1. Request all contacts from Google People API
2. Iterate through pages (pagination)
3. Transform each contact from Google format to internal format
4. Insert/update contacts in database
5. Store sync token from last page
6. Mark sync as complete

### Performance Considerations
- Batch database operations (commit every N contacts)
- Sequential API requests (per Google recommendation)
- Small delays between requests
- Progress tracking for large contact lists

## Acceptance Criteria

- [ ] Full sync downloads all contacts successfully
- [ ] Pagination handles multiple pages correctly
- [ ] Contacts are transformed and stored properly
- [ ] Phone numbers are normalized and stored
- [ ] Sync token is stored for future incremental syncs
- [ ] Progress is tracked and can be queried
- [ ] Errors during sync are logged and recoverable
- [ ] Duplicate contacts are handled (upsert logic)
- [ ] Sync can be interrupted and resumed
- [ ] Tests verify sync logic with mock data

## Implementation Steps

### 1. Create Contact Repository

Create `google_contacts_cisco/repositories/contact_repository.py`:

```python
"""Contact repository for database operations."""
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..models.contact import Contact
from ..models.phone_number import PhoneNumber
from ..schemas.contact import ContactCreateSchema, PhoneNumberSchema


class ContactRepository:
    """Repository for contact database operations."""
    
    def __init__(self, db: Session):
        """Initialize repository.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def create_contact(self, contact_data: ContactCreateSchema) -> Contact:
        """Create a new contact.
        
        Args:
            contact_data: Contact data to create
            
        Returns:
            Created contact
        """
        # Create contact
        contact = Contact(
            resource_name=contact_data.resource_name,
            etag=contact_data.etag,
            given_name=contact_data.given_name,
            family_name=contact_data.family_name,
            display_name=contact_data.display_name,
            organization=contact_data.organization,
            job_title=contact_data.job_title,
            deleted=contact_data.deleted,
            synced_at=datetime.utcnow()
        )
        
        self.db.add(contact)
        self.db.flush()  # Get contact ID
        
        # Add phone numbers
        for phone_data in contact_data.phone_numbers:
            phone = PhoneNumber(
                contact_id=contact.id,
                value=phone_data.value,
                display_value=phone_data.display_value,
                type=phone_data.type,
                primary=phone_data.primary
            )
            self.db.add(phone)
        
        return contact
    
    def get_by_resource_name(self, resource_name: str) -> Optional[Contact]:
        """Get contact by Google resource name.
        
        Args:
            resource_name: Google resource name
            
        Returns:
            Contact or None if not found
        """
        return self.db.query(Contact).filter(
            Contact.resource_name == resource_name
        ).first()
    
    def upsert_contact(self, contact_data: ContactCreateSchema) -> Contact:
        """Insert or update contact.
        
        Args:
            contact_data: Contact data
            
        Returns:
            Created or updated contact
        """
        existing = self.get_by_resource_name(contact_data.resource_name)
        
        if existing:
            # Update existing contact
            existing.etag = contact_data.etag
            existing.given_name = contact_data.given_name
            existing.family_name = contact_data.family_name
            existing.display_name = contact_data.display_name
            existing.organization = contact_data.organization
            existing.job_title = contact_data.job_title
            existing.deleted = contact_data.deleted
            existing.synced_at = datetime.utcnow()
            existing.updated_at = datetime.utcnow()
            
            # Delete old phone numbers
            self.db.query(PhoneNumber).filter(
                PhoneNumber.contact_id == existing.id
            ).delete()
            
            # Add new phone numbers
            for phone_data in contact_data.phone_numbers:
                phone = PhoneNumber(
                    contact_id=existing.id,
                    value=phone_data.value,
                    display_value=phone_data.display_value,
                    type=phone_data.type,
                    primary=phone_data.primary
                )
                self.db.add(phone)
            
            return existing
        else:
            # Create new contact
            return self.create_contact(contact_data)
    
    def get_all_active(self) -> List[Contact]:
        """Get all non-deleted contacts.
        
        Returns:
            List of active contacts
        """
        return self.db.query(Contact).filter(
            Contact.deleted == False
        ).all()
    
    def count_all(self) -> int:
        """Count all contacts.
        
        Returns:
            Total contact count
        """
        return self.db.query(Contact).count()
    
    def count_active(self) -> int:
        """Count active (non-deleted) contacts.
        
        Returns:
            Active contact count
        """
        return self.db.query(Contact).filter(
            Contact.deleted == False
        ).count()
```

### 2. Create Sync State Repository

Create `google_contacts_cisco/repositories/sync_repository.py`:

```python
"""Sync state repository."""
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session

from ..models.sync_state import SyncState


class SyncRepository:
    """Repository for sync state operations."""
    
    def __init__(self, db: Session):
        """Initialize repository.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def get_latest_sync_state(self) -> Optional[SyncState]:
        """Get the most recent sync state.
        
        Returns:
            Latest sync state or None
        """
        return self.db.query(SyncState).order_by(
            SyncState.last_sync_at.desc()
        ).first()
    
    def create_sync_state(
        self,
        sync_token: Optional[str] = None,
        status: str = "idle",
        error_message: Optional[str] = None
    ) -> SyncState:
        """Create new sync state.
        
        Args:
            sync_token: Sync token from Google
            status: Sync status
            error_message: Error message if any
            
        Returns:
            Created sync state
        """
        sync_state = SyncState(
            sync_token=sync_token,
            last_sync_at=datetime.utcnow(),
            sync_status=status,
            error_message=error_message
        )
        self.db.add(sync_state)
        return sync_state
    
    def update_sync_state(
        self,
        sync_state: SyncState,
        sync_token: Optional[str] = None,
        status: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Update existing sync state.
        
        Args:
            sync_state: Sync state to update
            sync_token: New sync token
            status: New status
            error_message: New error message
        """
        if sync_token is not None:
            sync_state.sync_token = sync_token
        if status is not None:
            sync_state.sync_status = status
        if error_message is not None:
            sync_state.error_message = error_message
        sync_state.last_sync_at = datetime.utcnow()
```

### 3. Implement Full Sync Service

Create `google_contacts_cisco/services/sync_service.py`:

```python
"""Sync service for Google Contacts."""
from typing import Optional
import time

from sqlalchemy.orm import Session

from ..services.google_client import get_google_client
from ..services.contact_transformer import transform_google_persons_batch
from ..repositories.contact_repository import ContactRepository
from ..repositories.sync_repository import SyncRepository
from ..api.schemas import GoogleConnectionsResponse, GooglePerson
from ..models import get_db
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SyncService:
    """Service for syncing Google Contacts."""
    
    def __init__(self, db: Session):
        """Initialize sync service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.contact_repo = ContactRepository(db)
        self.sync_repo = SyncRepository(db)
        self.google_client = get_google_client()
    
    def full_sync(self, batch_size: int = 100) -> dict:
        """Perform full sync of all contacts.
        
        Args:
            batch_size: Number of contacts to commit per batch
            
        Returns:
            Sync statistics
        """
        logger.info("Starting full sync")
        
        # Create sync state
        sync_state = self.sync_repo.create_sync_state(status="syncing")
        self.db.commit()
        
        stats = {
            "total_fetched": 0,
            "created": 0,
            "updated": 0,
            "errors": 0,
            "pages": 0
        }
        
        try:
            # Fetch all contacts from Google
            for response_data in self.google_client.list_connections(page_size=100):
                stats["pages"] += 1
                
                # Parse response
                response = GoogleConnectionsResponse(**response_data)
                
                if not response.connections:
                    logger.info(f"Page {stats['pages']}: No contacts")
                    continue
                
                logger.info(f"Page {stats['pages']}: Processing {len(response.connections)} contacts")
                
                # Transform contacts
                contacts_data = transform_google_persons_batch(response.connections)
                
                # Upsert contacts in batch
                for contact_data in contacts_data:
                    try:
                        existing = self.contact_repo.get_by_resource_name(contact_data.resource_name)
                        contact = self.contact_repo.upsert_contact(contact_data)
                        
                        if existing:
                            stats["updated"] += 1
                        else:
                            stats["created"] += 1
                        
                        stats["total_fetched"] += 1
                        
                        # Commit in batches
                        if stats["total_fetched"] % batch_size == 0:
                            self.db.commit()
                            logger.info(f"Committed batch: {stats['total_fetched']} contacts processed")
                    
                    except Exception as e:
                        logger.error(f"Error processing contact {contact_data.resource_name}: {e}")
                        stats["errors"] += 1
                        continue
                
                # Commit remaining contacts in page
                self.db.commit()
                
                # Store sync token if this is the last page
                if not response.next_page_token and response.next_sync_token:
                    self.sync_repo.update_sync_state(
                        sync_state,
                        sync_token=response.next_sync_token
                    )
                    self.db.commit()
                    logger.info(f"Stored sync token: {response.next_sync_token[:20]}...")
                
                # Small delay between pages
                time.sleep(0.1)
            
            # Mark sync as complete
            self.sync_repo.update_sync_state(sync_state, status="idle")
            self.db.commit()
            
            logger.info(f"Full sync completed: {stats}")
            return stats
        
        except Exception as e:
            logger.error(f"Full sync failed: {e}")
            self.sync_repo.update_sync_state(
                sync_state,
                status="error",
                error_message=str(e)
            )
            self.db.commit()
            raise
    
    def get_sync_status(self) -> dict:
        """Get current sync status.
        
        Returns:
            Sync status information
        """
        sync_state = self.sync_repo.get_latest_sync_state()
        contact_count = self.contact_repo.count_active()
        total_count = self.contact_repo.count_all()
        
        if sync_state:
            return {
                "status": sync_state.sync_status,
                "last_sync_at": sync_state.last_sync_at.isoformat() if sync_state.last_sync_at else None,
                "has_sync_token": sync_state.sync_token is not None,
                "error_message": sync_state.error_message,
                "contact_count": contact_count,
                "total_contacts": total_count
            }
        else:
            return {
                "status": "never_synced",
                "last_sync_at": None,
                "has_sync_token": False,
                "error_message": None,
                "contact_count": contact_count,
                "total_contacts": total_count
            }


def get_sync_service(db: Session) -> SyncService:
    """Get sync service instance.
    
    Args:
        db: Database session
        
    Returns:
        SyncService instance
    """
    return SyncService(db)
```

### 4. Add Sync API Endpoints

Update `google_contacts_cisco/api/routes.py`:

```python
# Add these endpoints

from ..models import get_db
from ..services.sync_service import get_sync_service

@router.post("/api/sync/full")
async def trigger_full_sync(db: Session = Depends(get_db)):
    """Trigger full sync of Google Contacts."""
    from ..auth.oauth import is_authenticated
    
    if not is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        sync_service = get_sync_service(db)
        stats = sync_service.full_sync()
        return {
            "status": "success",
            "message": "Full sync completed",
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/api/sync/status")
async def get_sync_status(db: Session = Depends(get_db)):
    """Get current sync status."""
    sync_service = get_sync_service(db)
    return sync_service.get_sync_status()
```

### 5. Create Tests

Create `tests/test_full_sync.py`:

```python
"""Test full sync implementation."""
import pytest
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from google_contacts_cisco.models import Base
from google_contacts_cisco.services.sync_service import SyncService
from google_contacts_cisco.api.schemas import GooglePerson, GoogleName


@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def mock_google_client():
    """Create mock Google client."""
    client = Mock()
    return client


def test_full_sync_single_page(db_session, mock_google_client):
    """Test full sync with single page of contacts."""
    # Mock API response
    mock_response = {
        'connections': [
            {
                'resourceName': 'people/c1',
                'names': [{'displayName': 'John Doe'}],
                'phoneNumbers': [{'value': '5551234567'}]
            },
            {
                'resourceName': 'people/c2',
                'names': [{'displayName': 'Jane Smith'}],
                'phoneNumbers': [{'value': '5559876543'}]
            }
        ],
        'nextSyncToken': 'sync_token_123'
    }
    
    mock_google_client.list_connections.return_value = [mock_response]
    
    with patch('google_contacts_cisco.services.sync_service.get_google_client', return_value=mock_google_client):
        sync_service = SyncService(db_session)
        stats = sync_service.full_sync()
    
    assert stats['total_fetched'] == 2
    assert stats['created'] == 2
    assert stats['updated'] == 0
    assert stats['errors'] == 0


def test_full_sync_updates_existing(db_session, mock_google_client):
    """Test that sync updates existing contacts."""
    # First sync
    mock_response1 = {
        'connections': [{
            'resourceName': 'people/c1',
            'names': [{'displayName': 'John Doe'}],
            'phoneNumbers': [{'value': '5551234567'}]
        }],
        'nextSyncToken': 'sync1'
    }
    
    mock_google_client.list_connections.return_value = [mock_response1]
    
    with patch('google_contacts_cisco.services.sync_service.get_google_client', return_value=mock_google_client):
        sync_service = SyncService(db_session)
        stats1 = sync_service.full_sync()
    
    assert stats1['created'] == 1
    
    # Second sync with updated contact
    mock_response2 = {
        'connections': [{
            'resourceName': 'people/c1',
            'names': [{'displayName': 'John Updated'}],
            'phoneNumbers': [{'value': '5551234567'}]
        }],
        'nextSyncToken': 'sync2'
    }
    
    mock_google_client.list_connections.return_value = [mock_response2]
    
    with patch('google_contacts_cisco.services.sync_service.get_google_client', return_value=mock_google_client):
        sync_service = SyncService(db_session)
        stats2 = sync_service.full_sync()
    
    assert stats2['updated'] == 1
    assert stats2['created'] == 0
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
- Test full sync downloads all contacts
- Test pagination handles multiple pages
- Test contacts are stored in database
- Test sync token is saved
- Test error recovery during sync


## Verification

After completing this task:

1. **Trigger Full Sync**:
   ```bash
   # Via API
   curl -X POST http://localhost:8000/api/sync/full
   
   # Should return success with statistics
   ```

2. **Check Sync Status**:
   ```bash
   curl http://localhost:8000/api/sync/status
   
   # Should show contact count and last sync time
   ```

3. **Verify Database**:
   ```bash
   sqlite3 data/contacts.db
   SELECT COUNT(*) FROM contacts;
   SELECT COUNT(*) FROM phone_numbers;
   SELECT * FROM sync_states ORDER BY last_sync_at DESC LIMIT 1;
   ```

4. **Run Tests**:
   ```bash
   pytest tests/test_full_sync.py -v
   ```

## Notes

- **Batch Commits**: Commits every 100 contacts to avoid memory issues
- **Sequential Requests**: Small delays between API requests
- **Upsert Logic**: Updates existing contacts, inserts new ones
- **Sync Token**: Stored for future incremental syncs
- **Error Handling**: Individual contact errors don't stop entire sync
- **Progress Tracking**: Logs progress every batch

## Common Issues

1. **Memory Issues**: Reduce batch size if syncing many contacts
2. **Rate Limits**: Increase delay between requests if hitting limits
3. **Duplicate Phone Numbers**: Handled by deleting old, inserting new
4. **Large Contacts**: Some contacts have many phone numbers/emails

## Related Documentation

- Google People API Sync: https://developers.google.com/people/v1/contacts#sync
- SQLAlchemy Bulk Operations: https://docs.sqlalchemy.org/en/20/orm/session_api.html

## Estimated Time

4-6 hours

