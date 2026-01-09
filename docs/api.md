# API Documentation

## Overview

The Google Contacts to Cisco IP Phone application provides a comprehensive REST API for managing contacts, synchronization, and serving Cisco XML directories. This document provides detailed information about all available endpoints, request/response formats, and usage examples.

## Base URL

```
http://localhost:8000
```

For production deployments, replace with your server's URL.

## API Endpoints

The API is organized into the following groups:

- **Authentication**: OAuth 2.0 flow with Google (`/auth/*`)
- **Contacts**: Contact management and listing (`/api/contacts/*`)
- **Search**: Full-text search (`/api/search`, `/api/contacts/search*`)
- **Synchronization**: Google Contacts sync (`/api/sync/*`)
- **Cisco Directory**: XML directory for Cisco IP Phones (`/directory/*`)
- **Google API**: Google People API testing (`/api/test-connection`)

## Interactive Documentation

FastAPI provides automatically generated interactive documentation:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## Authentication Endpoints

### Overview

OAuth 2.0 authentication flow with Google for accessing Google Contacts API. The application stores and manages access and refresh tokens securely.

### Get OAuth URL

**Endpoint**: `GET /auth/url`

Returns the Google OAuth authorization URL for client-side redirects.

**Query Parameters**:
- `redirect_uri` (optional): Custom URI to redirect to after authentication

**Response** (`200 OK`):
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "/sync"
}
```

**Example**:
```bash
curl http://localhost:8000/auth/url
```

**Use Case**: Frontend applications can retrieve the OAuth URL and redirect users to it.

---

### Initiate OAuth Flow

**Endpoint**: `GET /auth/google`

Server-side redirect to Google's OAuth consent screen.

**Query Parameters**:
- `redirect_uri` (optional): Custom URI to redirect to after authentication

**Response**: `307 Temporary Redirect` to Google OAuth

**Example**:
```bash
# Visit in browser
http://localhost:8000/auth/google
```

**Use Case**: Direct browser access or server-side redirects.

---

### OAuth Callback

**Endpoint**: `GET /auth/callback`

Handles the OAuth callback from Google. Exchanges authorization code for access/refresh tokens.

**Query Parameters** (provided by Google):
- `code`: Authorization code
- `state`: CSRF state parameter (may contain redirect URI)
- `error`: Error code if user denied access
- `error_description`: Human-readable error description

**Response**: HTML page with success or error message

**Example**:
```
# Automatically called by Google after user grants permission
http://localhost:8000/auth/callback?code=4/0AfJ...&state=/sync
```

**Use Case**: OAuth flow completion (automatic).

---

### Get Authentication Status

**Endpoint**: `GET /auth/status`

Returns detailed authentication status information.

**Response** (`200 OK`):
```json
{
  "authenticated": true,
  "has_token_file": true,
  "credentials_valid": true,
  "credentials_expired": false,
  "has_refresh_token": true,
  "scopes": [
    "https://www.googleapis.com/auth/contacts.readonly"
  ]
}
```

**Example**:
```bash
curl http://localhost:8000/auth/status
```

**Response Fields**:
- `authenticated`: Overall authentication state
- `has_token_file`: Token file exists on disk
- `credentials_valid`: Credentials are valid (not expired)
- `credentials_expired`: Credentials have expired (but may be refreshable)
- `has_refresh_token`: Refresh token is available for automatic renewal
- `scopes`: OAuth scopes granted by user

---

### Refresh Access Token

**Endpoint**: `POST /auth/refresh`

Manually refreshes the access token using the refresh token.

**Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Access token refreshed successfully"
}
```

**Error Responses**:
- `401 Unauthorized`: Not authenticated or no refresh token
- `500 Internal Server Error`: Refresh failed

**Example**:
```bash
curl -X POST http://localhost:8000/auth/refresh
```

**Use Case**: Manually refresh token when it's about to expire or after encountering auth errors.

---

### Revoke Credentials

