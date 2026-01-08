"""Search service for contacts.

This module provides full-text search functionality for contacts
by name and phone number with pagination support.
"""

from typing import List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from ..models.contact import Contact
from ..models.phone_number import PhoneNumber
from ..utils.logger import get_logger
from ..utils.phone_utils import PhoneNumberNormalizer

logger = get_logger(__name__)


class SearchService:
    """Service for searching contacts.

    Provides full-text search capabilities for finding contacts
    by name (display_name, given_name, family_name) and phone number.
    """

    def __init__(
        self,
        db: Session,
        phone_normalizer: Optional[PhoneNumberNormalizer] = None,
    ):
        """Initialize search service.

        Args:
            db: Database session
            phone_normalizer: Phone number normalizer (defaults to US)
        """
        self.db = db
        self.phone_normalizer = phone_normalizer or PhoneNumberNormalizer("US")

    def search_contacts(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
        include_phone_search: bool = True,
    ) -> List[Contact]:
        """Search contacts by name and optionally phone number.

        Searches across display_name, given_name, and family_name fields
        using case-insensitive matching. Optionally also searches phone numbers.

        Args:
            query: Search query string
            limit: Maximum number of results (default: 50)
            offset: Number of results to skip (default: 0)
            include_phone_search: Include phone number search (default: True)

        Returns:
            List of matching Contact objects with phone_numbers loaded
        """
        if not query or not query.strip():
            logger.warning("Empty search query provided")
            return []

        # Sanitize query
        search_term = query.strip()
        logger.info("Searching contacts for: %s", search_term)

        # Build name search conditions
        name_conditions = self._build_name_search_conditions(search_term)

        # Build phone search conditions if enabled
        phone_conditions = []
        if include_phone_search:
            phone_conditions = self._build_phone_search_conditions(search_term)

        # Combine conditions with OR
        if phone_conditions:
            all_conditions = or_(*name_conditions, *phone_conditions)
        else:
            all_conditions = or_(*name_conditions)

        # Execute query with eager loading of phone numbers
        stmt = (
            select(Contact)
            .options(joinedload(Contact.phone_numbers))
            .where(~Contact.deleted)
            .where(all_conditions)
            .distinct()
            .order_by(Contact.display_name)
            .limit(limit)
            .offset(offset)
        )

        results = self.db.execute(stmt).unique().scalars().all()
        logger.info("Found %d contacts matching: %s", len(results), search_term)
        return list(results)

    def search_by_name(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Contact]:
        """Search contacts by name only (no phone number search).

        Args:
            query: Search query string
            limit: Maximum number of results (default: 50)
            offset: Number of results to skip (default: 0)

        Returns:
            List of matching Contact objects
        """
        return self.search_contacts(
            query=query,
            limit=limit,
            offset=offset,
            include_phone_search=False,
        )

    def search_by_phone(
        self,
        phone_number: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Contact]:
        """Search contacts by phone number.

        Uses phone number normalization to match various formats.

        Args:
            phone_number: Phone number to search for
            limit: Maximum number of results (default: 50)
            offset: Number of results to skip (default: 0)

        Returns:
            List of matching Contact objects with phone_numbers loaded
        """
        if not phone_number or not phone_number.strip():
            logger.warning("Empty phone number search query")
            return []

        logger.info("Searching contacts by phone: %s", phone_number)

        # Normalize search input
        normalized = self.phone_normalizer.normalize_for_search(phone_number)

        # Build conditions for both normalized and suffix matching
        conditions = []

        if normalized:
            # Exact match on normalized value
            conditions.append(PhoneNumber.value == normalized)
            # Suffix match on last 7+ digits
            digits_only = ''.join(c for c in normalized if c.isdigit())
            if len(digits_only) >= 7:
                conditions.append(PhoneNumber.value.like(f"%{digits_only[-7:]}"))

        # Fallback: digit-only suffix match
        digits = ''.join(c for c in phone_number if c.isdigit())
        if digits and len(digits) >= 7:
            conditions.append(PhoneNumber.value.like(f"%{digits[-7:]}"))

        if not conditions:
            logger.warning(
                "Could not create search conditions for phone: %s", phone_number
            )
            return []

        # Execute query
        stmt = (
            select(Contact)
            .join(Contact.phone_numbers)
            .options(joinedload(Contact.phone_numbers))
            .where(~Contact.deleted)
            .where(or_(*conditions))
            .distinct()
            .order_by(Contact.display_name)
            .limit(limit)
            .offset(offset)
        )

        results = self.db.execute(stmt).unique().scalars().all()
        logger.info("Found %d contacts with phone: %s", len(results), phone_number)
        return list(results)

    def count_search_results(
        self,
        query: str,
        include_phone_search: bool = True,
    ) -> int:
        """Count total number of search results.

        Args:
            query: Search query string
            include_phone_search: Include phone number search (default: True)

        Returns:
            Total count of matching contacts
        """
        if not query or not query.strip():
            return 0

        search_term = query.strip()

        # Build name search conditions
        name_conditions = self._build_name_search_conditions(search_term)

        # Build phone search conditions if enabled
        phone_conditions = []
        if include_phone_search:
            phone_conditions = self._build_phone_search_conditions(search_term)

        # Combine conditions
        if phone_conditions:
            all_conditions = or_(*name_conditions, *phone_conditions)
        else:
            all_conditions = or_(*name_conditions)

        # Count distinct contacts
        stmt = (
            select(func.count(func.distinct(Contact.id)))
            .select_from(Contact)
            .where(~Contact.deleted)
            .where(all_conditions)
        )

        if phone_conditions:
            stmt = stmt.outerjoin(Contact.phone_numbers)

        count = self.db.execute(stmt).scalar()
        return count or 0

    def _build_name_search_conditions(self, search_term: str) -> List:
        """Build search conditions for name fields.

        Args:
            search_term: Search query

        Returns:
            List of SQLAlchemy conditions
        """
        # Case-insensitive pattern matching
        pattern = f"%{search_term}%"
        return [
            Contact.display_name.ilike(pattern),
            Contact.given_name.ilike(pattern),
            Contact.family_name.ilike(pattern),
        ]

    def _build_phone_search_conditions(self, search_term: str) -> List:
        """Build search conditions for phone number fields.

        Args:
            search_term: Search query

        Returns:
            List of SQLAlchemy conditions
        """
        conditions = []

        # Try to normalize the search term
        normalized = self.phone_normalizer.normalize_for_search(search_term)

        if normalized:
            # Exact match on normalized value
            conditions.append(PhoneNumber.value == normalized)

            # Suffix matching on digits
            digits_only = ''.join(c for c in normalized if c.isdigit())
            if len(digits_only) >= 7:
                suffix_pattern = f"%{digits_only[-7:]}"
                conditions.append(PhoneNumber.value.like(suffix_pattern))

        # Fallback: digit-only matching for partial numbers
        digits = ''.join(c for c in search_term if c.isdigit())
        if digits and len(digits) >= 4:
            digit_pattern = f"%{digits}%"
            conditions.append(PhoneNumber.value.like(digit_pattern))
            # Also try display_value
            conditions.append(PhoneNumber.display_value.like(digit_pattern))

        return conditions


def get_search_service(
    db: Session,
    phone_normalizer: Optional[PhoneNumberNormalizer] = None,
) -> SearchService:
    """Get search service instance.

    Args:
        db: Database session
        phone_normalizer: Optional phone normalizer

    Returns:
        SearchService instance
    """
    return SearchService(db, phone_normalizer)
