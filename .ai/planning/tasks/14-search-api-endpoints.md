# Task 5.3: Search API Endpoints

## Overview

Create RESTful API endpoints for searching contacts by name and phone number. These endpoints will be used by both the Cisco phone search functionality and the web frontend.

## Priority

**P1 (High)** - Required for MVP

## Dependencies

- Task 1.1: Environment Setup
- Task 5.1: Phone Number Normalization
- Task 5.2: Search Service Implementation

## Objectives

1. Create search API endpoint (`GET /api/search`)
2. Support query parameters for name and phone
3. Return JSON responses with contact data
4. Add pagination support
5. Implement proper error handling
6. Add request validation
7. Include response time logging
8. Test all endpoints

## Technical Context

### API Design
- **Endpoint**: `GET /api/search`
- **Query Parameters**:
  - `q`: General search query (name or phone)
  - `name`: Search by name only
  - `phone`: Search by phone only
  - `limit`: Max results (default 50, max 100)
- **Response**: JSON array of contacts with match metadata

### Performance Target
- < 250ms response time for searches
- Efficient database queries
- Minimal data transfer

## Acceptance Criteria

- [ ] Search endpoint returns correct results
- [ ] Supports name and phone search
- [ ] Query parameters are validated
- [ ] Pagination works correctly
- [ ] Errors return appropriate HTTP codes
- [ ] Response time is logged
- [ ] JSON responses are properly formatted
- [ ] Tests cover all scenarios
- [ ] API documentation is generated

## Implementation Steps

### 1. Create Search Router

Create `google_contacts_cisco/api/search.py`:

```python
"""Search API endpoints."""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import time

from ..models import get_db
from ..services.search_service import get_search_service, SearchResult
from ..utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


class PhoneNumberSchema(BaseModel):
    """Phone number schema."""
    value: str
    display_value: str
    type: str
    primary: bool


class EmailAddressSchema(BaseModel):
    """Email address schema."""
    value: str
    type: str
    primary: bool


class SearchResultSchema(BaseModel):
    """Search result schema."""
    id: str
    display_name: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    phone_numbers: List[PhoneNumberSchema] = Field(default_factory=list)
    email_addresses: List[EmailAddressSchema] = Field(default_factory=list)
    match_type: str
    match_field: str
    
    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    """Search response schema."""
    results: List[SearchResultSchema]
    count: int
    query: str
    elapsed_ms: float


@router.get("", response_model=SearchResponse)
async def search_contacts(
    q: Optional[str] = Query(None, description="General search query (name or phone)"),
    name: Optional[str] = Query(None, description="Search by name only"),
    phone: Optional[str] = Query(None, description="Search by phone number only"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results to return"),
    db: Session = Depends(get_db)
):
    """Search contacts by name or phone number.
    
    Query parameters:
    - q: General search (searches both name and phone)
    - name: Search by name only
    - phone: Search by phone number only
    - limit: Maximum results (1-100, default 50)
    
    Only one of q, name, or phone should be provided.
    
    Returns:
        SearchResponse with matching contacts
    """
    start_time = time.time()
    
    try:
        # Validate: only one search parameter
        search_params = [q, name, phone]
        if sum(p is not None for p in search_params) != 1:
            raise HTTPException(
                status_code=400,
                detail="Exactly one of 'q', 'name', or 'phone' must be provided"
            )
        
        # Get search service
        search_service = get_search_service(db)
        
        # Perform search
        results: List[SearchResult] = []
        query_str = ""
        
        if q:
            query_str = q
            results = search_service.search(q, max_results=limit)
            logger.info(f"General search for '{q}': {len(results)} results")
        elif name:
            query_str = name
            results = search_service.search_by_name(name, max_results=limit)
            logger.info(f"Name search for '{name}': {len(results)} results")
        elif phone:
            query_str = phone
            results = search_service.search_by_phone(phone, max_results=limit)
            logger.info(f"Phone search for '{phone}': {len(results)} results")
        
        # Convert to response schema
        result_dicts = [r.to_dict() for r in results]
        
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"Search completed in {elapsed:.2f}ms")
        
        return SearchResponse(
            results=result_dicts,
            count=len(result_dicts),
            query=query_str,
            elapsed_ms=round(elapsed, 2)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error during search"
        )
```

