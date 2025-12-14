# Task 6.5: Sync Management Interface

## Overview

Create a comprehensive web interface for managing contact synchronization, including manual sync triggers, real-time sync status display, sync history logs, and error handling.

## Priority

**P1 (High)** - Required for MVP

## Dependencies

- Task 3.3: Sync Service
- Task 6.1: Frontend Framework Setup

## Objectives

1. Display current sync status (idle, running, completed, error)
2. Show last sync time and statistics (contacts added/updated/deleted)
3. Add manual sync button with loading state
4. Display real-time sync progress
5. Show sync history with timestamps
6. Handle and display sync errors gracefully
7. Add automatic sync information
8. Test complete sync workflow

## Technical Context

### Sync States
- **Idle**: No sync running, system ready
- **Running**: Sync in progress
- **Completed**: Last sync successful
- **Error**: Last sync failed with error

### Real-Time Updates
- Poll `/api/sync/status` endpoint every 2-3 seconds during sync
- Show progress percentage and current operation
- Update UI immediately when sync completes or fails

### Sync Statistics
- Contacts added
- Contacts updated
- Contacts deleted
- Sync duration
- Error count

## Acceptance Criteria

- [ ] Sync status displays correctly (idle/running/completed/error)
- [ ] Manual sync button works and shows loading state
- [ ] Sync progress updates in real-time
- [ ] Sync statistics are accurate
- [ ] Sync history shows last 10 syncs
- [ ] Error messages are user-friendly
- [ ] Polling stops when sync completes
- [ ] Tests cover all sync scenarios
- [ ] Page is responsive on mobile

## Implementation Steps

### 1. Create Sync Status API Endpoint

Create `google_contacts_cisco/api/sync.py`:

```python
"""Sync API endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from ..models import get_db
from ..services.sync_service import get_sync_service, SyncService
from ..utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/sync", tags=["sync"])


# Global sync state (in production, use Redis or database)
_sync_state = {
    "status": "idle",  # idle, running, completed, error
    "progress": 0,
    "current_operation": "",
    "stats": {
        "added": 0,
        "updated": 0,
        "deleted": 0
    },
    "started_at": None,
    "completed_at": None,
    "error": None
}


class SyncStatusResponse(BaseModel):
    """Sync status response."""
    status: str
    progress: int
    current_operation: str
    stats: dict
    started_at: Optional[str]
    completed_at: Optional[str]
    error: Optional[str]


class SyncHistoryItem(BaseModel):
    """Sync history item."""
    id: int
    started_at: str
    completed_at: Optional[str]
    status: str
    contacts_added: int
    contacts_updated: int
    contacts_deleted: int
    error: Optional[str]


class SyncHistoryResponse(BaseModel):
    """Sync history response."""
    history: list[SyncHistoryItem]
    total: int


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status():
    """Get current sync status.
    
    Returns:
        Current sync status and progress
    """
    return SyncStatusResponse(**_sync_state)


@router.post("/trigger")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    force_full: bool = False,
    db: Session = Depends(get_db)
):
    """Trigger manual sync.
    
    Args:
        force_full: Force full sync instead of incremental
        
    Returns:
        Message indicating sync started
    """
    global _sync_state
    
    if _sync_state["status"] == "running":
        raise HTTPException(status_code=409, detail="Sync already running")
    
    try:
        logger.info(f"Triggering {'full' if force_full else 'incremental'} sync")
        
        # Reset sync state
        _sync_state = {
            "status": "running",
            "progress": 0,
            "current_operation": "Initializing sync...",
            "stats": {"added": 0, "updated": 0, "deleted": 0},
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "error": None
        }
        
        # Run sync in background
        background_tasks.add_task(run_sync_task, db, force_full)
        
        return {"message": "Sync started", "type": "full" if force_full else "incremental"}
    
    except Exception as e:
        logger.error(f"Error triggering sync: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to start sync")


async def run_sync_task(db: Session, force_full: bool):
    """Run sync task in background.
    
    Args:
        db: Database session
        force_full: Whether to force full sync
    """
    global _sync_state
    
    try:
        sync_service = get_sync_service(db)
        
        # Run sync
        if force_full:
            result = await sync_service.full_sync(
                progress_callback=update_sync_progress
            )
        else:
            result = await sync_service.incremental_sync(
                progress_callback=update_sync_progress
            )
        
        # Update state with results
        _sync_state.update({
            "status": "completed",
            "progress": 100,
            "current_operation": "Sync completed",
            "stats": {
                "added": result.contacts_added,
                "updated": result.contacts_updated,
                "deleted": result.contacts_deleted
            },
            "completed_at": datetime.utcnow().isoformat(),
            "error": None
        })
        
        logger.info(f"Sync completed: {result}")
        
        # Save to history
        save_sync_history(result)
        
    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        
        _sync_state.update({
            "status": "error",
            "current_operation": "Sync failed",
            "completed_at": datetime.utcnow().isoformat(),
            "error": str(e)
        })


def update_sync_progress(progress: int, operation: str):
    """Update sync progress.
    
    Args:
        progress: Progress percentage (0-100)
        operation: Current operation description
    """
    global _sync_state
    _sync_state["progress"] = progress
    _sync_state["current_operation"] = operation


def save_sync_history(result):
    """Save sync result to history.
    
    Args:
        result: Sync result object
    """
    # In production, save to database
    # For now, just log it
    logger.info(f"Saving sync history: {result}")


@router.get("/history", response_model=SyncHistoryResponse)
async def get_sync_history(
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get sync history.
    
    Args:
        limit: Maximum number of records to return
        offset: Number of records to skip
        
    Returns:
        List of sync history records
    """
    # In production, query from database
    # For now, return empty list
    return SyncHistoryResponse(history=[], total=0)


@router.get("/info")
async def get_sync_info(db: Session = Depends(get_db)):
    """Get general sync information.
    
    Returns:
        Sync configuration and statistics
    """
    from ..models.contact import Contact
    
    total_contacts = db.query(Contact).filter(Contact.deleted == False).count()
    
    return {
        "total_contacts": total_contacts,
        "last_sync": _sync_state.get("completed_at"),
        "sync_type": "automatic" if False else "manual",  # TODO: Get from config
        "sync_interval": None  # TODO: Get from config if automatic
    }
```

