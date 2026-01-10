"""Search API routes.

This module provides FastAPI endpoints for searching contacts:
- /api/contacts/search - Full-text search by name and phone
- /api/contacts/{contact_id} - Get single contact by ID
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import get_db
from ..models.contact import Contact
from ..repositories.contact_repository import ContactRepository
from ..services.search_service import SearchService, get_search_service
from ..utils.datetime_utils import format_timestamp_for_display
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


class ContactDetailResponse(BaseModel):
    """Detailed contact response schema."""

    id: UUID
    resource_name: str
    display_name: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    phone_numbers: List[PhoneNumberResponse] = []
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


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


@router.get("/{contact_id}", response_model=ContactDetailResponse)
async def get_contact(
    contact_id: UUID,
    db: Session = Depends(get_db),
) -> ContactDetailResponse:
    """Get a single contact by ID.

    Retrieves full contact details including all phone numbers.

    Args:
        contact_id: UUID of the contact
        db: Database session (injected)

    Returns:
        ContactDetailResponse with complete contact information

    Raises:
        HTTPException: If contact not found or retrieval fails
    """
    try:
        repository = ContactRepository(db)
        contact = repository.get_by_id(contact_id)

        if contact is None:
            logger.warning("Contact not found: %s", contact_id)
            raise HTTPException(
                status_code=404,
                detail=f"Contact with ID {contact_id} not found",
            )

        if contact.deleted:
            logger.warning("Attempted to access deleted contact: %s", contact_id)
            raise HTTPException(
                status_code=404,
                detail=f"Contact with ID {contact_id} not found",
            )

        logger.info("Retrieved contact: %s (%s)", contact.display_name, contact_id)

        # Convert timestamps to ISO format strings with configured timezone
        settings = get_settings()
        return ContactDetailResponse(
            id=contact.id,
            resource_name=contact.resource_name,
            display_name=contact.display_name,
            given_name=contact.given_name,
            family_name=contact.family_name,
            phone_numbers=[
                PhoneNumberResponse.model_validate(pn) for pn in contact.phone_numbers
            ],
            created_at=format_timestamp_for_display(contact.created_at, settings.timezone),
            updated_at=format_timestamp_for_display(contact.updated_at, settings.timezone),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get contact %s: %s", contact_id, e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve contact: {str(e)}",
        ) from e


@router.get("", response_model=SearchResponse)
async def list_contacts(
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
    """List all contacts (paginated).

    Returns all non-deleted contacts in alphabetical order by display name.

    Args:
        limit: Maximum number of results to return (1-100)
        offset: Number of results to skip for pagination
        db: Database session (injected)

    Returns:
        SearchResponse with contacts and pagination info

    Raises:
        HTTPException: If listing fails
    """
    try:
        repository = ContactRepository(db)

        # Get paginated contacts
        contacts = repository.list_contacts(
            limit=limit,
            offset=offset,
            include_deleted=False,
        )

        # Get total count
        total_count = repository.count_contacts(include_deleted=False)

        # Convert to response models
        contact_responses = [
            ContactResponse.model_validate(contact) for contact in contacts
        ]

        logger.info(
            "Listed contacts: returned=%d, total=%d",
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
        logger.error("Failed to list contacts: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list contacts: {str(e)}",
        ) from e