### 2. Register Router in Main App

Update `google_contacts_cisco/main.py`:

```python
"""Main application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from google_contacts_cisco._version import __version__
from google_contacts_cisco.api import directory, search
from google_contacts_cisco.config import settings

app = FastAPI(
    title="Google Contacts Cisco Directory",
    description="Web application for syncing Google Contacts to Cisco IP Phones",
    version=__version__
)

# CORS middleware for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(directory.router)
app.include_router(search.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Google Contacts Cisco Directory",
        "version": __version__,
        "endpoints": {
            "directory": "/directory",
            "search": "/api/search",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
```

### 3. Update Configuration

Update `google_contacts_cisco/config.py` to add CORS settings:

```python
# CORS Settings
cors_origins: List[str] = Field(
    default=["http://localhost:3000", "http://localhost:8000"],
    description="Allowed CORS origins for web frontend"
)
```

### 4. Create Tests

Create `tests/test_search_api.py`:

```python
"""Test search API endpoints."""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from google_contacts_cisco.main import app
from google_contacts_cisco.models.contact import Contact
from google_contacts_cisco.models.phone_number import PhoneNumber


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_contacts(db_session):
    """Create sample contacts."""
    contacts = [
        Contact(
            id=uuid4(),
            resource_name="people/c1",
            display_name="John Doe",
            given_name="John",
            family_name="Doe"
        ),
        Contact(
            id=uuid4(),
            resource_name="people/c2",
            display_name="Jane Smith",
            given_name="Jane",
            family_name="Smith"
        ),
    ]
    
    # Add phone numbers
    contacts[0].phone_numbers.append(
        PhoneNumber(
            id=uuid4(),
            contact_id=contacts[0].id,
            value="+15551234567",
            display_value="(555) 123-4567",
            type="mobile",
            primary=True
        )
    )
    
    for contact in contacts:
        db_session.add(contact)
    
    db_session.commit()
    return contacts


def test_search_general_query(client, sample_contacts):
    """Test general search with q parameter."""
    response = client.get("/api/search?q=John")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "results" in data
    assert "count" in data
    assert "query" in data
    assert "elapsed_ms" in data
    
    assert data["count"] >= 1
    assert data["query"] == "John"
    
    # Check result structure
    result = data["results"][0]
    assert "id" in result
    assert "display_name" in result
    assert "phone_numbers" in result
    assert "match_type" in result


def test_search_by_name(client, sample_contacts):
    """Test search by name parameter."""
    response = client.get("/api/search?name=Jane")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["count"] >= 1
    assert "Jane" in data["results"][0]["display_name"]


def test_search_by_phone(client, sample_contacts):
    """Test search by phone parameter."""
    response = client.get("/api/search?phone=555-123-4567")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["count"] >= 1
    assert data["results"][0]["display_name"] == "John Doe"


def test_search_with_limit(client, sample_contacts):
    """Test search with limit parameter."""
    response = client.get("/api/search?q=o&limit=1")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["count"] <= 1


def test_search_no_parameters(client):
    """Test search without any parameters."""
    response = client.get("/api/search")
    
    assert response.status_code == 400
    assert "must be provided" in response.json()["detail"]


def test_search_multiple_parameters(client):
    """Test search with multiple parameters."""
    response = client.get("/api/search?q=John&name=Jane")
    
    assert response.status_code == 400
    assert "Exactly one" in response.json()["detail"]


def test_search_empty_query(client, sample_contacts):
    """Test search with empty query."""
    response = client.get("/api/search?q=")
    
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0


def test_search_no_results(client, sample_contacts):
    """Test search with no matching results."""
    response = client.get("/api/search?q=Nonexistent")
    
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert len(data["results"]) == 0


def test_search_limit_validation(client):
    """Test limit parameter validation."""
    # Too large
    response = client.get("/api/search?q=test&limit=1000")
    assert response.status_code == 422  # Validation error
    
    # Too small
    response = client.get("/api/search?q=test&limit=0")
    assert response.status_code == 422


def test_search_response_structure(client, sample_contacts):
    """Test complete response structure."""
    response = client.get("/api/search?q=John")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check top-level fields
    assert isinstance(data["results"], list)
    assert isinstance(data["count"], int)
    assert isinstance(data["query"], str)
    assert isinstance(data["elapsed_ms"], (int, float))
    
    # Check result fields
    if data["count"] > 0:
        result = data["results"][0]
        assert "id" in result
        assert "display_name" in result
        assert "phone_numbers" in result
        assert isinstance(result["phone_numbers"], list)
        assert "email_addresses" in result
        assert isinstance(result["email_addresses"], list)
        assert "match_type" in result
        assert "match_field" in result


def test_search_performance(client, sample_contacts):
    """Test search performance."""
    response = client.get("/api/search?q=John")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should complete in < 250ms
    assert data["elapsed_ms"] < 250


def test_search_case_insensitive(client, sample_contacts):
    """Test case-insensitive search."""
    response_upper = client.get("/api/search?q=JOHN")
    response_lower = client.get("/api/search?q=john")
    
    assert response_upper.status_code == 200
    assert response_lower.status_code == 200
    
    # Should return same results
    assert response_upper.json()["count"] == response_lower.json()["count"]


def test_search_special_characters(client, sample_contacts):
    """Test search with special characters."""
    # Should not cause errors
    response = client.get("/api/search?q=John%27s")
    assert response.status_code == 200
    
    response = client.get("/api/search?q=%26test")
    assert response.status_code == 200


def test_search_phone_formats(client, sample_contacts):
    """Test search with various phone formats."""
    formats = [
        "5551234567",
        "555-123-4567",
        "(555) 123-4567",
        "+1 555-123-4567",
    ]
    
    for phone_format in formats:
        response = client.get(f"/api/search?phone={phone_format}")
        assert response.status_code == 200
        # All should find the same contact
        data = response.json()
        if data["count"] > 0:
            assert "John Doe" in [r["display_name"] for r in data["results"]]
```