**Endpoint**: `POST /auth/revoke` or `POST /auth/disconnect`

Revokes OAuth credentials with Google and deletes local token file.

**Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Credentials revoked and deleted successfully"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/auth/revoke
```

**Use Case**: Disconnect Google account from application.

---

## Contact Endpoints

### List Contacts

**Endpoint**: `GET /api/contacts`

Returns a paginated list of contacts with filtering and sorting options.

**Query Parameters**:
- `limit` (int, default: 30): Number of contacts per page (1-100)
- `offset` (int, default: 0): Offset for pagination
- `sort` (string, default: "name"): Sort order (`name` or `recent`)
- `group` (string, optional): Filter by first letter (A-Z) or `#` for numbers/special characters

**Response** (`200 OK`):
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
      ],
      "email_addresses": [
        {
          "id": "770e8400-e29b-41d4-a716-446655440000",
          "value": "john.doe@example.com",
          "type": "work",
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

**Examples**:

Get first page of contacts:
```bash
curl http://localhost:8000/api/contacts?limit=20
```

Get contacts starting with 'A':
```bash
curl http://localhost:8000/api/contacts?group=A
```

Get recently updated contacts:
```bash
curl http://localhost:8000/api/contacts?sort=recent&limit=10
```

**Sorting Options**:
- `name`: Alphabetical by display name (default)
- `recent`: Most recently updated first

**Filtering**:
- Use `group=A` through `group=Z` for alphabetical filtering
- Use `group=#` for contacts starting with numbers or special characters

---

### Get Single Contact

**Endpoint**: `GET /api/contacts/{contact_id}`

Returns detailed information for a single contact.

**Path Parameters**:
- `contact_id` (UUID): Contact's unique identifier

**Response** (`200 OK`):
```json
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
  ],
  "email_addresses": []
}
```

**Error Responses**:
- `404 Not Found`: Contact doesn't exist or is deleted
- `500 Internal Server Error`: Database error

**Example**:
```bash
curl http://localhost:8000/api/contacts/550e8400-e29b-41d4-a716-446655440000
```

---

### Get Contact Statistics

**Endpoint**: `GET /api/contacts/stats`

Returns aggregate statistics about contacts in the database.

**Response** (`200 OK`):
```json
{
  "total_contacts": 150,
  "contacts_with_phone": 145,
  "contacts_with_email": 120,
  "total_phone_numbers": 180,
  "total_emails": 125
}
```

**Example**:
```bash
curl http://localhost:8000/api/contacts/stats
```

**Use Case**: Dashboard widgets, monitoring contact database health.

---

## Search Endpoints

### Search Contacts

**Endpoint**: `GET /api/search`

Performs real-time search across contact names and phone numbers with multiple matching strategies.

**Query Parameters**:
- `q` (string, required): Search query (minimum 2 characters)
- `limit` (int, default: 50): Maximum results to return (1-100)

**Matching Strategies**:
1. **Exact match**: Full name or phone number match
2. **Prefix match**: Name starts with query
3. **Substring match**: Name contains query
4. **Phone match**: Phone number contains query digits

**Response** (`200 OK`):
```json
{
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
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
      ],
      "email_addresses": [],
      "match_type": "prefix",
      "match_field": "display_name"
    }
  ],
  "count": 1,
  "query": "john",
  "elapsed_ms": 12.5
}
```

**Response Fields**:
- `match_type`: How the contact matched (`exact`, `prefix`, `substring`, `phone`)
- `match_field`: Which field matched the query
- `elapsed_ms`: Search execution time in milliseconds

**Error Responses**:
- `400 Bad Request`: Query is empty or too short (< 2 characters)
- `500 Internal Server Error`: Search failed

**Examples**:

Search by name:
```bash
curl "http://localhost:8000/api/search?q=john"
```

Search by phone number:
```bash
curl "http://localhost:8000/api/search?q=234567"
```

Search with limit:
```bash
curl "http://localhost:8000/api/search?q=smith&limit=10"
```

**Performance**: Typical response time <50ms for databases with <10,000 contacts.

---

## Synchronization Endpoints

### Overview

The synchronization API manages the process of downloading contacts from Google and storing them locally. It supports both full and incremental synchronization.

### Get Sync Status

**Endpoint**: `GET /api/sync/status`

Returns the current synchronization status and metadata.

**Response** (`200 OK`):
```json
{
  "status": "idle",
  "last_sync_at": "2026-01-08T10:30:00Z",
  "has_sync_token": true,
  "error_message": null,
  "contact_count": 150,
  "total_contacts": 150
}
```

**Status Values**:
- `never_synced`: No sync has been performed
- `idle`: Not currently syncing
- `syncing`: Sync in progress
- `error`: Last sync failed

**Example**:
```bash
curl http://localhost:8000/api/sync/status
```

---

### Trigger Auto Sync

**Endpoint**: `POST /api/sync`

Automatically chooses between full and incremental sync based on current state.

**Sync Selection Logic**:
- If sync token exists → incremental sync
- If no sync token → full sync

**Response** (`200 OK`):
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
    "duration_seconds": 3.45,
    "started_at": "2026-01-08T10:30:00Z",
    "completed_at": "2026-01-08T10:30:03Z"
  }
}
```

**Error Responses**:
- `401 Unauthorized`: Not authenticated with Google
- `409 Conflict`: Sync already in progress
- `500 Internal Server Error`: Sync failed

**Example**:
```bash
curl -X POST http://localhost:8000/api/sync
```

**Recommended Use**: This is the recommended endpoint for most sync operations as it intelligently selects the appropriate sync method.

---

### Trigger Full Sync

**Endpoint**: `POST /api/sync/full`

Forces a complete synchronization of all contacts from Google.

**When to Use**:
- Initial setup (first sync)
- After sync token expires (410 error)
- When incremental sync is not working correctly
- To refresh all contact data

**Response** (`200 OK`):
```json
{
  "status": "success",
  "message": "Full sync completed successfully",
  "statistics": {
    "sync_type": "full",
    "contacts_added": 150,
    "contacts_updated": 0,
    "contacts_deleted": 0,
    "total_contacts": 150,
    "duration_seconds": 12.34,
    "started_at": "2026-01-08T10:30:00Z",
    "completed_at": "2026-01-08T10:30:12Z"
  }
}
```

**Performance**: 
- Small accounts (< 1000 contacts): 5-15 seconds
- Medium accounts (1000-5000 contacts): 15-60 seconds
- Large accounts (> 5000 contacts): 1-5 minutes

**Example**:
```bash
curl -X POST http://localhost:8000/api/sync/full
```

---

### Trigger Incremental Sync

**Endpoint**: `POST /api/sync/incremental`

Syncs only contacts that changed since the last sync using the stored sync token.

**Prerequisites**:
- At least one full sync completed (to have a sync token)
- Sync token not expired (< 7 days old typically)

**Response** (`200 OK`):
```json
{
  "status": "success",
  "message": "Incremental sync completed successfully",
  "statistics": {
    "sync_type": "incremental",
    "contacts_added": 3,
    "contacts_updated": 8,
    "contacts_deleted": 1,
    "total_contacts": 152,
    "duration_seconds": 2.15,
    "started_at": "2026-01-08T10:30:00Z",
    "completed_at": "2026-01-08T10:30:02Z"
  }
}
```

**Fallback Behavior**:
If the sync token is expired or invalid (Google returns 410 Gone), the endpoint automatically falls back to a full sync.

**Performance**: Typically completes in 1-5 seconds regardless of total contact count.

**Example**:
```bash
curl -X POST http://localhost:8000/api/sync/incremental
```

---

### Trigger Safe Sync

**Endpoint**: `POST /api/sync/safe`

Triggers sync with concurrency protection using a lock mechanism.

**Response** (`200 OK` on success):
```json
{
  "status": "success",
  "message": "Incremental sync completed successfully",
  "statistics": { ... }
}
```

**Response** (`409 Conflict` when sync in progress):
```json
{
  "status": "skipped",
  "message": "Sync already in progress"
}
```

**Use Case**: Recommended for background jobs, scheduled tasks, or webhooks to prevent multiple simultaneous syncs.

**Example**:
```bash
curl -X POST http://localhost:8000/api/sync/safe
```

---

### Check if Full Sync Needed

**Endpoint**: `GET /api/sync/needs-sync`

Determines whether a full sync is required.

**Response** (`200 OK`):
```json
{
  "needs_full_sync": false,
  "reason": "Incremental sync available"
}
```

**Reasons**:
- `"No previous sync found"`: Never synced before
- `"Sync token not available"`: Token was deleted or invalidated
- `"Sync token may have expired"`: Token is old
- `"Incremental sync available"`: Ready for incremental sync

**Example**:
```bash
curl http://localhost:8000/api/sync/needs-sync
```

**Use Case**: Decision logic for UI or automated sync scheduling.

---

### Get Sync History

**Endpoint**: `GET /api/sync/history`

Returns a list of recent sync operations with their outcomes.

**Query Parameters**:
- `limit` (int, default: 10): Number of records to return (1-100)

**Response** (`200 OK`):
```json
{
  "history": [
    {
      "id": "sync_20260108_103000",
      "status": "idle",
      "last_sync_at": "2026-01-08T10:30:00Z",
      "has_sync_token": true,
      "error_message": null
    },
    {
      "id": "sync_20260108_093000",
      "status": "idle",
      "last_sync_at": "2026-01-08T09:30:00Z",
      "has_sync_token": true,
      "error_message": null
    }
  ]
}
```

**Example**:
```bash
curl http://localhost:8000/api/sync/history?limit=20
```

---

### Get Sync Statistics

**Endpoint**: `GET /api/sync/statistics`

Returns comprehensive synchronization statistics.

**Response** (`200 OK`):
```json
{
  "contacts": {
    "total": 150,
    "active": 148,
    "deleted": 2
  },
  "phone_numbers": 180,
  "sync": {
    "last_sync_at": "2026-01-08T10:30:00Z",
    "status": "idle",
    "has_sync_token": true,
    "error_message": null
  },
  "sync_history": {
    "success": 25,
    "error": 2,
    "total": 27
  }
}
```

**Example**:
```bash
curl http://localhost:8000/api/sync/statistics
```

**Use Case**: Dashboard overview, monitoring sync health.

---

### Clear Sync History

**Endpoint**: `DELETE /api/sync/history`

Removes old sync state records from the database.

**Query Parameters**:
- `keep_latest` (bool, default: true): Keep the most recent sync state

**Response** (`200 OK`):
```json
{
  "status": "success",
  "deleted_count": 15
}
```

**Example**:
```bash
curl -X DELETE "http://localhost:8000/api/sync/history?keep_latest=true"
```

**Use Case**: Database maintenance, cleanup of old sync records.

---

## Cisco Directory Endpoints

### Overview

These endpoints serve XML formatted directories compatible with Cisco IP Phones. They implement a three-level hierarchy:
1. **Main Menu**: Phone keypad groups (1, 2ABC, 3DEF, etc.)
2. **Group Menu**: Contacts in a specific group
3. **Contact Directory**: Individual contact with dialable phone numbers

All XML responses use the `text/xml; charset=utf-8` content type and follow Cisco IP Phone XML Object specifications.

### Get Main Directory

**Endpoint**: `GET /directory`

Returns the main directory menu with phone keypad groups.

**Response** (`200 OK`):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CiscoIPPhoneMenu>
  <Title>Google Contacts</Title>
  <Prompt>Select a group</Prompt>
  <MenuItem>
    <Name>1</Name>
    <URL>http://localhost:8000/directory/groups/1</URL>
  </MenuItem>
  <MenuItem>
    <Name>2ABC</Name>
    <URL>http://localhost:8000/directory/groups/2ABC</URL>
  </MenuItem>
  <!-- More groups... -->
</CiscoIPPhoneMenu>
```

