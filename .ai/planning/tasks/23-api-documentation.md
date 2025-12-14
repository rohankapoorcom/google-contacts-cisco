# Task 8.1: API Documentation

## Overview

Create comprehensive API documentation using FastAPI's automatic OpenAPI generation, add detailed descriptions, create usage guides, and provide Postman collections for testing and integration.

## Priority

**P1 (High)** - Required for maintainability and external integration

## Dependencies

- All API implementation tasks (1-19)

## Objectives

1. Enhance OpenAPI schema with descriptions
2. Document all request/response models
3. Add usage examples to endpoints
4. Document error responses
5. Create Postman collection
6. Write setup and deployment guides
7. Document Cisco phone configuration
8. Create troubleshooting guide

## Technical Context

### FastAPI Auto-Documentation
FastAPI automatically generates:
- **OpenAPI 3.0** schema
- **Swagger UI** at `/docs`
- **ReDoc** at `/redoc`
- **JSON Schema** for all models

### Documentation Structure
```
docs/
├── README.md              # Main documentation
├── API.md                 # API reference
├── SETUP.md              # Setup guide
├── DEPLOYMENT.md         # Deployment guide
├── CISCO_PHONE_SETUP.md  # Cisco configuration
├── OAUTH_SETUP.md        # OAuth configuration
├── TROUBLESHOOTING.md    # Common issues
└── postman/
    └── collection.json   # Postman collection
```

## Acceptance Criteria

- [ ] All endpoints have descriptions
- [ ] Request/response schemas documented
- [ ] Usage examples provided
- [ ] Error codes documented
- [ ] Postman collection created
- [ ] Setup guide complete
- [ ] Cisco phone guide complete
- [ ] OAuth guide complete
- [ ] Troubleshooting guide complete
- [ ] OpenAPI schema validates

## Implementation Steps

### 1. Enhance API Endpoint Documentation

Update `google_contacts_cisco/api/contacts.py` with detailed docs:

