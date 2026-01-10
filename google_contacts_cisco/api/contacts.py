"""API routes for contact management and search.

This module provides FastAPI endpoints for:
- /api/contacts - List contacts with pagination, sorting, and filtering
- /api/contacts/{id} - Get a single contact
- /api/contacts/stats - Get contact statistics
- /api/search - Search contacts by name or phone number
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..models import get_db
from ..repositories.contact_repository import ContactRepository
from ..schemas.contact import (
    ContactListResponse,
    ContactResponse,
    EmailAddressResponse,
    PhoneNumberResponse,
)
from ..services.search_service import SearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["contacts"])


class ContactStatsResponse(BaseModel):
    """Response model for contact statistics."""

    total_contacts: int
    contacts_with_phone: int
    contacts_with_email: int
    total_phone_numbers: int
    total_emails: int


class SearchResultItem(BaseModel):
    """Individual search result with match metadata."""

    id: str
    display_name: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    phone_numbers: list[PhoneNumberResponse]
    email_addresses: list[EmailAddressResponse]
    match_type: str  # 'exact', 'prefix', 'substring', 'phone'
    match_field: str  # field that matched


class SearchResultsResponse(BaseModel):
    """Response model for search results."""

    results: list[SearchResultItem]
    count: int
    query: str
    elapsed_ms: float


@router.get("/contacts", response_model=ContactListResponse)
async def get_contacts(
    limit: int = Query(
        default=30, ge=1, le=100, description="Number of contacts per page"
    ),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    sort: Optional[str] = Query(
        default="name", description="Sort order: 'name' or 'recent'"
    ),
    group: Optional[str] = Query(
        default=None, description="Filter by first letter (A-Z, #)"
    ),
    db: Session = Depends(get_db),
) -> ContactListResponse:
    """Get a paginated list of contacts.

    Returns contacts with support for:
    - Pagination via limit and offset
    - Sorting by name or recently updated
    - Filtering by first letter of display name

    Args:
        limit: Maximum number of contacts to return (1-100, default 30)
        offset: Number of contacts to skip for pagination (default 0)
        sort: Sort order - 'name' (alphabetical) or 'recent' (by updated_at)
        group: Filter by first letter - A-Z for letters, '#' for numbers/special chars
        db: Database session

    Returns:
        ContactListResponse with contacts and pagination metadata
    """
    import time

    start_time = time.time()

    repo = ContactRepository(db)

    try:
        # Determine sort order
        sort_by_recent = sort == "recent"

        # Get contacts
        if group:
            # Filter by first letter
            if group == "#":
                # Get contacts starting with numbers or special characters
                contacts = repo.get_contacts_by_letter_group(
                    "#", limit=limit, offset=offset, sort_by_recent=sort_by_recent
                )
                total = repo.count_contacts_by_letter_group("#")
            elif len(group) == 1 and group.isalpha():
                # Get contacts starting with specific letter
                contacts = repo.get_contacts_by_letter_group(
                    group.upper(),
                    limit=limit,
                    offset=offset,
                    sort_by_recent=sort_by_recent,
                )
                total = repo.count_contacts_by_letter_group(group.upper())
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Group must be a single letter (A-Z) or '#' for numbers",
                )
        else:
            # Get all contacts
            contacts = repo.get_contacts(
                limit=limit, offset=offset, sort_by_recent=sort_by_recent
            )
            total = repo.count_contacts()

        # Convert to response models
        contact_responses = [ContactResponse.from_orm(c) for c in contacts]

        elapsed_ms = (time.time() - start_time) * 1000

        logger.debug(
            "Returned %d contacts (offset=%d, limit=%d, group=%s, sort=%s) in %.2fms",
            len(contacts),
            offset,
            limit,
            group,
            sort,
            elapsed_ms,
        )

        return ContactListResponse(
            contacts=contact_responses,
            total=total,
            offset=offset,
            limit=limit,
            has_more=offset + len(contacts) < total,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching contacts")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch contacts: {str(e)}"
        )


@router.get("/contacts/stats", response_model=ContactStatsResponse)
async def get_contact_stats(
    db: Session = Depends(get_db),
) -> ContactStatsResponse:
    """Get contact statistics.

    Returns aggregate statistics about contacts in the database,
    including counts of contacts with phone numbers, emails, etc.

    Args:
        db: Database session

    Returns:
        ContactStatsResponse with statistics
    """
    repo = ContactRepository(db)

    try:
        stats = repo.get_contact_statistics()
        return ContactStatsResponse(**stats)

    except Exception as e:
        logger.exception("Error fetching contact statistics")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch statistics: {str(e)}"
        )


@router.get("/contacts/{contact_id}", response_model=ContactResponse)
async def get_contact_by_id(
    contact_id: UUID,
    db: Session = Depends(get_db),
) -> ContactResponse:
    """Get a single contact by ID.

    Args:
        contact_id: UUID of the contact
        db: Database session

    Returns:
        ContactResponse with full contact details

    Raises:
        HTTPException 404: If contact not found
        HTTPException 500: If database error occurs
    """
    repo = ContactRepository(db)

    try:
        contact = repo.get_contact_by_id(str(contact_id))

        if not contact:
            raise HTTPException(
                status_code=404, detail=f"Contact with ID {contact_id} not found"
            )

        if contact.deleted:
            raise HTTPException(
                status_code=404, detail=f"Contact with ID {contact_id} not found"
            )

        return ContactResponse.from_orm(contact)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching contact %s", contact_id)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch contact: {str(e)}"
        )


@router.get("/search", response_model=SearchResultsResponse)
async def search_contacts(
    q: str = Query(..., description="Search query (name or phone number)"),
    limit: int = Query(
        default=50, ge=1, le=100, description="Maximum results to return"
    ),
    db: Session = Depends(get_db),
) -> SearchResultsResponse:
    """Search contacts by name or phone number.

    Performs a real-time search across contact names and phone numbers
    with the following matching strategies:
    - Exact match: Full name or phone number match
    - Prefix match: Name starts with query
    - Substring match: Name contains query
    - Phone match: Phone number contains query digits

    Args:
        q: Search query string
        limit: Maximum number of results to return (1-100, default 50)
        db: Database session

    Returns:
        SearchResultsResponse with matched contacts and metadata

    Raises:
        HTTPException 400: If query is empty or too short
        HTTPException 500: If search fails
    """
    import time

    start_time = time.time()

    # Validate query
    query = q.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    if len(query) < 2:
        raise HTTPException(
            status_code=400, detail="Search query must be at least 2 characters"
        )

    try:
        search_service = SearchService(db)
        results = search_service.search(query, limit=limit)

        # Convert to response format
        search_results = []
        for result in results:
            search_results.append(
                SearchResultItem(
                    id=str(result.contact.id),
                    display_name=result.contact.display_name,  # type: ignore[arg-type]
                    given_name=result.contact.given_name,  # type: ignore[arg-type]
                    family_name=result.contact.family_name,  # type: ignore[arg-type]
                    phone_numbers=[
                        PhoneNumberResponse.model_validate(p)
                        for p in result.contact.phone_numbers
                    ],
                    email_addresses=(
                        [
                            EmailAddressResponse.model_validate(e)
                            for e in result.contact.email_addresses
                        ]
                        if hasattr(result.contact, "email_addresses")
                        else []
                    ),
                    match_type=result.match_type,
                    match_field=result.match_field,
                )
            )

        elapsed_ms = (time.time() - start_time) * 1000

        logger.info(
            "Search for '%s' returned %d results in %.2fms",
            query,
            len(results),
            elapsed_ms,
        )

        return SearchResultsResponse(
            results=search_results,
            count=len(results),
            query=query,
            elapsed_ms=elapsed_ms,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error performing search for query: %s", query)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
