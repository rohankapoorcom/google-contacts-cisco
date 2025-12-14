# Architecture & Design

## System Architecture

### High-Level Architecture

```
┌─────────────────┐
│  Cisco IP Phone │
└────────┬────────┘
         │ HTTP/HTTPS
         │ (XML Directory)
         ▼
┌─────────────────────────────────────┐
│      Web Application                 │
│  ┌───────────────────────────────┐  │
│  │   Web Server (Flask/FastAPI)  │  │
│  └───────────┬───────────────────┘  │
│              │                       │
│  ┌───────────▼───────────────────┐  │
│  │   API Layer                    │  │
│  │  - XML Directory Endpoint      │  │
│  │  - Search API Endpoint         │  │
│  │  - Sync Management Endpoint    │  │
│  └───────────┬───────────────────┘  │
│              │                       │
│  ┌───────────▼───────────────────┐  │
│  │   Business Logic Layer         │  │
│  │  - Contact Service             │  │
│  │  - Sync Service                │  │
│  │  - XML Formatter               │  │
│  │  - Search Service              │  │
│  └───────────┬───────────────────┘  │
│              │                       │
│  ┌───────────▼───────────────────┐  │
│  │   Data Access Layer            │  │
│  │  - Contact Repository          │  │
│  │  - Sync State Repository       │  │
│  └───────────┬───────────────────┘  │
└──────────────┼───────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│         Database                    │
│  - Contacts Table                   │
│  - Sync State Table                 │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│   Google People API                 │
│  (External Service)                 │
└─────────────────────────────────────┘
         ▲
         │ OAuth 2.0
         │ API Calls
         │
┌────────┴────────────────────────────┐
│   Google Contacts Integration       │
│  - OAuth Client                     │
│  - API Client                       │
│  - Token Manager                    │
└─────────────────────────────────────┘
```

## Component Design

### 1. Web Server Layer
- **Purpose**: Handle HTTP requests and responses
- **Responsibilities**:
  - Route requests to appropriate handlers
  - Manage request/response lifecycle
  - Handle authentication/authorization
  - Error handling and logging

### 2. API Layer
- **Endpoints**:
  - `GET /directory.xml` - Cisco IP Phone XML directory
  - `GET /api/search?phone=<number>` - Phone number search
  - `POST /api/sync` - Trigger manual sync
  - `GET /api/status` - Application and sync status

### 3. Business Logic Layer

#### Contact Service
- **Responsibilities**:
  - Retrieve contacts from database
  - Format contacts for display
  - Handle contact data transformations

#### Sync Service
- **Responsibilities**:
  - Manage sync operations (full and incremental)
  - Handle sync token management
  - Coordinate with Google API client
  - Update local database

#### XML Formatter
- **Responsibilities**:
  - Convert contact data to Cisco XML format
  - Handle pagination if needed
  - Format names and phone numbers appropriately

#### Search Service
- **Responsibilities**:
  - Normalize phone number queries
  - Search database for matching contacts
  - Return formatted search results

### 4. Data Access Layer

#### Contact Repository
- **Responsibilities**:
  - CRUD operations for contacts
  - Query contacts by various criteria
  - Manage contact relationships

#### Sync State Repository
- **Responsibilities**:
  - Store and retrieve sync tokens
  - Track last sync timestamp
  - Manage sync status

### 5. Google Contacts Integration

#### OAuth Client
- **Responsibilities**:
  - Handle OAuth 2.0 flow
  - Manage authorization tokens
  - Refresh expired tokens

#### API Client
- **Responsibilities**:
  - Make requests to Google People API
  - Handle pagination
  - Implement retry logic
  - Respect rate limits

#### Token Manager
- **Responsibilities**:
  - Store tokens securely
  - Refresh tokens automatically
  - Handle token expiration

## Data Model

### Contact Entity
```
Contact:
  - id: UUID (primary key)
  - resource_name: string (Google resource name)
  - etag: string (for conflict detection)
  - given_name: string
  - family_name: string
  - display_name: string
  - phone_numbers: array of PhoneNumber
  - email_addresses: array of EmailAddress
  - organization: string (optional)
  - job_title: string (optional)
  - created_at: timestamp
  - updated_at: timestamp
  - deleted: boolean
  - synced_at: timestamp
```

### PhoneNumber Entity
```
PhoneNumber:
  - id: UUID (primary key)
  - contact_id: UUID (foreign key)
  - value: string (normalized phone number)
  - display_value: string (original format)
  - type: string (work, mobile, home, etc.)
  - primary: boolean
```

### SyncState Entity
```
SyncState:
  - id: UUID (primary key)
  - sync_token: string (nullable)
  - last_sync_at: timestamp
  - sync_status: enum (idle, syncing, error)
  - error_message: string (nullable)
```

## Data Flow

### Initial Sync Flow
```
1. User authenticates with Google
2. Application receives OAuth token
3. Sync Service initiates full sync
4. API Client requests all contacts (paginated)
5. For each page:
   a. Parse contact data
   b. Store in database
   c. Request next page if available
6. Store sync token from final response
7. Mark sync as complete
```

### Incremental Sync Flow
```
1. Scheduled/Manual trigger
2. Sync Service retrieves stored sync token
3. API Client requests changes using sync token
4. Process response:
   a. For each contact:
      - If deleted: mark as deleted in DB
      - If modified: update in DB
      - If new: insert into DB
5. Update sync token
6. Handle 410 error (token expired) by doing full sync
```

### XML Directory Request Flow
```
1. Cisco IP Phone requests /directory.xml
2. Web Server routes to XML Directory endpoint
3. Contact Service retrieves all active contacts
4. XML Formatter converts contacts to Cisco XML
5. Response sent to phone
```

### Search Request Flow
```
1. Client requests /api/search?phone=1234567890
2. Web Server routes to Search API endpoint
3. Search Service normalizes phone number
4. Search Service queries database
5. Results formatted and returned as JSON
```

## Security Architecture

### Authentication
- OAuth 2.0 for Google API access
- Token storage: Encrypted at rest
- Token refresh: Automatic with retry logic

### API Security
- API endpoints protected with authentication (API keys or OAuth)
- Rate limiting to prevent abuse
- Input validation and sanitization

### Data Security
- HTTPS for all external communication
- Encrypted database storage
- Secure credential management (environment variables, secrets manager)

## Deployment Architecture

### Development Environment
- Local Python environment
- SQLite database
- Direct Google API access

### Production Environment
- Web server (Gunicorn/uWSGI with Flask/FastAPI)
- PostgreSQL or similar database
- Reverse proxy (Nginx)
- SSL/TLS certificates
- Environment-based configuration

## Scalability Considerations

### Horizontal Scaling
- Stateless application design
- Shared database
- Load balancer for multiple instances

### Performance Optimization
- Database indexing (especially on phone numbers)
- Caching of frequently accessed data
- Connection pooling
- Async operations where possible

## Error Handling Strategy

### API Errors
- Retry with exponential backoff
- Log errors for monitoring
- Return appropriate HTTP status codes
- User-friendly error messages

### Sync Errors
- Handle 410 (sync token expired) by full sync
- Handle rate limits with backoff
- Queue failed operations for retry
- Alert on persistent failures