### 2. Create Sync Management Page

Create `google_contacts_cisco/templates/sync.html`:

```html
{% extends "base.html" %}

{% block title %}Sync Management - Google Contacts Directory{% endblock %}

{% block content %}
<div class="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
    <h1 class="text-2xl font-bold text-gray-900 mb-6">Sync Management</h1>
    
    <!-- Current Sync Status -->
    <div class="mb-8 rounded-lg bg-white p-6 shadow">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">Current Status</h2>
        
        <div id="sync-status" class="space-y-4">
            <div class="flex justify-center py-8">
                <div class="spinner"></div>
            </div>
        </div>
    </div>
    
    <!-- Sync Actions -->
    <div class="mb-8 rounded-lg bg-white p-6 shadow">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">Actions</h2>
        
        <div class="flex gap-4">
            <button 
                id="sync-button"
                onclick="triggerSync(false)"
                class="inline-flex items-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:bg-gray-300 disabled:cursor-not-allowed">
                <svg class="mr-2 h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Sync Now
            </button>
            
            <button 
                id="full-sync-button"
                onclick="triggerSync(true)"
                class="inline-flex items-center rounded-md bg-white px-4 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 disabled:bg-gray-100 disabled:cursor-not-allowed">
                <svg class="mr-2 h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Full Sync
            </button>
        </div>
        
        <p class="mt-4 text-sm text-gray-600">
            <strong>Sync Now:</strong> Incrementally sync only changed contacts<br>
            <strong>Full Sync:</strong> Re-sync all contacts from Google
        </p>
    </div>
    
    <!-- Sync Information -->
    <div class="mb-8 rounded-lg bg-white p-6 shadow">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">Information</h2>
        
        <div id="sync-info" class="space-y-2">
            <!-- Will be populated by JavaScript -->
        </div>
    </div>
    
    <!-- Sync History -->
    <div class="rounded-lg bg-white p-6 shadow">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">Sync History</h2>
        
        <div id="sync-history">
            <div class="text-center py-8 text-gray-500">
                <p>No sync history yet</p>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_scripts %}
<script src="{{ url_for('static', path='/js/sync.js') }}"></script>
{% endblock %}
```

### 3. Create Sync JavaScript

Create `google_contacts_cisco/static/js/sync.js`:

```javascript
/**
 * Sync management functionality
 */

let pollInterval = null;

async function loadSyncStatus() {
    try {
        const status = await API.get('/api/sync/status');
        renderSyncStatus(status);
        
        // Start polling if sync is running
        if (status.status === 'running') {
            startPolling();
        } else {
            stopPolling();
        }
    } catch (error) {
        console.error('Failed to load sync status:', error);
        showStatusError();
    }
}

function renderSyncStatus(status) {
    const container = document.getElementById('sync-status');
    
    // Status badge
    const statusBadge = getStatusBadge(status.status);
    
    // Progress bar (only show if running)
    const progressBar = status.status === 'running' ? `
        <div class="mt-4">
            <div class="flex items-center justify-between mb-2">
                <span class="text-sm text-gray-700">${status.current_operation}</span>
                <span class="text-sm font-medium text-gray-900">${status.progress}%</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2">
                <div class="bg-indigo-600 h-2 rounded-full transition-all duration-300" style="width: ${status.progress}%"></div>
            </div>
        </div>
    ` : '';
    
    // Statistics
    const stats = status.stats ? `
        <div class="mt-4 grid grid-cols-3 gap-4">
            <div class="text-center">
                <div class="text-2xl font-bold text-green-600">${status.stats.added}</div>
                <div class="text-xs text-gray-500">Added</div>
            </div>
            <div class="text-center">
                <div class="text-2xl font-bold text-blue-600">${status.stats.updated}</div>
                <div class="text-xs text-gray-500">Updated</div>
            </div>
            <div class="text-center">
                <div class="text-2xl font-bold text-red-600">${status.stats.deleted}</div>
                <div class="text-xs text-gray-500">Deleted</div>
            </div>
        </div>
    ` : '';
    
    // Error message
    const errorMsg = status.error ? `
        <div class="mt-4 rounded-md bg-red-50 p-4">
            <div class="flex">
                <svg class="h-5 w-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div class="ml-3">
                    <h3 class="text-sm font-medium text-red-800">Sync Error</h3>
                    <div class="mt-2 text-sm text-red-700">${status.error}</div>
                </div>
            </div>
        </div>
    ` : '';
    
    // Timestamps
    const timestamps = `
        <div class="mt-4 text-sm text-gray-600">
            ${status.started_at ? `<div>Started: ${new Date(status.started_at).toLocaleString()}</div>` : ''}
            ${status.completed_at ? `<div>Completed: ${new Date(status.completed_at).toLocaleString()}</div>` : ''}
        </div>
    `;
    
    container.innerHTML = `
        <div class="flex items-center justify-between">
            <div class="text-sm font-medium text-gray-700">Status:</div>
            ${statusBadge}
        </div>
        ${progressBar}
        ${stats}
        ${errorMsg}
        ${timestamps}
    `;
    
    // Update button states
    updateButtonStates(status.status);
}

function getStatusBadge(status) {
    const badges = {
        idle: '<span class="inline-flex items-center rounded-full bg-gray-100 px-3 py-1 text-sm font-medium text-gray-800">Idle</span>',
        running: '<span class="inline-flex items-center rounded-full bg-blue-100 px-3 py-1 text-sm font-medium text-blue-800"><span class="mr-2">●</span> Running</span>',
        completed: '<span class="inline-flex items-center rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-800">Completed</span>',
        error: '<span class="inline-flex items-center rounded-full bg-red-100 px-3 py-1 text-sm font-medium text-red-800">Error</span>'
    };
    return badges[status] || badges.idle;
}

function updateButtonStates(status) {
    const syncButton = document.getElementById('sync-button');
    const fullSyncButton = document.getElementById('full-sync-button');
    
    const isRunning = status === 'running';
    
    syncButton.disabled = isRunning;
    fullSyncButton.disabled = isRunning;
    
    if (isRunning) {
        syncButton.innerHTML = `
            <div class="spinner w-5 h-5 mr-2"></div>
            Syncing...
        `;
    } else {
        syncButton.innerHTML = `
            <svg class="mr-2 h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Sync Now
        `;
    }
}

async function triggerSync(forceFull = false) {
    try {
        const syncType = forceFull ? 'Full' : 'Incremental';
        
        await API.post(`/api/sync/trigger?force_full=${forceFull}`);
        
        Toast.show(`${syncType} sync started`, 'success');
        
        // Start polling for status updates
        startPolling();
        
        // Reload status immediately
        loadSyncStatus();
        
    } catch (error) {
        console.error('Failed to trigger sync:', error);
        
        if (error.message.includes('409')) {
            Toast.show('Sync already running', 'warning');
        } else {
            Toast.show('Failed to start sync', 'error');
        }
    }
}

function startPolling() {
    if (pollInterval) return; // Already polling
    
    pollInterval = setInterval(() => {
        loadSyncStatus();
    }, 2000); // Poll every 2 seconds
}

function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

async function loadSyncInfo() {
    try {
        const info = await API.get('/api/sync/info');
        
        const container = document.getElementById('sync-info');
        container.innerHTML = `
            <div class="flex justify-between py-2">
                <span class="text-sm text-gray-600">Total Contacts:</span>
                <span class="text-sm font-medium text-gray-900">${info.total_contacts}</span>
            </div>
            <div class="flex justify-between py-2">
                <span class="text-sm text-gray-600">Last Sync:</span>
                <span class="text-sm font-medium text-gray-900">
                    ${info.last_sync ? new Date(info.last_sync).toLocaleString() : 'Never'}
                </span>
            </div>
            <div class="flex justify-between py-2">
                <span class="text-sm text-gray-600">Sync Type:</span>
                <span class="text-sm font-medium text-gray-900">${info.sync_type || 'Manual'}</span>
            </div>
        `;
    } catch (error) {
        console.error('Failed to load sync info:', error);
    }
}

async function loadSyncHistory() {
    try {
        const response = await API.get('/api/sync/history');
        
        const container = document.getElementById('sync-history');
        
        if (response.history.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8 text-gray-500">
                    <p>No sync history yet</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = `
            <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Started</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Added</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Updated</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Deleted</th>
                        </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
                        ${response.history.map(item => `
                            <tr>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                    ${new Date(item.started_at).toLocaleString()}
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    ${getStatusBadge(item.status)}
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${item.contacts_added}</td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${item.contacts_updated}</td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${item.contacts_deleted}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    } catch (error) {
        console.error('Failed to load sync history:', error);
    }
}

function showStatusError() {
    const container = document.getElementById('sync-status');
    container.innerHTML = `
        <div class="text-center py-8 text-red-600">
            <svg class="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p class="mt-4">Failed to load sync status</p>
            <button onclick="loadSyncStatus()" class="mt-4 text-sm text-indigo-600 hover:text-indigo-500">Try again</button>
        </div>
    `;
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    loadSyncStatus();
    loadSyncInfo();
    loadSyncHistory();
});

// Cleanup polling on page unload
window.addEventListener('beforeunload', () => {
    stopPolling();
});

// Make function available globally
window.triggerSync = triggerSync;
```

### 4. Register Routes

Update `google_contacts_cisco/main.py`:

```python
from google_contacts_cisco.api import directory, search, contacts, sync

# Include routers
app.include_router(directory.router)
app.include_router(search.router)
app.include_router(contacts.router)
app.include_router(sync.router)


@app.get("/sync", response_class=HTMLResponse)
async def sync_page(request: Request):
    """Sync management page."""
    return templates.TemplateResponse(
        "sync.html",
        {"request": request, "version": __version__}
    )
```

## Verification

After completing this task:

1. **Start Server**:
   ```bash
   uv run python -m google_contacts_cisco.main
   ```

2. **View Sync Page**:
   - Open http://localhost:8000/sync
   - Should see sync management interface

3. **Test Manual Sync**:
   - Click "Sync Now" button
   - Status should change to "Running"
   - Progress bar should appear and update
   - Statistics should update when complete

4. **Test Full Sync**:
   - Click "Full Sync" button
   - Should trigger full re-sync
   - All contacts should be refreshed

5. **Test Real-Time Updates**:
   - Start a sync
   - Watch progress bar update
   - Status should update every 2 seconds

6. **Test Error Handling**:
   - Disconnect internet or stop Google API access
   - Trigger sync
   - Should show error message in red box

7. **Test Polling**:
   - Open browser dev tools (Network tab)
   - Start a sync
   - Should see polling requests every 2 seconds
   - Polling should stop when sync completes

8. **Test Button States**:
   - During sync, buttons should be disabled
   - After sync, buttons should re-enable

9. **Run Tests**:
   ```bash
   uv run pytest tests/test_sync_api.py -v
   ```

## Notes

- **Polling**: Uses 2-second interval to balance responsiveness and server load
- **State Management**: Global state works for single instance; use Redis for multi-instance
- **Progress**: Callback function updates progress from sync service
- **History**: Should be persisted to database in production
- **Error Handling**: Captures and displays sync errors gracefully
- **Button States**: Disabled during sync to prevent multiple concurrent syncs
- **Cleanup**: Polling stops when page is closed to prevent memory leaks

## Common Issues

1. **Polling Continues After Page Close**: Add `beforeunload` handler
2. **Multiple Syncs**: Check sync status before allowing new sync
3. **Stale Progress**: Ensure progress callback is called regularly
4. **Memory Leaks**: Clear interval when component unmounts
5. **Race Conditions**: Use locking mechanism for concurrent sync requests
6. **State Persistence**: Store sync state in database for multi-instance deployments

## Performance Optimization

- Cache sync status for 1-2 seconds
- Use WebSocket instead of polling for real-time updates
- Batch status updates to reduce overhead
- Add sync queue for multiple requests
- Implement rate limiting

## Future Enhancements

- Add automatic scheduled syncs
- Add sync configuration (frequency, time)
- Add selective sync (only certain groups)
- Add sync conflict resolution UI
- Add sync preview (show what will change)
- Add export sync logs
- Add sync notifications

## Related Documentation

- Background Tasks: https://fastapi.tiangolo.com/tutorial/background-tasks/
- Polling vs WebSocket: https://ably.com/topic/websockets-vs-polling
- Progress Callbacks: https://realpython.com/python-progress-bar/

## Estimated Time

4-5 hours

