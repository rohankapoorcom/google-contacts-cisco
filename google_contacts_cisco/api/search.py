"""API routes for contact search operations.

This module provides FastAPI endpoints for searching contacts:
- /api/search - General search (name or phone)
- /api/search/name - Search by name only
- /api/search/phone - Search by phone number only
"""

import logging
import time
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ..models import get_db
from ..models.contact import Contact
from ..services.search_service import SearchService, get_search_service
from ..utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


class PhoneNumberSchema(BaseModel):
    """Phone number schema for API responses."""

    model_config = ConfigDict(from_attributes=True)

    value: str
    display_value: str
    type: str
    primary: bool


class ContactSearchResult(BaseModel):
    """Contact search result schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    resource_name: str
    display_name: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    organization: Optional[str] = None
    job_title: Optional[str] = None
    phone_numbers: List[PhoneNumberSchema] = Field(default_factory=list)


class SearchResponse(BaseModel):
    """Search response schema."""

    results: List[ContactSearchResult]
    count: int
    total_count: int
    query: str
    elapsed_ms: float
    limit: int
    offset: int


class SearchErrorResponse(BaseModel):
    """Error response for search operations."""

    error: str
    detail: str


def _contact_to_result(contact: Contact) -> ContactSearchResult:
    """Convert Contact model to ContactSearchResult schema.

    Args:
        contact: Contact model instance

    Returns:
        ContactSearchResult with all contact details
    """
    return ContactSearchResult(
        id=str(contact.id),
        resource_name=contact.resource_name,
        display_name=contact.display_name,
        given_name=contact.given_name,
        family_name=contact.family_name,
        organization=contact.organization,
        job_title=contact.job_title,
        phone_numbers=[
            PhoneNumberSchema(
                value=phone.value,
                display_value=phone.display_value,
                type=phone.type,
                primary=phone.primary,
            )
            for phone in contact.phone_numbers
        ],
    )


@router.get("", response_model=SearchResponse)
async def search_contacts(
    q: str = Query(..., min_length=1, description="Search query (name or phone)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """Search contacts by name or phone number.

    Performs a general search across contact names and phone numbers.
    The search automatically detects whether the query looks like a phone number
    and adjusts the search strategy accordingly.

    Query parameters:
    - q: Search query (required, min length 1)
    - limit: Maximum results (1-100, default 50)
    - offset: Pagination offset (default 0)

    Returns:
        SearchResponse with matching contacts and metadata

    Raises:
        HTTPException 422: If query parameters are invalid
        HTTPException 500: If search fails due to server error
    """
    start_time = time.time()

    try:
        # Get search service
        search_service: SearchService = get_search_service(db)

        # Perform search
        logger.info("General search for '%s' (limit=%d, offset=%d)", q, limit, offset)
        results = search_service.search_contacts(
            query=q,
            limit=limit,
            offset=offset,
        )

        # Get total count for pagination
        total_count = search_service.count_search_results(query=q)

        # Convert to response schema
        result_schemas = [_contact_to_result(contact) for contact in results]

        elapsed = (time.time() - start_time) * 1000
        logger.info("Search completed in %.2fms (%d results)", elapsed, len(results))

        return SearchResponse(
            results=result_schemas,
            count=len(result_schemas),
            total_count=total_count,
            query=q,
            elapsed_ms=round(elapsed, 2),
            limit=limit,
            offset=offset,
        )

    except ValueError as e:
        logger.error("Invalid search parameters: %s", str(e))
        raise HTTPException(
            status_code=422,
            detail=f"Invalid search parameters: {str(e)}",
        )
    except Exception as e:
        logger.exception("Search failed with unexpected error")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}",
        )


@router.get("/name", response_model=SearchResponse)
async def search_by_name(
    q: str = Query(..., min_length=1, description="Name to search for"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """Search contacts by name only.

    Searches across display_name, given_name, and family_name fields
    using case-insensitive matching. Does not search phone numbers.

    Query parameters:
    - q: Name to search for (required, min length 1)
    - limit: Maximum results (1-100, default 50)
    - offset: Pagination offset (default 0)

    Returns:
        SearchResponse with matching contacts and metadata

    Raises:
        HTTPException 422: If query parameters are invalid
        HTTPException 500: If search fails due to server error
    """
    start_time = time.time()

    try:
        # Get search service
        search_service: SearchService = get_search_service(db)

        # Perform name-only search
        logger.info("Name search for '%s' (limit=%d, offset=%d)", q, limit, offset)
        results = search_service.search_by_name(
            query=q,
            limit=limit,
            offset=offset,
        )

        # Get total count for pagination
        total_count = search_service.count_search_results(
            query=q,
            include_phone_search=False,
        )

        # Convert to response schema
        result_schemas = [_contact_to_result(contact) for contact in results]

        elapsed = (time.time() - start_time) * 1000
        logger.info("Name search completed in %.2fms (%d results)", elapsed, len(results))

        return SearchResponse(
            results=result_schemas,
            count=len(result_schemas),
            total_count=total_count,
            query=q,
            elapsed_ms=round(elapsed, 2),
            limit=limit,
            offset=offset,
        )

    except ValueError as e:
        logger.error("Invalid search parameters: %s", str(e))
        raise HTTPException(
            status_code=422,
            detail=f"Invalid search parameters: {str(e)}",
        )
    except Exception as e:
        logger.exception("Name search failed with unexpected error")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}",
        )


@router.get("/phone", response_model=SearchResponse)
async def search_by_phone(
    q: str = Query(..., min_length=1, description="Phone number to search for"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """Search contacts by phone number only.

    Searches phone numbers using normalization to match various formats.
    Supports partial matching on the last 7+ digits.

    Query parameters:
    - q: Phone number to search for (required, min length 1)
    - limit: Maximum results (1-100, default 50)
    - offset: Pagination offset (default 0)

    Returns:
        SearchResponse with matching contacts and metadata

    Raises:
        HTTPException 422: If query parameters are invalid
        HTTPException 500: If search fails due to server error
    """
    start_time = time.time()

    try:
        # Get search service
        search_service: SearchService = get_search_service(db)

        # Perform phone-only search
        logger.info("Phone search for '%s' (limit=%d, offset=%d)", q, limit, offset)
        results = search_service.search_by_phone(
            phone_number=q,
            limit=limit,
            offset=offset,
        )

        # Note: Count not implemented for phone-only search
        # Would require duplicating the complex phone search logic
        total_count = len(results)

        # Convert to response schema
        result_schemas = [_contact_to_result(contact) for contact in results]

        elapsed = (time.time() - start_time) * 1000
        logger.info("Phone search completed in %.2fms (%d results)", elapsed, len(results))

        return SearchResponse(
            results=result_schemas,
            count=len(result_schemas),
            total_count=total_count,
            query=q,
            elapsed_ms=round(elapsed, 2),
            limit=limit,
            offset=offset,
        )

    except ValueError as e:
        logger.error("Invalid search parameters: %s", str(e))
        raise HTTPException(
            status_code=422,
            detail=f"Invalid search parameters: {str(e)}",
        )
    except Exception as e:
        logger.exception("Phone search failed with unexpected error")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}",
        )


@router.get("/health")
async def search_health() -> dict[str, Any]:
    """Health check for search endpoints.

    Returns:
        Dictionary with status and version information
    """
    return {
        "status": "healthy",
        "service": "search",
        "endpoints": [
            "/api/search",
            "/api/search/name",
            "/api/search/phone",
        ],
    }