```python
@router.get("", response_model=ContactListResponse)
async def list_contacts(
    limit: int = Query(
        50,
        ge=1,
        le=100,
        description="Maximum number of contacts to return (1-100)"
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of contacts to skip for pagination"
    ),
    sort: str = Query(
        "name",
        regex="^(name|recent)$",
        description="Sort order: 'name' for alphabetical, 'recent' for recently updated"
    ),
    group: Optional[str] = Query(
        None,
        max_length=1,
        description="Filter by first letter (A-Z) or '#' for numbers/special characters"
    ),
    db: Session = Depends(get_db)
):
    """
    List all contacts with pagination, filtering, and sorting.
    
    This endpoint returns a paginated list of contacts from the database.
    Use the `offset` and `limit` parameters to implement pagination in your client.
    
    **Filtering:**
    - Use `group` parameter to filter by first letter of contact name
    - Example: `?group=A` returns only contacts starting with 'A'
    - Use `group=#` for contacts starting with numbers or special characters
    
    **Sorting:**
    - `sort=name`: Alphabetical by display name (default)
    - `sort=recent`: Most recently updated first
    
    **Performance:**
    - Response time: <100ms for typical queries
    - Maximum 100 contacts per request
    
    **Example Usage:**
    ```
    GET /api/contacts?limit=20&offset=0&sort=name&group=A
    ```
    
    **Response includes:**
    - `contacts`: Array of contact objects
    - `total`: Total number of contacts (across all pages)
    - `offset`: Current offset
    - `limit`: Current limit
    - `has_more`: Boolean indicating if more pages exist
    """
    # Implementation...
```

### 2. Document Response Models

Add descriptions to Pydantic models:

```python
class ContactSchema(BaseModel):
    """
    Contact information schema.
    
    Represents a single contact with all associated data including
    phone numbers and email addresses.
    """
    
    id: str = Field(..., description="Unique UUID for the contact")
    display_name: str = Field(..., description="Full display name")
    given_name: Optional[str] = Field(None, description="First name")
    family_name: Optional[str] = Field(None, description="Last name")
    phone_numbers: List[PhoneNumberSchema] = Field(
        default_factory=list,
        description="List of phone numbers associated with this contact"
    )
    email_addresses: List[EmailAddressSchema] = Field(
        default_factory=list,
        description="List of email addresses associated with this contact"
    )
    updated_at: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp of last update"
    )
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "display_name": "John Doe",
                "given_name": "John",
                "family_name": "Doe",
                "phone_numbers": [{
                    "id": "660e8400-e29b-41d4-a716-446655440000",
                    "value": "+15551234567",
                    "display_value": "(555) 123-4567",
                    "type": "mobile",
                    "primary": True
                }],
                "email_addresses": [{
                    "id": "770e8400-e29b-41d4-a716-446655440000",
                    "value": "john.doe@example.com",
                    "type": "personal",
                    "primary": True
                }],
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
```

### 3. Create Main README

Create `README.md`:

```markdown
# Google Contacts Cisco Directory

A web application that syncs Google Contacts and provides a directory interface for Cisco IP Phones, along with a modern web interface for contact management and search.

## Features

- 🔄 **Automatic Sync**: Sync contacts from Google Contacts API
- 📱 **Cisco Phone Support**: XML directory format for Cisco IP Phones
- 🔍 **Fast Search**: Full-text search by name or phone number
- 🎨 **Modern UI**: Vue 3 web interface with responsive design
- 🔐 **OAuth Security**: Secure Google authentication
- 📊 **Sync Management**: Manual and automatic sync with progress tracking

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+ (for frontend)
- Google Cloud Project with People API enabled
- OAuth 2.0 credentials

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/google-contacts-cisco.git
   cd google-contacts-cisco
   ```

2. **Install backend dependencies**:
   ```bash
   uv sync
   ```

3. **Install frontend dependencies**:
   ```bash
   cd frontend
   npm install
   ```

4. **Configure application**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run database migrations**:
   ```bash
   uv run alembic upgrade head
   ```

6. **Start the application**:
   ```bash
   # Terminal 1: Backend
   uv run python -m google_contacts_cisco.main
   
   # Terminal 2: Frontend (development)
   cd frontend && npm run dev
   ```

7. **Access the application**:
   - Web Interface: http://localhost:5173
   - API Docs: http://localhost:8000/docs
   - Cisco Directory: http://localhost:8000/directory

## Documentation

- [API Documentation](docs/API.md)
- [Setup Guide](docs/SETUP.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Cisco Phone Setup](docs/CISCO_PHONE_SETUP.md)
- [OAuth Configuration](docs/OAUTH_SETUP.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## API Endpoints

### Contacts
- `GET /api/contacts` - List contacts
- `GET /api/contacts/{id}` - Get single contact
- `GET /api/contacts/stats` - Get contact statistics

### Search
- `GET /api/search?q={query}` - Search contacts

### Sync
- `GET /api/sync/status` - Get sync status
- `POST /api/sync/trigger` - Trigger manual sync
- `GET /api/sync/info` - Get sync information

### Cisco Directory
- `GET /directory` - Main directory menu
- `GET /directory/groups/{group}` - Group contacts
- `GET /directory/contacts/{id}` - Contact phone numbers

### OAuth
- `GET /auth/google` - Initiate OAuth flow
- `GET /auth/callback` - OAuth callback
- `GET /auth/status` - Check auth status

## Technology Stack

- **Backend**: FastAPI, SQLAlchemy, SQLite
- **Frontend**: Vue 3, Vite, TypeScript, Tailwind CSS
- **Testing**: pytest, Playwright
- **Package Management**: uv
- **API**: Google People API v1

## Development

### Running Tests

```bash
# Unit tests
uv run pytest tests/unit -v

# Integration tests
uv run pytest tests/integration -v

# E2E tests
uv run pytest tests/e2e -v

# Coverage report
uv run pytest --cov=google_contacts_cisco --cov-report=html
```

### Code Quality

```bash
# Format code
uv run black google_contacts_cisco

# Type checking
uv run mypy google_contacts_cisco

# Linting
uv run ruff google_contacts_cisco
```

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or contributions, please visit:
https://github.com/your-org/google-contacts-cisco/issues
```

### 4. Create API Documentation

Create `docs/API.md`:

```markdown
# API Documentation

Complete API reference for the Google Contacts Cisco Directory application.

## Base URL

- Development: `http://localhost:8000`
- Production: `https://your-domain.com`

## Authentication

Most endpoints are publicly accessible. OAuth authentication is required for:
- Syncing contacts from Google
- Managing OAuth tokens

## Endpoints

### Contacts API

#### List Contacts

```http
GET /api/contacts
```

**Query Parameters:**

| Parameter | Type   | Default | Description                  |
|-----------|--------|---------|------------------------------|
| limit     | int    | 50      | Max contacts (1-100)         |
| offset    | int    | 0       | Skip N contacts              |
| sort      | string | name    | Sort by: name, recent        |
| group     | string | null    | Filter by letter (A-Z or #)  |

**Example Request:**

```bash
curl "http://localhost:8000/api/contacts?limit=10&sort=name&group=A"
```

**Example Response:**

```json
{
  "contacts": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "display_name": "Alice Anderson",
      "given_name": "Alice",
      "family_name": "Anderson",
      "phone_numbers": [
        {
          "id": "660e8400-e29b-41d4-a716-446655440000",
          "value": "+15551234567",
          "display_value": "(555) 123-4567",
          "type": "mobile",
          "primary": true
        }
      ],
      "email_addresses": [
        {
          "id": "770e8400-e29b-41d4-a716-446655440000",
          "value": "alice@example.com",
          "type": "personal",
          "primary": true
        }
      ],
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 150,
  "offset": 0,
  "limit": 10,
  "has_more": true
}
```

**Error Responses:**

| Status Code | Description                        |
|-------------|------------------------------------|
| 400         | Invalid query parameters           |
| 422         | Validation error (limit too large) |
| 500         | Internal server error              |

---

#### Get Single Contact

```http
GET /api/contacts/{id}
```

**Path Parameters:**

| Parameter | Type | Description           |
|-----------|------|-----------------------|
| id        | UUID | Contact UUID          |

**Example Request:**

```bash
curl "http://localhost:8000/api/contacts/550e8400-e29b-41d4-a716-446655440000"
```

**Error Responses:**

| Status Code | Description                  |
|-------------|------------------------------|
| 400         | Invalid UUID format          |
| 404         | Contact not found            |
| 500         | Internal server error        |

---

### Search API

#### Search Contacts

```http
GET /api/search
```

**Query Parameters:**

| Parameter | Type   | Required | Description                    |
|-----------|--------|----------|--------------------------------|
| q         | string | *        | Search query (name or phone)   |
| name      | string | *        | Search by name only            |
| phone     | string | *        | Search by phone only           |
| limit     | int    | No       | Max results (1-100, default 50)|

*Note: Exactly one of q, name, or phone must be provided*

**Example Request:**

```bash
curl "http://localhost:8000/api/search?q=John"
```

**Example Response:**

```json
{
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "display_name": "John Doe",
      "given_name": "John",
      "family_name": "Doe",
      "phone_numbers": [...],
      "email_addresses": [...],
      "match_type": "exact",
      "match_field": "display_name"
    }
  ],
  "count": 1,
  "query": "John",
  "elapsed_ms": 45.23
}
```

**Match Types:**

- `exact`: Exact name match
- `prefix`: Name starts with query
- `substring`: Name contains query
- `phone`: Phone number match

**Performance:**

- Target: < 250ms response time
- Actual response time included in `elapsed_ms`

---

### Cisco Directory XML API

#### Main Directory

```http
GET /directory
```

Returns Cisco IPPhoneMenu XML with letter groups (A-Z, #).

**Response Format:** XML (`text/xml; charset=utf-8`)

**Example Response:**

```xml
<?xml version='1.0' encoding='UTF-8'?>
<CiscoIPPhoneMenu>
  <Title>Contacts</Title>
  <MenuItem>
    <Name>A</Name>
    <URL>http://localhost:8000/directory/groups/A</URL>
  </MenuItem>
  <SoftKeyItem>
    <Name>Exit</Name>
    <Position>1</Position>
    <URL>Init:Directories</URL>
  </SoftKeyItem>
</CiscoIPPhoneMenu>
```

---

## Rate Limiting

Currently no rate limiting is implemented. Recommended limits for production:
- 100 requests per minute per IP
- 1000 requests per hour per IP

## Versioning

API version is included in the root endpoint response.

```bash
curl http://localhost:8000/
{
  "name": "Google Contacts Cisco Directory",
  "version": "0.1.0",
  "endpoints": {...}
}
```

## Error Handling

All errors return JSON (except Cisco XML endpoints which return XML):

```json
{
  "detail": "Error message description"
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad Request (invalid parameters)
- `401`: Unauthorized (OAuth required)
- `404`: Not Found
- `409`: Conflict (e.g., sync already running)
- `422`: Validation Error (Pydantic)
- `500`: Internal Server Error
```

### 5. Create Postman Collection

Create `docs/postman/collection.json` (abbreviated):

```json
{
  "info": {
    "name": "Google Contacts Cisco Directory",
    "description": "API collection for testing and integration",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Contacts",
      "item": [
        {
          "name": "List Contacts",
          "request": {
            "method": "GET",
            "header": [],
            "url": {
              "raw": "{{baseUrl}}/api/contacts?limit=10&offset=0&sort=name",
              "host": ["{{baseUrl}}"],
              "path": ["api", "contacts"],
              "query": [
                {"key": "limit", "value": "10"},
                {"key": "offset", "value": "0"},
                {"key": "sort", "value": "name"}
              ]
            }
          }
        }
      ]
    }
  ],
  "variable": [
    {
      "key": "baseUrl",
      "value": "http://localhost:8000",
      "type": "string"
    }
  ]
}
```

### 6. Create Cisco Phone Setup Guide

Create `docs/CISCO_PHONE_SETUP.md`:

```markdown
# Cisco IP Phone Setup Guide

Configure your Cisco IP Phone to access the Google Contacts directory.

## Prerequisites

- Cisco IP Phone (7940, 7960, 7970, 8841, etc.)
- Network access to the application server
- Application running and accessible

## Configuration Steps

### Option 1: Phone Web Interface

1. **Access Phone Web Interface**:
   - Find your phone's IP address (Press Settings → Network Configuration)
   - Open browser: `http://PHONE_IP_ADDRESS`

2. **Configure Directory**:
   - Navigate to: Directory → XML Service
   - Add new service:
     - Name: `Google Contacts`
     - URL: `http://YOUR_SERVER:8000/directory`
   - Save configuration

3. **Test**:
   - Press Directory button on phone
   - Select "Google Contacts"
   - Navigate through directory

### Option 2: CUCM Configuration

1. **Create XML Service**:
   - CUCM → Device → Device Settings → Phone Services
   - Add New → XML Service
   - Service Name: `Google Contacts`
   - Service URL: `http://YOUR_SERVER:8000/directory`

2. **Subscribe Phones**:
   - Device → Phone
   - Select phone → Subscribe/Unsubscribe Services
   - Add "Google Contacts"

3. **Push Configuration**:
   - Reset phone or wait for next check-in

## Directory Navigation

### Main Menu
- Shows letter groups: A, B, C, ..., Z, #
- Use keypad to quick-jump to letter
- Soft Keys:
  - Exit: Return to phone menu
  - View: Select group
  - Help: Show help text

### Group Menu (e.g., "A")
- Shows all contacts starting with that letter
- Scroll through list
- Soft Keys:
  - Exit: Return to main directory
  - View: Show contact details
  - Help: Show help for this group

### Contact Details
- Shows all phone numbers for contact
- Format: `Type (Primary)` - `Number`
- Soft Keys:
  - Exit: Return to main directory
  - Back: Return to group list
  - Call: Dial selected number

## Troubleshooting

### "Service Not Available"
- Check server is running: `curl http://YOUR_SERVER:8000/directory`
- Check network connectivity from phone to server
- Verify URL is correct (no trailing slash)

### "No Contacts Found"
- Ensure contacts are synced: Open web interface → Sync
- Check OAuth is configured
- Verify database has contacts

### Directory Loads Slowly
- Check server response time: `curl -w "@curl-format.txt" http://YOUR_SERVER:8000/directory`
- Target: < 100ms response time
- Consider adding caching

### Phone Shows XML Instead of Menu
- Verify Content-Type is `text/xml; charset=utf-8`
- Check XML format matches Cisco specification
- Test XML in browser developer tools

## Phone-Specific Notes

### 7940/7960 Series
- Supports basic CiscoIPPhoneMenu and CiscoIPPhoneDirectory
- 4x12 character display (limited)
- 4 softkeys

### 7970 Series
- Color display
- 8 softkeys
- Better navigation

### 8800 Series
- High resolution color display
- Touch screen support
- Enhanced XML support

## Network Requirements

- HTTP access from phone VLAN to application server
- Port 8000 (default) or configured port
- Optional: HTTPS for production (recommended)
- Latency: < 100ms recommended

## Security Considerations

### Production Deployment
1. Use HTTPS (TLS certificate)
2. Restrict access by IP/VLAN
3. Consider authentication (optional)
4. Monitor access logs

### Example HAProxy Configuration
```haproxy
frontend cisco_directory
    bind *:443 ssl crt /etc/ssl/certs/cert.pem
    acl is_directory path_beg /directory
    use_backend directory_backend if is_directory

backend directory_backend
    server app1 localhost:8000 check
```
```

## Verification

After completing this task:

1. **Check OpenAPI Docs**:
   - Visit http://localhost:8000/docs
   - Verify all endpoints are documented
   - Test endpoints from Swagger UI

2. **Check ReDoc**:
   - Visit http://localhost:8000/redoc
   - Verify clean documentation layout

3. **Test Postman Collection**:
   - Import `docs/postman/collection.json`
   - Run all requests
   - Verify responses

4. **Review Documentation**:
   - Check all docs/ files are complete
   - Verify links work
   - Test code examples

## Estimated Time

3-4 hours


