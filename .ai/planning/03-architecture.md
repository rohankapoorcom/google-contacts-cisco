# Architecture & Design

## System Architecture

### High-Level Architecture

```
┌─────────────────┐      ┌──────────────┐
│  Cisco IP Phone │      │ Web Browser  │
└────────┬────────┘      └──────┬───────┘
         │ HTTP/HTTPS            │ HTTP/HTTPS
         │ (XML Directory)        │ (Web Frontend)
         │                        │
         ▼                        ▼
┌─────────────────────────────────────┐
│      Web Application                 │
│  ┌───────────────────────────────┐  │
│  │   Web Server (FastAPI)        │  │
│  └───────────┬───────────────────┘  │
│              │                       │
│  ┌───────────▼───────────────────┐  │
│  │   API Layer                    │  │
│  │  - XML Directory Endpoint      │  │
│  │  - Search API Endpoint         │  │
│  │  - Sync Management Endpoint    │  │
│  │  - Web Frontend Routes         │  │
│  │  - OAuth Setup Routes          │  │
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
│         SQLite Database             │
│  - Contacts Table                   │
│  - Phone Numbers Table              │
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
- **Cisco IP Phone Directory Endpoints**:
  - `GET /directory` - Main directory menu with group options
  - `GET /directory/groups/<group>` - Contact list for a specific group
  - `GET /directory/contacts/<id>` - Individual contact phone numbers
  - `GET /directory/help` - Help information (optional)
- **Search and API Endpoints**:
  - `GET /api/search?phone=<number>` - Phone number search
  - `GET /api/contacts` - API endpoint for frontend search (full-text)
  - `POST /api/sync` - Trigger manual sync
  - `GET /api/status` - Application and sync status
- **Web Frontend Endpoints**:
  - `GET /` - Web frontend home page
  - `GET /auth/google` - Initiate OAuth flow
  - `GET /auth/callback` - OAuth callback handler

### 3. Business Logic Layer (Application Services)

The Business Logic Layer contains application services that implement the core business rules and orchestrate operations. These services coordinate between the API layer and the data access layer.

#### Contact Service
- **Responsibilities**:
  - Retrieve contacts from database
  - Format contacts for display
  - Handle contact data transformations
  - Provide contact data to various consumers (XML formatter, web frontend, API)

#### Sync Service
- **Responsibilities**:
  - Manage sync operations (full and incremental)
  - Handle sync token management
  - Coordinate with Google API client
  - Update local database
  - Track sync status and errors

#### XML Formatter
- **Responsibilities**:
  - Generate main directory menu (`CiscoIPPhoneMenu`) with group options
  - Generate directory groups menu (`CiscoIPPhoneMenu`) filtered by group
  - Generate individual contact directory (`CiscoIPPhoneDirectory`) with phone numbers
  - Map contact names to groups (2ABC, 3DEF, etc.)
  - Handle pagination if needed for large groups
  - Format names and phone numbers appropriately
  - Escape special characters and XML entities
  - Generate XML structure compliant with Cisco IP Phone specifications
  - Build RESTful URLs for menu items (`/directory/groups/<group>`, `/directory/contacts/<id>`)

#### Search Service
- **Responsibilities**:
  - Normalize phone number queries
  - Perform full-text search on contact names
  - Search database for matching contacts by phone number
  - Return formatted search results
  - Handle search result ranking and relevance

### 4. Data Access Layer

#### Contact Repository
- **Responsibilities**:
  - CRUD operations for contacts
  - Query contacts by various criteria
  - Manage contact relationships

#### Sync State Repository
- **Responsibilities**:
  - Store and retrieve sync tokens (tokens returned by Google API for incremental sync)
  - Track last sync timestamp
  - Manage sync status (idle, syncing, error)
  - Store sync error messages
  - The SyncState entity represents the current state of synchronization with Google Contacts, including the token needed for incremental updates

### 5. Web Frontend

#### Frontend Interface
- **Responsibilities**:
  - Provide beautiful, user-friendly interface for viewing contacts
  - Display contact directory with search capabilities
  - Handle OAuth 2.0 setup flow
  - Display sync status and manage sync operations
  - Full-text search interface for names and phone numbers

#### OAuth Setup Interface
- **Responsibilities**:
  - Initiate Google OAuth 2.0 flow
  - Handle OAuth callback
  - Display OAuth setup status
  - Manage token refresh using Google's web OAuth flow

### 6. Google Contacts Integration

#### OAuth Client
- **Responsibilities**:
  - Handle OAuth 2.0 flow
  - Manage authorization tokens
  - Refresh expired tokens using Google's web OAuth mechanism

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

### Cisco IP Phone Directory Request Flow

#### Main Directory Menu
```
1. Cisco IP Phone requests /directory
2. Web Server routes to main directory endpoint
3. XML Formatter generates CiscoIPPhoneMenu with index menu items
4. Response sent to phone
```

#### Directory Groups Request
```
1. User selects group (e.g., "2ABC") on phone
2. Phone requests /directory/groups/2ABC
3. Web Server routes to groups endpoint
4. Contact Service filters contacts by group
5. XML Formatter generates CiscoIPPhoneMenu with contact names
6. Response sent to phone
```

#### Individual Contact Request
```
1. User selects contact on phone
2. Phone requests /directory/contacts/<id>
3. Web Server routes to contacts endpoint
4. Contact Service retrieves contact by id
5. XML Formatter generates CiscoIPPhoneDirectory with phone numbers
6. Response sent to phone
```

### Search Request Flow
```
1. Client requests /api/search?phone=1234567890
2. Web Server routes to Search API endpoint
3. Search Service normalizes phone number
4. Search Service queries database
5. Results formatted and returned as JSON
```

### Web Frontend Request Flow
```
1. User accesses web frontend (GET /)
2. Web Server serves frontend HTML
3. Frontend makes API calls to /api/contacts for search
4. Search Service performs full-text search
5. Results displayed in web interface
```

### OAuth Setup Flow
```
1. User accesses OAuth setup page
2. User clicks "Connect Google Account"
3. Application redirects to Google OAuth consent screen
4. User grants permissions
5. Google redirects back with authorization code
6. Application exchanges code for tokens
7. Tokens stored securely
8. User redirected to main interface
```

## Security Architecture

### Authentication
- OAuth 2.0 for Google API access
- Token storage: Secure file-based storage
- Token refresh: Automatic with retry logic using Google's web OAuth flow

### API Security
- API endpoints protected with authentication (API keys or OAuth)
- Rate limiting to prevent abuse
- Input validation and sanitization

### Data Security
- HTTPS for all external communication
- Secure credential management (environment variables, secrets manager)
- SQLite database file permissions restricted

## Deployment Architecture

### Development Environment
- Local Python environment
- SQLite database
- Direct Google API access

### Production Environment
- Web server (Uvicorn with FastAPI)
- SQLite database
- Reverse proxy (Nginx) - optional
- SSL/TLS certificates
- Environment-based configuration

## Scalability Considerations

### Single-User Design
- Application designed for single-user use
- SQLite database sufficient for up to 10,000 contacts
- No horizontal scaling required

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

