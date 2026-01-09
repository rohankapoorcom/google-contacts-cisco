# Postman Collection

## Overview

This directory contains a Postman collection for testing the Google Contacts to Cisco IP Phone API. The collection includes all API endpoints organized by category.

## Import to Postman

### Method 1: Import from File

1. Open Postman
2. Click "Import" button
3. Select "File" tab
4. Choose `collection.json` from this directory
5. Click "Import"

### Method 2: Import from URL

If you have the collection published or hosted:

```
https://raw.githubusercontent.com/YOUR_REPO/main/docs/postman/collection.json
```

## Collection Structure

The collection is organized into the following folders:

1. **Health Check** - Application health and status
2. **Authentication** - OAuth 2.0 flow and token management
3. **Contacts** - Contact listing and retrieval
4. **Search** - Full-text search functionality
5. **Synchronization** - Google Contacts sync operations
6. **Cisco Directory** - XML directory for Cisco phones
7. **Google API** - Google API connection testing

## Configuration

### Environment Variables

The collection uses the following variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `base_url` | API base URL | `http://localhost:8000` |
| `contact_id` | Contact UUID for testing | (empty) |

### Setting Variables

**Option 1: Create Environment**

1. Click "Environments" in Postman
2. Click "+" to create new environment
3. Name it "Local Development"
4. Add variables:
   - `base_url`: `http://localhost:8000`
5. Click "Save"
6. Select environment from dropdown

**Option 2: Use Collection Variables**

The collection includes default values for `base_url`. You can override these:

1. Click on collection name
2. Go to "Variables" tab
3. Update "Current Value" column
4. Click "Save"

## Usage

### 1. Check Application Health

Before testing, verify the application is running:

```
GET /health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "debug": true,
  "config_valid": true
}
```

### 2. Authenticate

**Note**: OAuth flow requires browser interaction. The Postman requests help you:

1. Get OAuth URL:
   ```
   GET /auth/url
   ```

2. Copy the `auth_url` from response
3. Open URL in browser
4. Complete OAuth flow
5. Verify authentication:
   ```
   GET /auth/status
   ```

### 3. Sync Contacts

Trigger initial sync:
```
POST /api/sync
```

This downloads contacts from Google. Monitor progress with:
```
GET /api/sync/status
```

### 4. Test Contact Endpoints

Once synced, test various endpoints:

**List contacts**:
```
GET /api/contacts?limit=10
```

**Get single contact** (copy ID from list response):
1. Set `contact_id` variable to a UUID from the list
2. Run: `GET /api/contacts/{{contact_id}}`

**Search contacts**:
```
GET /api/search?q=john
```

### 5. Test Cisco Directory

**Get main directory**:
```
GET /directory
```

Expected: XML menu with keypad groups

**Get group directory**:
```
GET /directory/groups/2ABC
```

Expected: XML menu with contacts in group

## Testing Workflow

### Complete Test Flow

1. **Health Check** → Verify app is running
2. **Get Auth Status** → Check if authenticated
3. **If not authenticated**:
   - Get OAuth URL
   - Complete OAuth in browser
   - Verify with Auth Status
4. **Test Google Connection** → Verify API access
5. **Trigger Sync** → Download contacts
6. **Get Sync Status** → Monitor progress
7. **List Contacts** → Verify contacts loaded
8. **Search Contacts** → Test search
9. **Get Directory** → Test Cisco XML

### Automated Testing

For automated testing, use Postman's Collection Runner:

1. Click on collection
2. Click "Run" button
3. Select requests to run
4. Click "Run Google Contacts API"

**Note**: Skip OAuth-related requests in automated runs as they require browser interaction.

## Example Workflows

### Workflow 1: Initial Setup

```
1. GET /health                     # Check app is healthy
2. GET /auth/status                # Check auth status
3. GET /auth/url                   # Get OAuth URL (open in browser)
4. GET /auth/status                # Verify authenticated
5. GET /api/test-connection        # Test Google API
6. POST /api/sync                  # Initial full sync
7. GET /api/sync/status            # Check sync progress
8. GET /api/contacts/stats         # View contact count
```

### Workflow 2: Daily Operations

```
1. GET /auth/status                # Check auth
2. POST /api/sync                  # Daily sync (auto-incremental)
3. GET /api/sync/statistics        # View sync stats
4. GET /api/search?q=smith         # Search for contact
5. GET /directory                  # Test Cisco directory
```

### Workflow 3: Troubleshooting

```
1. GET /health                     # Check overall health
2. GET /auth/status                # Check auth details
3. POST /auth/refresh              # Try refreshing token
4. GET /api/test-connection        # Test Google API
5. GET /api/sync/status            # Check last sync
6. GET /api/contacts?limit=5       # Sample contacts
```

## Response Examples

### Successful Contact List

```json
{
  "contacts": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "resource_name": "people/c1234567890",
      "display_name": "John Doe",
      "given_name": "John",
      "family_name": "Doe",
      "phone_numbers": [
        {
          "id": "660e8400-e29b-41d4-a716-446655440000",
          "value": "+1234567890",
          "display_value": "+1 (234) 567-890",
          "type": "mobile",
          "primary": true
        }
      ]
    }
  ],
  "total": 150,
  "offset": 0,
  "limit": 30,
  "has_more": true
}
```

### Successful Search

```json
{
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "display_name": "John Doe",
      "phone_numbers": [...],
      "match_type": "prefix",
      "match_field": "display_name"
    }
  ],
  "count": 1,
  "query": "john",
  "elapsed_ms": 12.5
}
```

### Successful Sync

```json
{
  "status": "success",
  "message": "Incremental sync completed successfully",
  "statistics": {
    "sync_type": "incremental",
    "contacts_added": 5,
    "contacts_updated": 12,
    "contacts_deleted": 2,
    "total_contacts": 150,
    "duration_seconds": 3.45
  }
}
```

## Common Issues

### Base URL Not Working

If you're getting connection errors:

1. Check application is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Update `base_url` variable to match your setup:
   - Local: `http://localhost:8000`
   - Docker: `http://localhost:8000`
   - Production: `https://yourdomain.com`

### 401 Unauthorized Errors

If getting 401 errors on sync/contacts:

1. Run `GET /auth/status`
2. If not authenticated, complete OAuth flow
3. Run `POST /auth/refresh` if token expired

### Contact ID Not Found

To get a valid contact ID:

1. Run `GET /api/contacts?limit=1`
2. Copy the `id` from first contact
3. Set as `contact_id` variable
4. Retry the request

## Advanced Usage

### Pre-request Scripts

You can add pre-request scripts to automate variable setting:

```javascript
// Auto-extract contact ID from list response
pm.test("Extract contact ID", function () {
    var jsonData = pm.response.json();
    if (jsonData.contacts && jsonData.contacts.length > 0) {
        pm.collectionVariables.set("contact_id", jsonData.contacts[0].id);
    }
});
```

### Tests

Add test scripts to verify responses:

```javascript
// Test successful response
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Response has contacts", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.contacts).to.be.an('array');
    pm.expect(jsonData.contacts.length).to.be.above(0);
});
```

## Documentation

For detailed API documentation, see:

- [API Documentation](../api.md) - Complete API reference
- [Authentication Guide](../authentication.md) - OAuth setup and troubleshooting
- [Troubleshooting Guide](../troubleshooting.md) - Common issues and solutions

## Support

For issues with the Postman collection:

1. Check collection is up to date
2. Verify environment variables are set
3. Review API documentation
4. Check application logs for errors
