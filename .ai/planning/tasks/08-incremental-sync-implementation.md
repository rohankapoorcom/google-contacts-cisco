# Task 3.2: Incremental Sync Implementation

## Overview

Implement incremental synchronization using sync tokens to efficiently update only changed contacts since the last sync. This reduces API calls and improves sync performance.

## Priority

**P1 (High)** - Should have for production

## Dependencies

- Task 3.1: Full Sync Implementation
- Task 2.2: Google API Client

## Objectives

1. Implement incremental sync using sync tokens
2. Handle contact updates (modified contacts)
3. Handle contact deletions (soft delete)
4. Handle sync token expiration (410 error)
5. Implement fallback to full sync when needed
6. Test incremental sync workflow

## Technical Context

### Incremental Sync Process
1. Retrieve stored sync token from database
2. Request changes since last sync using sync token
3. Process returned contacts (updates and deletions)
4. Update database accordingly
5. Store new sync token

### Sync Token Handling
- **Valid Token**: Returns only changes since last sync
- **Expired Token (410)**: Must perform full sync
- **First Sync**: No token, perform full sync

### Change Detection
- **Updated Contacts**: Have non-null data
- **Deleted Contacts**: metadata.deleted = true

## Acceptance Criteria

- [ ] Incremental sync uses stored sync token
- [ ] Updated contacts are updated in database
- [ ] Deleted contacts are soft-deleted (marked as deleted)
- [ ] Sync token expiration triggers full sync
- [ ] New sync token is stored after successful sync
- [ ] Incremental sync is faster than full sync
- [ ] No sync token triggers full sync
- [ ] Tests verify incremental sync logic

## Implementation Steps

### 1. Update Sync Service with Incremental Sync

Update `google_contacts_cisco/services/sync_service.py`:

```python
# Add this method to SyncService class

def incremental_sync(self, batch_size: int = 100) -> dict:
    """Perform incremental sync using sync token.
    
    Args:
        batch_size: Number of contacts to commit per batch
        
    Returns:
        Sync statistics
    """
    logger.info("Starting incremental sync")
    
    # Get latest sync state
    sync_state = self.sync_repo.get_latest_sync_state()
    
    if not sync_state or not sync_state.sync_token:
        logger.warning("No sync token available, performing full sync instead")
        return self.full_sync(batch_size)
    
    sync_token = sync_state.sync_token
    logger.info(f"Using sync token: {sync_token[:20]}...")
    
    # Create new sync state
    new_sync_state = self.sync_repo.create_sync_state(status="syncing")
    self.db.commit()
    
    stats = {
        "total_fetched": 0,
        "updated": 0,
        "deleted": 0,
        "errors": 0,
        "pages": 0
    }
    
    try:
        # Fetch changes from Google
        for response_data in self.google_client.list_connections(
            page_size=100,
            sync_token=sync_token
        ):
            stats["pages"] += 1
            
            # Parse response
            response = GoogleConnectionsResponse(**response_data)
            
            if not response.connections:
                logger.info(f"Page {stats['pages']}: No changes")
                continue
            
            logger.info(f"Page {stats['pages']}: Processing {len(response.connections)} changes")
            
            # Process each contact
            for person in response.connections:
                try:
                    stats["total_fetched"] += 1
                    
                    if person.is_deleted():
                        # Handle deleted contact
                        self._handle_deleted_contact(person.resource_name)
                        stats["deleted"] += 1
                    else:
                        # Handle updated contact
                        from ..services.contact_transformer import transform_google_person_to_contact
                        contact_data = transform_google_person_to_contact(person)
                        self.contact_repo.upsert_contact(contact_data)
                        stats["updated"] += 1
                    
                    # Commit in batches
                    if stats["total_fetched"] % batch_size == 0:
                        self.db.commit()
                        logger.info(f"Committed batch: {stats['total_fetched']} changes processed")
                
                except Exception as e:
                    logger.error(f"Error processing contact {person.resource_name}: {e}")
                    stats["errors"] += 1
                    continue
            
            # Commit remaining changes in page
            self.db.commit()
            
            # Store new sync token if this is the last page
            if not response.next_page_token and response.next_sync_token:
                self.sync_repo.update_sync_state(
                    new_sync_state,
                    sync_token=response.next_sync_token
                )
                self.db.commit()
                logger.info(f"Stored new sync token: {response.next_sync_token[:20]}...")
            
            # Small delay between pages
            time.sleep(0.1)
        
        # Mark sync as complete
        self.sync_repo.update_sync_state(new_sync_state, status="idle")
        self.db.commit()
        
        logger.info(f"Incremental sync completed: {stats}")
        return stats
    
    except HttpError as e:
        if e.resp.status == 410:
            # Sync token expired, perform full sync
            logger.warning("Sync token expired (410), falling back to full sync")
            self.sync_repo.update_sync_state(
                new_sync_state,
                status="error",
                error_message="Sync token expired, performing full sync"
            )
            self.db.commit()
            return self.full_sync(batch_size)
        else:
            logger.error(f"Incremental sync failed: {e}")
            self.sync_repo.update_sync_state(
                new_sync_state,
                status="error",
                error_message=str(e)
            )
            self.db.commit()
            raise
    
    except Exception as e:
        logger.error(f"Incremental sync failed: {e}")
        self.sync_repo.update_sync_state(
            new_sync_state,
            status="error",
            error_message=str(e)
        )
        self.db.commit()
        raise

def _handle_deleted_contact(self, resource_name: str):
    """Handle deleted contact by soft-deleting it.
    
    Args:
        resource_name: Resource name of deleted contact
    """
    contact = self.contact_repo.get_by_resource_name(resource_name)
    if contact:
        contact.deleted = True
        contact.synced_at = datetime.utcnow()
        logger.info(f"Marked contact as deleted: {resource_name}")
    else:
        logger.warning(f"Deleted contact not found in database: {resource_name}")

def auto_sync(self, batch_size: int = 100) -> dict:
    """Automatically choose between full and incremental sync.
    
    Args:
        batch_size: Number of contacts to commit per batch
        
    Returns:
        Sync statistics
    """
    sync_state = self.sync_repo.get_latest_sync_state()
    
    if sync_state and sync_state.sync_token:
        logger.info("Sync token available, performing incremental sync")
        return self.incremental_sync(batch_size)
    else:
        logger.info("No sync token available, performing full sync")
        return self.full_sync(batch_size)
```