**Example**:
```bash
curl http://localhost:8000/directory
```

**Phone Keypad Groups**:
- `1`: Contacts starting with 1
- `2ABC`: Contacts starting with 2, A, B, or C
- `3DEF`: Contacts starting with 3, D, E, or F
- `4GHI`: Contacts starting with 4, G, H, or I
- `5JKL`: Contacts starting with 5, J, K, or L
- `6MNO`: Contacts starting with 6, M, N, or O
- `7PQRS`: Contacts starting with 7, P, Q, R, or S
- `8TUV`: Contacts starting with 8, T, U, or V
- `9WXYZ`: Contacts starting with 9, W, X, Y, or Z
- `0`: Contacts starting with 0
- `*`: Contacts starting with special characters

---

### Get Group Directory

**Endpoint**: `GET /directory/groups/{group}`

Returns contacts in a specific phone keypad group.

**Path Parameters**:
- `group` (string): Group identifier (e.g., "2ABC", "5JKL")

**Response** (`200 OK`):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CiscoIPPhoneMenu>
  <Title>2ABC Contacts</Title>
  <Prompt>Select contact (5 total)</Prompt>
  <MenuItem>
    <Name>Alice Smith</Name>
    <URL>http://localhost:8000/directory/contacts/550e8400-e29b-41d4-a716-446655440000</URL>
  </MenuItem>
  <MenuItem>
    <Name>Bob Jones</Name>
    <URL>http://localhost:8000/directory/contacts/660e8400-e29b-41d4-a716-446655440001</URL>
  </MenuItem>
  <!-- More contacts... -->
  <SoftKeyItem>
    <Name>Back</Name>
    <URL>http://localhost:8000/directory</URL>
    <Position>1</Position>
  </SoftKeyItem>
