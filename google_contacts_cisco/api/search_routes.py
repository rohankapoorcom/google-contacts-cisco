"""Search API routes.

This module provides FastAPI endpoints for searching contacts:
- /api/contacts/search - Full-text search by name and phone
- /api/contacts/search/by-name - Search by name only
- /api/contacts/search/by-phone - Search by phone number only
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..models import get_db
from ..services.search_service import get_search_service
from ..utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


# Response Models


class PhoneNumberResponse(BaseModel):
    """Phone number response schema."""

    id: UUID
    value: str
    display_value: str
    type: Optional[str] = None
    primary: bool = False

    model_config = {"from_attributes": True}


class ContactResponse(BaseModel):
    """Contact response schema."""

    id: UUID
    resource_name: str
    display_name: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    phone_numbers: List[PhoneNumberResponse] = []

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    """Search results response schema."""

    results: List[ContactResponse]
    total_count: int
    limit: int
    offset: int
    has_more: bool


# Endpoints


@router.get("/search", response_model=SearchResponse)
async def search_contacts(
    q: str = Query(
        ...,
        description="Search query (name or phone number)",
        min_length=1,
        max_length=100,
    ),
    limit: int = Query(
        50,
        description="Maximum number of results",
        ge=1,
        le=100,
    ),
    offset: int = Query(
        0,
        description="Number of results to skip for pagination",
        ge=0,
    ),
    include_phone_search: bool = Query(
        True,
        description="Include phone number in search",
    ),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """Search contacts by name and/or phone number.

    Performs a full-text search across contact names (display_name, given_name,
    family_name) and optionally phone numbers. Returns paginated results.

    Args:
        q: Search query string
        limit: Maximum number of results to return (1-100)
        offset: Number of results to skip for pagination
        include_phone_search: Whether to search phone numbers (default: True)
        db: Database session (injected)

    Returns:
        SearchResponse with matching contacts and pagination info

    Raises:
        HTTPException: If search query is invalid or search fails
    """
    try:
        search_service = get_search_service(db)

        # Perform search
        results = search_service.search_contacts(
            query=q,
            limit=limit,
            offset=offset,
            include_phone_search=include_phone_search,
        )

        # Get total count for pagination
        total_count = search_service.count_search_results(
            query=q,
            include_phone_search=include_phone_search,
        )

        # Convert to response models
        contact_responses = [
            ContactResponse.model_validate(contact) for contact in results
        ]

        logger.info(
            "Search completed: query='%s', found=%d, total=%d",
            q,
            len(contact_responses),
            total_count,
        )

        return SearchResponse(
            results=contact_responses,
            total_count=total_count,
            limit=limit,
            offset=offset,
            has_more=(offset + len(contact_responses)) < total_count,
        )

    except Exception as e:
        logger.error("Search failed for query '%s': %s", q, e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}",
        ) from e


@router.get("/search/by-name", response_model=SearchResponse)
async def search_contacts_by_name(
    q: str = Query(
        ...,
        description="Search query (name only)",
        min_length=1,
        max_length=100,
    ),
    limit: int = Query(
        50,
        description="Maximum number of results",
        ge=1,
        le=100,
    ),
    offset: int = Query(
        0,
        description="Number of results to skip for pagination",
        ge=0,
    ),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """Search contacts by name only (no phone search).

    Searches across display_name, given_name, and family_name fields only.

    Args:
        q: Search query string
        limit: Maximum number of results to return (1-100)
        offset: Number of results to skip for pagination
        db: Database session (injected)

    Returns:
        SearchResponse with matching contacts and pagination info

    Raises:
        HTTPException: If search query is invalid or search fails
    """
    try:
        search_service = get_search_service(db)

        # Perform name-only search
        results = search_service.search_by_name(
            query=q,
            limit=limit,
            offset=offset,
        )

        # Get total count
        total_count = search_service.count_search_results(
            query=q,
            include_phone_search=False,
        )

        # Convert to response models
        contact_responses = [
            ContactResponse.model_validate(contact) for contact in results
        ]

        logger.info(
            "Name search completed: query='%s', found=%d",
            q,
            len(contact_responses),
        )

        return SearchResponse(
            results=contact_responses,
            total_count=total_count,
            limit=limit,
            offset=offset,
            has_more=(offset + len(contact_responses)) < total_count,
        )

    except Exception as e:
        logger.error("Name search failed for query '%s': %s", q, e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Name search failed: {str(e)}",
        ) from e


@router.get("/search/by-phone", response_model=SearchResponse)
async def search_contacts_by_phone(
    q: str = Query(
        ...,
        description="Phone number to search",
        min_length=4,
        max_length=20,
    ),
    limit: int = Query(
        50,
        description="Maximum number of results",
        ge=1,
        le=100,
    ),
    offset: int = Query(
        0,
        description="Number of results to skip for pagination",
        ge=0,
    ),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """Search contacts by phone number.

    Searches phone numbers using normalization and suffix matching.
    Supports various phone formats (with/without country code, dashes, spaces).

    Args:
        q: Phone number to search for
        limit: Maximum number of results to return (1-100)
        offset: Number of results to skip for pagination
        db: Database session (injected)

    Returns:
        SearchResponse with matching contacts and pagination info

    Raises:
        HTTPException: If phone number is invalid or search fails
    """
    try:
        search_service = get_search_service(db)

        # Perform phone search
        results = search_service.search_by_phone(
            phone_number=q,
            limit=limit,
            offset=offset,
        )

        # For phone search, we don't have a separate count method,
        # so we'll use the length of results as the count
        # This is a simplified approach; for production, you might want
        # to implement a count method in the service
        total_count = len(results)

        # Convert to response models
        contact_responses = [
            ContactResponse.model_validate(contact) for contact in results
        ]

        logger.info(
            "Phone search completed: query='%s', found=%d",
            q,
            len(contact_responses),
        )

        return SearchResponse(
            results=contact_responses,
            total_count=total_count,
            limit=limit,
            offset=offset,
            has_more=False,  # Simplified: no pagination for phone search
        )

    except Exception as e:
        logger.error("Phone search failed for query '%s': %s", q, e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Phone search failed: {str(e)}",
        ) from e