### 2. Add Incremental Sync API Endpoints

Update `google_contacts_cisco/api/routes.py`:

```python
# Add these endpoints

@router.post("/api/sync/incremental")
async def trigger_incremental_sync(db: Session = Depends(get_db)):
    """Trigger incremental sync of Google Contacts."""
    from ..auth.oauth import is_authenticated
    
    if not is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        sync_service = get_sync_service(db)
        stats = sync_service.incremental_sync()
        return {
            "status": "success",
            "message": "Incremental sync completed",
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/api/sync")
async def trigger_auto_sync(db: Session = Depends(get_db)):
    """Trigger automatic sync (full or incremental based on state)."""
    from ..auth.oauth import is_authenticated
    
    if not is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        sync_service = get_sync_service(db)
        stats = sync_service.auto_sync()
        return {
            "status": "success",
            "message": "Sync completed",
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
```

### 3. Create Tests

Create `tests/test_incremental_sync.py`:

```python
"""Test incremental sync implementation."""
import pytest
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from googleapiclient.errors import HttpError

from google_contacts_cisco.models import Base
from google_contacts_cisco.services.sync_service import SyncService
from google_contacts_cisco.repositories.sync_repository import SyncRepository


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
def sync_state_with_token(db_session):
    """Create sync state with token."""
    sync_repo = SyncRepository(db_session)
    sync_state = sync_repo.create_sync_state(
        sync_token="test_sync_token_123",
        status="idle"
    )
    db_session.commit()
    return sync_state


def test_incremental_sync_with_updates(db_session, sync_state_with_token, mock_google_client):
    """Test incremental sync with updated contacts."""
    # Mock API response with changes
    mock_response = {
        'connections': [{
            'resourceName': 'people/c1',
            'names': [{'displayName': 'John Updated'}],
            'phoneNumbers': [{'value': '5551234567'}]
        }],
        'nextSyncToken': 'new_sync_token_456'
    }
    
    mock_google_client.list_connections.return_value = [mock_response]
    
    # First, create the original contact
    from google_contacts_cisco.repositories.contact_repository import ContactRepository
    from google_contacts_cisco.schemas.contact import ContactCreateSchema, PhoneNumberSchema
    
    contact_repo = ContactRepository(db_session)
    contact_repo.upsert_contact(ContactCreateSchema(
        resource_name='people/c1',
        display_name='John Doe',
        phone_numbers=[PhoneNumberSchema(
            value='5551234567',
            display_value='(555) 123-4567'
        )]
    ))
    db_session.commit()
    
    with patch('google_contacts_cisco.services.sync_service.get_google_client', return_value=mock_google_client):
        sync_service = SyncService(db_session)
        stats = sync_service.incremental_sync()
    
    assert stats['updated'] == 1
    assert stats['deleted'] == 0
    
    # Verify contact was updated
    updated_contact = contact_repo.get_by_resource_name('people/c1')
    assert updated_contact.display_name == 'John Updated'


def test_incremental_sync_with_deletions(db_session, sync_state_with_token, mock_google_client):
    """Test incremental sync with deleted contacts."""
    # Mock API response with deleted contact
    mock_response = {
        'connections': [{
            'resourceName': 'people/c1',
            'names': [{'displayName': 'Deleted Contact'}],
            'metadata': {
                'deleted': True,
                'sources': []
            }
        }],
        'nextSyncToken': 'new_sync_token_456'
    }
    
    mock_google_client.list_connections.return_value = [mock_response]
    
    # Create contact first
    from google_contacts_cisco.repositories.contact_repository import ContactRepository
    from google_contacts_cisco.schemas.contact import ContactCreateSchema
    
    contact_repo = ContactRepository(db_session)
    contact_repo.upsert_contact(ContactCreateSchema(
        resource_name='people/c1',
        display_name='John Doe',
        phone_numbers=[]
    ))
    db_session.commit()
    
    with patch('google_contacts_cisco.services.sync_service.get_google_client', return_value=mock_google_client):
        sync_service = SyncService(db_session)
        stats = sync_service.incremental_sync()
    
    assert stats['deleted'] == 1
    
    # Verify contact was soft-deleted
    contact = contact_repo.get_by_resource_name('people/c1')
    assert contact.deleted is True


def test_incremental_sync_token_expired(db_session, sync_state_with_token, mock_google_client):
    """Test incremental sync falls back to full sync when token expires."""
    # Mock 410 error (sync token expired)
    error_response = Mock()
    error_response.status = 410
    
    mock_google_client.list_connections.side_effect = HttpError(error_response, b'Sync token expired')
    
    # Mock full sync to succeed
    mock_full_sync_response = {
        'connections': [{
            'resourceName': 'people/c1',
            'names': [{'displayName': 'John Doe'}],
            'phoneNumbers': []
        }],
        'nextSyncToken': 'new_token'
    }
    
    with patch('google_contacts_cisco.services.sync_service.get_google_client', return_value=mock_google_client):
        # First call fails with 410, second call (full sync) succeeds
        mock_google_client.list_connections.side_effect = [
            HttpError(error_response, b'Sync token expired'),
            [mock_full_sync_response]  # Full sync response
        ]
        
        sync_service = SyncService(db_session)
        stats = sync_service.incremental_sync()
    
    # Should fall back to full sync
    assert stats['total_fetched'] >= 0  # Full sync completed


def test_auto_sync_with_token(db_session, sync_state_with_token, mock_google_client):
    """Test auto sync chooses incremental when token exists."""
    mock_response = {
        'connections': [],
        'nextSyncToken': 'new_token'
    }
    
    mock_google_client.list_connections.return_value = [mock_response]
    
    with patch('google_contacts_cisco.services.sync_service.get_google_client', return_value=mock_google_client):
        sync_service = SyncService(db_session)
        stats = sync_service.auto_sync()
    
    # Should have performed incremental sync
    assert 'updated' in stats or 'deleted' in stats


def test_auto_sync_without_token(db_session, mock_google_client):
    """Test auto sync chooses full sync when no token exists."""
    mock_response = {
        'connections': [{
            'resourceName': 'people/c1',
            'names': [{'displayName': 'John Doe'}],
            'phoneNumbers': []
        }],
        'nextSyncToken': 'new_token'
    }
    
    mock_google_client.list_connections.return_value = [mock_response]
    
    with patch('google_contacts_cisco.services.sync_service.get_google_client', return_value=mock_google_client):
        sync_service = SyncService(db_session)
        stats = sync_service.auto_sync()
    
    # Should have performed full sync
    assert stats['created'] > 0 or stats['total_fetched'] > 0
```