</CiscoIPPhoneMenu>
```

**Example**:
```bash
curl http://localhost:8000/directory/groups/2ABC
```

---

### Get Contact Directory

**Endpoint**: `GET /directory/contacts/{contact_id}`

Returns a dialable directory for an individual contact with all their phone numbers.

**Path Parameters**:
- `contact_id` (UUID): Contact's unique identifier

**Response** (`200 OK`):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CiscoIPPhoneDirectory>
  <Title>John Doe</Title>
  <Prompt>Select number to dial</Prompt>
  <DirectoryEntry>
    <Name>Mobile</Name>
    <Telephone>+1234567890</Telephone>
  </DirectoryEntry>
  <DirectoryEntry>
    <Name>Work</Name>
    <Telephone>+1987654321</Telephone>
  </DirectoryEntry>
  <SoftKeyItem>
    <Name>Dial</Name>
    <URL>SoftKey:Dial</URL>
    <Position>1</Position>
  </SoftKeyItem>
  <SoftKeyItem>
    <Name>Back</Name>
    <URL>http://localhost:8000/directory/groups/5JKL</URL>
    <Position>2</Position>
  </SoftKeyItem>
</CiscoIPPhoneDirectory>
```

**Example**:
```bash
curl http://localhost:8000/directory/contacts/550e8400-e29b-41d4-a716-446655440000
```