## Verification

After completing this task:

1. **Test Search Endpoint**:
   ```bash
   # General search
   curl "http://localhost:8000/api/search?q=John"
   
   # Name search
   curl "http://localhost:8000/api/search?name=John"
   
   # Phone search
   curl "http://localhost:8000/api/search?phone=555-123-4567"
   
   # With limit
   curl "http://localhost:8000/api/search?q=test&limit=10"
   ```

2. **Check API Documentation**:
   ```bash
   # Open browser to http://localhost:8000/docs
   # Interactive API documentation should show search endpoint
   ```

3. **Run Tests**:
   ```bash
   uv run pytest tests/test_search_api.py -v
   ```

4. **Test Performance**:
   ```bash
   # Use Apache Bench or similar
   ab -n 100 -c 10 "http://localhost:8000/api/search?q=test"
   ```

## Notes

- **Query Parameters**: Only one search parameter (q, name, or phone) allowed per request
- **Response Format**: JSON with results array and metadata
- **Performance Logging**: Response time included in response and logs
- **Error Handling**: 400 for bad requests, 500 for server errors
- **CORS**: Enabled for web frontend
- **Pagination**: Limit parameter (1-100, default 50)
- **Validation**: Pydantic models for request/response validation
- **Documentation**: Auto-generated via FastAPI

## Common Issues

1. **CORS Errors**: Add frontend origin to `cors_origins` config
2. **Slow Responses**: Check database indexes, optimize queries
3. **Validation Errors**: Check query parameter types and ranges
4. **Empty Results**: Verify contacts are synced and not deleted
5. **Performance Issues**: Monitor with `elapsed_ms` in response

## API Documentation

The search endpoint will be automatically documented at `/docs` (Swagger UI) and `/redoc` (ReDoc).

Example response:
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
          "value": "+15551234567",
          "display_value": "(555) 123-4567",
          "type": "mobile",
          "primary": true
        }
      ],
      "email_addresses": [],
      "match_type": "exact",
      "match_field": "display_name"
    }
  ],
  "count": 1,
  "query": "John Doe",
  "elapsed_ms": 45.23
}
```

## Related Documentation

- FastAPI: https://fastapi.tiangolo.com/
- Pydantic: https://docs.pydantic.dev/
- OpenAPI: https://swagger.io/specification/

## Estimated Time

3-4 hours