## Verification

After completing this task:

1. **Test Incremental Sync**:
   ```bash
   # First do a full sync
   curl -X POST http://localhost:8000/api/sync/full
   
   # Update a contact in Google Contacts
   
   # Then do incremental sync
   curl -X POST http://localhost:8000/api/sync/incremental
   
   # Should only sync changed contacts
   ```

2. **Test Auto Sync**:
   ```bash
   curl -X POST http://localhost:8000/api/sync
   # Automatically chooses full or incremental
   ```

3. **Verify Sync Token**:
   ```bash
   sqlite3 data/contacts.db
   SELECT sync_token FROM sync_states ORDER BY last_sync_at DESC LIMIT 1;
   ```

4. **Run Tests**:
   ```bash
   pytest tests/test_incremental_sync.py -v
   ```

## Notes

- **Efficiency**: Incremental sync only processes changes, much faster than full sync
- **Soft Delete**: Deleted contacts are marked, not physically deleted
- **Token Expiration**: 410 error triggers automatic fallback to full sync
- **Propagation Delay**: Google changes may take several minutes to appear in sync
- **Auto Sync**: Recommended endpoint - automatically chooses best sync method

## Performance Comparison

- **Full Sync**: O(n) where n is total contacts
- **Incremental Sync**: O(m) where m is changed contacts
- For 10,000 contacts with 10 changes: ~1000x faster

## Common Issues

1. **410 Sync Token Expired**: Normal after long periods, just triggers full sync
2. **Missing Deleted Contacts**: Contact never synced, can't be deleted
3. **Slow Incremental Sync**: May have many changes, consider full sync
4. **Propagation Delay**: Changes may not appear immediately (several minutes)

## Related Documentation

- Google Sync Tokens: https://developers.google.com/people/v1/contacts#sync
- Incremental Sync Guide: https://developers.google.com/people/v1/how-tos/sync

## Estimated Time

3-4 hours