---

### Get Help

**Endpoint**: `GET /directory/help`

Returns context-specific help text in Cisco XML format.

**Query Parameters**:
- `context` (string, default: "main"): Help context (`main`, `group/<group>`, `contact`)

**Response** (`200 OK`):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CiscoIPPhoneText>
  <Title>Help - Directory</Title>
  <Text>
    Use phone keypad to navigate:
    - Select a group (1, 2ABC, etc.)
    - Choose a contact
    - Press Dial to call
  </Text>
  <Prompt>Press Exit to return</Prompt>
</CiscoIPPhoneText>
```

**Example**:
```bash
curl "http://localhost:8000/directory/help?context=main"
```

---

## Google API Endpoints

### Test Google Connection

**Endpoint**: `GET /api/test-connection`

Verifies that the application can successfully connect to Google People API with stored credentials.

**Response** (`200 OK`):
```json
{
  "status": "success",
  "message": "Successfully connected to Google People API",
  "total_contacts": 150
}
```

**Error Responses**:
- `401 Unauthorized`: Not authenticated
- `429 Too Many Requests`: Rate limit exceeded
- `502 Bad Gateway`: Google API server error
- `500 Internal Server Error`: Connection test failed

**Example**:
```bash
curl http://localhost:8000/api/test-connection
```

**Use Case**: 
- Verify OAuth setup is working
- Check API connectivity before sync
- Troubleshooting authentication issues

---

## Health Check Endpoint

### Health Check

**Endpoint**: `GET /health`

Returns application health status and configuration validation.

**Response** (`200 OK`):
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "debug": true,
  "config_valid": true,
  "config_errors": []
}
```

**Example**:
```bash
curl http://localhost:8000/health
```

**Use Case**: 
- Kubernetes/Docker health probes
- Load balancer health checks
- Monitoring systems

---

## Error Handling

### Standard Error Response Format

All API endpoints use a consistent error response format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

The API uses standard HTTP status codes:

**Success Codes**:
- `200 OK`: Request succeeded
- `307 Temporary Redirect`: OAuth redirect

**Client Error Codes**:
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required or failed
- `404 Not Found`: Resource not found
- `409 Conflict`: Request conflicts with current state (e.g., sync in progress)

**Server Error Codes**:
- `500 Internal Server Error`: Unexpected server error
- `502 Bad Gateway`: External service (Google API) error

### Common Error Scenarios

#### Authentication Errors

**Not Authenticated**:
```json
{
  "detail": "Not authenticated with Google. Please complete OAuth setup first."
}
```

**Expired Credentials**:
```json
{
  "detail": "Token refresh failed: invalid_grant"
}
```

**Solution**: Revoke credentials and re-authenticate through OAuth flow.

#### Sync Errors

**Sync Already in Progress**:
```json
{
  "detail": "A sync is already in progress. Please wait for it to complete."
}
```

**Solution**: Wait for current sync to finish or use `/api/sync/status` to check status.

**Sync Token Expired**:
Automatically handled by falling back to full sync.

#### Search Errors

**Query Too Short**:
```json
{
  "detail": "Search query must be at least 2 characters"
}
```

**Solution**: Provide a longer search query.

#### Rate Limiting

**Google API Rate Limit**:
```json
{
  "detail": "Rate limit exceeded: Too many requests"
}
```

**Solution**: Wait and retry. The application implements exponential backoff automatically.

---

## Rate Limiting

### Google API Quotas

The Google People API has the following quotas:
- **Requests per day**: 1,000,000 (shared across all API calls)
- **Requests per 100 seconds per user**: 600
- **Requests per 100 seconds**: 30,000

### Application Rate Limiting

The application implements:
- Exponential backoff on rate limit errors (HTTP 429)
- Automatic retry with delays (up to 3 attempts)
- Request throttling during sync operations

### Best Practices

1. **Use incremental sync**: Reduces API calls significantly
2. **Avoid frequent full syncs**: Only when necessary
3. **Implement caching**: Cache contact lists in your frontend
4. **Batch operations**: Use pagination efficiently

---

## Pagination

### Standard Pagination

Most list endpoints support pagination using `limit` and `offset` parameters:

**Request**:
```
GET /api/contacts?limit=20&offset=40
```

**Response**:
```json
{
  "contacts": [...],
  "total": 150,
  "offset": 40,
  "limit": 20,
  "has_more": true
}
```

### Pagination Fields

- `total`: Total number of items across all pages
- `offset`: Current offset (number of items skipped)
- `limit`: Maximum number of items per page
- `has_more`: Boolean indicating if more pages exist

### Calculating Pages

```javascript
const totalPages = Math.ceil(total / limit);
const currentPage = Math.floor(offset / limit) + 1;
const nextOffset = offset + limit;
const prevOffset = Math.max(0, offset - limit);
```

### Example: Loading All Pages

```bash
#!/bin/bash
LIMIT=100
OFFSET=0
TOTAL=1  # Initialize

while [ $OFFSET -lt $TOTAL ]; do
  RESPONSE=$(curl -s "http://localhost:8000/api/contacts?limit=$LIMIT&offset=$OFFSET")
  TOTAL=$(echo $RESPONSE | jq -r '.total')
  CONTACTS=$(echo $RESPONSE | jq -r '.contacts')
  
  # Process contacts...
  echo "Fetched contacts $OFFSET to $((OFFSET + LIMIT))"
  
  OFFSET=$((OFFSET + LIMIT))
done
```

---

## Performance Optimization

### Caching Recommendations

**Client-Side Caching**:
- Cache contact lists for 5-10 minutes
- Invalidate cache after sync operations
- Use ETags for conditional requests (future feature)

**Server-Side Caching**:
- Database query results are indexed for fast retrieval
- Search results use SQLite FTS5 for performance

### Response Times

Typical response times (on average hardware):

- **List contacts**: 10-50ms
- **Get single contact**: 5-15ms
- **Search**: 10-50ms
- **Sync status**: 5-10ms
- **Full sync**: 5-300 seconds (depending on contact count)
- **Incremental sync**: 1-10 seconds

### Optimization Tips

1. **Use appropriate page sizes**: 20-50 items per page is optimal
2. **Leverage filtering**: Use `group` parameter to reduce result sets
3. **Implement lazy loading**: Load contacts as user scrolls
4. **Use incremental sync**: Much faster than full sync
5. **Cache search results**: Recent searches can be cached

---

## Security Considerations

### Authentication

- OAuth 2.0 tokens are stored encrypted on disk
- Refresh tokens enable long-term access without re-authentication
- Tokens are automatically refreshed when expired

### CORS

In development mode, CORS is enabled for:
- `http://localhost:5173` (Vite dev server)
- `http://localhost:8000` (API server)

In production, CORS is disabled. Configure your reverse proxy (nginx) to handle CORS if needed.

### Data Privacy

- Contact data is stored locally in SQLite database
- No data is sent to third parties (except Google People API)
- Deleted contacts are soft-deleted (marked as deleted, not removed)

### Best Practices

1. **Use HTTPS in production**: Encrypt all traffic
2. **Secure token storage**: Keep token files secure with appropriate permissions
3. **Regular credential rotation**: Revoke and re-authenticate periodically
4. **Monitor API usage**: Track sync operations and API calls
5. **Implement access control**: Use reverse proxy for authentication if needed

---

## Versioning

### Current Version

The API is currently at version `0.1.0`.

### Version Information

Check current version:
```bash
curl http://localhost:8000/health
```

### API Stability

The API is in **beta** status. Breaking changes may occur, but will be announced with version updates.

### Deprecation Policy

When endpoints are deprecated:
1. Announcement in release notes
2. Deprecation warnings in responses
3. Minimum 3 months before removal
4. Alternative endpoint provided

---

## Support and Troubleshooting

### Getting Help

- **Documentation**: See `/docs` directory
- **Interactive API docs**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health

### Common Issues

See the [Troubleshooting Guide](troubleshooting.md) for detailed solutions to common problems.

### Reporting Issues

When reporting issues, include:
- API endpoint and parameters
- Request and response (sanitized)
- Error messages from logs
- Application version (`/health` endpoint)

---

## Examples and Use Cases

### Example 1: Initial Setup and Sync

```bash
# 1. Check health
curl http://localhost:8000/health

# 2. Check auth status
curl http://localhost:8000/auth/status

# 3. If not authenticated, get OAuth URL
curl http://localhost:8000/auth/url

# 4. Visit OAuth URL in browser and complete authentication

# 5. Test Google connection
curl http://localhost:8000/api/test-connection

# 6. Perform initial sync
curl -X POST http://localhost:8000/api/sync

# 7. Check sync status
curl http://localhost:8000/api/sync/status

# 8. View contacts
curl http://localhost:8000/api/contacts?limit=10
```

### Example 2: Scheduled Incremental Sync

```bash
#!/bin/bash
# Run this script in cron every 30 minutes

# Check if authenticated
AUTH_STATUS=$(curl -s http://localhost:8000/auth/status | jq -r '.authenticated')

if [ "$AUTH_STATUS" != "true" ]; then
  echo "Not authenticated, skipping sync"
  exit 1
fi

# Trigger safe sync (won't run if already syncing)
RESPONSE=$(curl -s -X POST http://localhost:8000/api/sync/safe)
STATUS=$(echo $RESPONSE | jq -r '.status')

if [ "$STATUS" = "success" ]; then
  STATS=$(echo $RESPONSE | jq -r '.statistics')
  echo "Sync completed: $STATS"
elif [ "$STATUS" = "skipped" ]; then
  echo "Sync already in progress, skipped"
else
  echo "Sync failed: $RESPONSE"
  exit 1
fi
```

### Example 3: Contact Search Application

```javascript
// Frontend JavaScript example
class ContactSearchApp {
  constructor(apiBase = 'http://localhost:8000') {
    this.apiBase = apiBase;
    this.cache = new Map();
    this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
  }

  async searchContacts(query) {
    // Check cache
    const cacheKey = `search:${query}`;
    const cached = this.cache.get(cacheKey);
    
    if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
      return cached.data;
    }

    // Fetch from API
    const response = await fetch(
      `${this.apiBase}/api/search?q=${encodeURIComponent(query)}&limit=50`
    );
    
    if (!response.ok) {
      throw new Error(`Search failed: ${response.statusText}`);
    }

    const data = await response.json();
    
    // Cache results
    this.cache.set(cacheKey, {
      data,
      timestamp: Date.now()
    });

    return data;
  }

  async getContact(contactId) {
    const response = await fetch(
      `${this.apiBase}/api/contacts/${contactId}`
    );
    
    if (!response.ok) {
      throw new Error(`Failed to fetch contact: ${response.statusText}`);
    }

    return await response.json();
  }

  async syncContacts() {
    // Invalidate cache
    this.cache.clear();

    const response = await fetch(
      `${this.apiBase}/api/sync`,
      { method: 'POST' }
    );
    
    if (!response.ok) {
      throw new Error(`Sync failed: ${response.statusText}`);
    }

    return await response.json();
  }
}

// Usage
const app = new ContactSearchApp();

// Search
const results = await app.searchContacts('john');
console.log(`Found ${results.count} contacts in ${results.elapsed_ms}ms`);

// Get specific contact
const contact = await app.getContact('550e8400-e29b-41d4-a716-446655440000');
console.log(`Contact: ${contact.display_name}`);

// Trigger sync
const syncResult = await app.syncContacts();
console.log(`Sync completed: ${syncResult.message}`);
```

---

## Conclusion

This API documentation provides comprehensive information for integrating with the Google Contacts to Cisco IP Phone application. For more specific guides, see:

- [Setup Guide](setup.md) - Installation and initial configuration
- [Authentication Guide](authentication.md) - OAuth 2.0 setup details
- [Cisco Phone Setup](cisco-phone-setup.md) - Configuring Cisco IP Phones
- [Deployment Guide](deployment.md) - Production deployment
- [Troubleshooting Guide](troubleshooting.md) - Common issues and solutions

For interactive testing, visit:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
