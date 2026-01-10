"""Contact repository for database operations.

This module provides data access operations for Contact and PhoneNumber entities,
including CRUD operations, upsert logic, and query methods.
"""

import re
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.contact import Contact
from ..models.phone_number import PhoneNumber
from ..schemas.contact import ContactCreateSchema
from ..utils.logger import get_logger
from ..utils.phone_utils import get_phone_normalizer

logger = get_logger(__name__)


class ContactRepository:
    """Repository for contact database operations.

    Provides methods for creating, reading, updating, and querying contacts
    in the database. Handles the relationship between contacts and their
    phone numbers.
    """

    def __init__(self, db: Session):
        """Initialize repository.

        Args:
            db: Database session for all operations
        """
        self.db = db

    def create_contact(self, contact_data: ContactCreateSchema) -> Contact:
        """Create a new contact with phone numbers.

        Args:
            contact_data: Contact data to create

        Returns:
            Created contact entity with populated ID
        """
        contact = Contact(
            resource_name=contact_data.resource_name,
            etag=contact_data.etag,
            given_name=contact_data.given_name,
            family_name=contact_data.family_name,
            display_name=contact_data.display_name,
            organization=contact_data.organization,
            job_title=contact_data.job_title,
            deleted=contact_data.deleted,
            synced_at=datetime.now(timezone.utc),
        )

        self.db.add(contact)
        self.db.flush()  # Get contact ID

        # Add phone numbers
        for phone_data in contact_data.phone_numbers:
            phone = PhoneNumber(
                contact_id=contact.id,
                value=phone_data.value,
                display_value=phone_data.display_value,
                type=phone_data.type,
                primary=phone_data.primary,
            )
            self.db.add(phone)

        logger.debug("Created contact: %s (%s)", contact.display_name, contact.id)
        return contact

    def get_by_id(self, contact_id: UUID) -> Optional[Contact]:
        """Get contact by ID.

        Args:
            contact_id: Contact UUID

        Returns:
            Contact or None if not found
        """
        return self.db.query(Contact).filter(Contact.id == contact_id).first()

    def get_by_resource_name(self, resource_name: str) -> Optional[Contact]:
        """Get contact by Google resource name.

        Args:
            resource_name: Google resource name (e.g., 'people/c12345')

        Returns:
            Contact or None if not found
        """
        return (
            self.db.query(Contact)
            .filter(Contact.resource_name == resource_name)
            .first()
        )

    def upsert_contact(self, contact_data: ContactCreateSchema) -> Contact:
        """Insert or update contact.

        If a contact with the same resource_name exists, it will be updated.
        Otherwise, a new contact will be created.

        Args:
            contact_data: Contact data to insert or update

        Returns:
            Created or updated contact entity
        """
        existing = self.get_by_resource_name(contact_data.resource_name)

        if existing:
            return self._update_contact(existing, contact_data)
        else:
            return self.create_contact(contact_data)

    def _update_contact(
        self, existing: Contact, contact_data: ContactCreateSchema
    ) -> Contact:
        """Update an existing contact.

        Args:
            existing: Existing contact to update
            contact_data: New contact data

        Returns:
            Updated contact entity
        """
        # Update contact fields
        existing.etag = contact_data.etag
        existing.given_name = contact_data.given_name
        existing.family_name = contact_data.family_name
        existing.display_name = contact_data.display_name
        existing.organization = contact_data.organization
        existing.job_title = contact_data.job_title
        existing.deleted = contact_data.deleted
        existing.synced_at = datetime.now(timezone.utc)
        existing.updated_at = datetime.now(timezone.utc)

        # Delete old phone numbers
        self.db.query(PhoneNumber).filter(
            PhoneNumber.contact_id == existing.id
        ).delete()

        # Add new phone numbers
        for phone_data in contact_data.phone_numbers:
            phone = PhoneNumber(
                contact_id=existing.id,
                value=phone_data.value,
                display_value=phone_data.display_value,
                type=phone_data.type,
                primary=phone_data.primary,
            )
            self.db.add(phone)

        logger.debug(
            "Updated contact: %s (%s)", existing.display_name, existing.id
        )
        return existing

    def mark_as_deleted(self, resource_name: str) -> Optional[Contact]:
        """Mark a contact as deleted (soft delete).

        Args:
            resource_name: Google resource name

        Returns:
            Updated contact or None if not found
        """
        contact = self.get_by_resource_name(resource_name)
        if contact:
            contact.deleted = True
            contact.synced_at = datetime.now(timezone.utc)
            contact.updated_at = datetime.now(timezone.utc)
            logger.debug("Marked contact as deleted: %s", resource_name)
            return contact
        return None

    def get_all_active(self) -> List[Contact]:
        """Get all non-deleted contacts.

        Returns:
            List of active contacts
        """
        return (
            self.db.query(Contact)
            .filter(Contact.deleted == False)  # noqa: E712
            .all()
        )

    def get_all_active_with_phones(self) -> List[Contact]:
        """Get all non-deleted contacts that have at least one phone number.

        Returns:
            List of active contacts with phone numbers
        """
        return (
            self.db.query(Contact)
            .join(Contact.phone_numbers)
            .filter(Contact.deleted.is_(False))
            .distinct()
            .all()
        )

    def get_all(self) -> List[Contact]:
        """Get all contacts including deleted.

        Returns:
            List of all contacts
        """
        return self.db.query(Contact).all()

    def count_all(self) -> int:
        """Count all contacts.

        Returns:
            Total contact count
        """
        return self.db.query(Contact).count()

    def count_active(self) -> int:
        """Count active (non-deleted) contacts.

        Returns:
            Active contact count
        """
        return (
            self.db.query(Contact)
            .filter(Contact.deleted == False)  # noqa: E712
            .count()
        )

    def delete_all(self) -> int:
        """Delete all contacts (hard delete).

        Used for testing or resetting the database.

        Returns:
            Number of contacts deleted
        """
        # First delete all phone numbers
        self.db.query(PhoneNumber).delete()
        # Then delete all contacts
        count = self.db.query(Contact).delete()
        logger.info("Deleted all contacts: %d", count)
        return count

    def search_by_phone(self, phone_number: str) -> List[Contact]:
        """Search contacts by phone number.

        Normalizes the input phone number and searches against normalized
        values in the database. Falls back to digit-only suffix matching
        if normalization fails.

        Args:
            phone_number: Phone number to search (any format)

        Returns:
            List of matching contacts (non-deleted only)
        """
        normalizer = get_phone_normalizer()

        # Normalize search input
        normalized = normalizer.normalize_for_search(phone_number)

        if normalized:
            # Search by normalized value (exact match)
            return (
                self.db.query(Contact)
                .join(PhoneNumber)
                .filter(
                    Contact.deleted == False,  # noqa: E712
                    PhoneNumber.value == normalized,
                )
                .distinct()
                .all()
            )
        else:
            # Fallback: search by digits only (suffix matching)
            digits = re.sub(r"\D", "", phone_number)
            if len(digits) >= 7:
                # Use LIKE for suffix matching
                pattern = f"%{digits}"
                return (
                    self.db.query(Contact)
                    .join(PhoneNumber)
                    .filter(
                        Contact.deleted == False,  # noqa: E712
                        PhoneNumber.value.like(pattern),
                    )
                    .distinct()
                    .all()
                )

        return []

    def get_contacts(
        self,
        limit: int = 30,
        offset: int = 0,
        sort_by_recent: bool = False
    ) -> List[Contact]:
        """Get contacts with pagination and sorting.

        Args:
            limit: Maximum number of contacts to return
            offset: Number of contacts to skip
            sort_by_recent: If True, sort by updated_at desc; otherwise by display_name

        Returns:
            List of active contacts
        """
        query = (
            self.db.query(Contact)
            .filter(Contact.deleted == False)  # noqa: E712
        )

        if sort_by_recent:
            query = query.order_by(Contact.updated_at.desc())
        else:
            query = query.order_by(Contact.display_name.asc())

        return query.offset(offset).limit(limit).all()

    def get_contacts_by_letter_group(
        self,
        letter: str,
        limit: int = 30,
        offset: int = 0,
        sort_by_recent: bool = False
    ) -> List[Contact]:
        """Get contacts filtered by first letter of display name.

        Args:
            letter: First letter to filter by (A-Z) or '#' for non-alphabetic
            limit: Maximum number of contacts to return
            offset: Number of contacts to skip
            sort_by_recent: If True, sort by updated_at desc; otherwise by display_name

        Returns:
            List of active contacts starting with the specified letter
        """
        query = (
            self.db.query(Contact)
            .filter(Contact.deleted == False)  # noqa: E712
        )

        if letter == "#":
            # Match contacts starting with non-alphabetic characters
            # Cross-database compatible: check first character is not alphabetic
            from sqlalchemy import func
            first_char = func.substr(Contact.display_name, 1, 1)
            query = query.filter(
                ~first_char.between('A', 'Z'),
                ~first_char.between('a', 'z')
            )
        else:
            # Match contacts starting with specific letter (case-insensitive)
            query = query.filter(
                Contact.display_name.ilike(f"{letter}%")
            )

        if sort_by_recent:
            query = query.order_by(Contact.updated_at.desc())
        else:
            query = query.order_by(Contact.display_name.asc())

        return query.offset(offset).limit(limit).all()

    def count_contacts(self) -> int:
        """Count all active (non-deleted) contacts.

        Returns:
            Number of active contacts
        """
        return (
            self.db.query(Contact)
            .filter(Contact.deleted == False)  # noqa: E712
            .count()
        )

    def count_contacts_by_letter_group(self, letter: str) -> int:
        """Count contacts by first letter of display name.

        Args:
            letter: First letter to filter by (A-Z) or '#' for non-alphabetic

        Returns:
            Number of active contacts starting with the specified letter
        """
        query = (
            self.db.query(Contact)
            .filter(Contact.deleted == False)  # noqa: E712
        )

        if letter == "#":
            # Count contacts starting with non-alphabetic characters
            # Cross-database compatible: check first character is not alphabetic
            from sqlalchemy import func
            first_char = func.substr(Contact.display_name, 1, 1)
            query = query.filter(
                ~first_char.between('A', 'Z'),
                ~first_char.between('a', 'z')
            )
        else:
            # Count contacts starting with specific letter (case-insensitive)
            query = query.filter(
                Contact.display_name.ilike(f"{letter}%")
            )

        return query.count()

    def get_contact_by_id(self, contact_id: str) -> Optional[Contact]:
        """Get contact by ID (string format).

        Args:
            contact_id: Contact ID as string

        Returns:
            Contact or None if not found
        """
        try:
            uuid_id = UUID(contact_id)
            return (
                self.db.query(Contact)
                .filter(
                    Contact.id == uuid_id,
                    Contact.deleted == False  # noqa: E712
                )
                .first()
            )
        except (ValueError, AttributeError):
            return None

    def get_contact_statistics(self) -> dict:
        """Get aggregate contact statistics.

        Returns:
            Dictionary with contact statistics including:
            - total_contacts: Total number of active contacts
            - contacts_with_phone: Contacts with at least one phone number
            - contacts_with_email: Contacts with at least one email
            - total_phone_numbers: Total phone number records
            - total_emails: Total email records
        """
        from ..models.email_address import EmailAddress

        total_contacts = self.count_contacts()

        # Count contacts with phone numbers
        contacts_with_phone = (
            self.db.query(Contact.id)
            .join(PhoneNumber)
            .filter(Contact.deleted == False)  # noqa: E712
            .distinct()
            .count()
        )

        # Count contacts with emails
        contacts_with_email = (
            self.db.query(Contact.id)
            .join(EmailAddress)
            .filter(Contact.deleted == False)  # noqa: E712
            .distinct()
            .count()
        )

        # Count total phone numbers
        total_phone_numbers = (
            self.db.query(PhoneNumber)
            .join(Contact)
            .filter(Contact.deleted == False)  # noqa: E712
            .count()
        )

        # Count total emails
        total_emails = (
            self.db.query(EmailAddress)
            .join(Contact)
            .filter(Contact.deleted == False)  # noqa: E712
            .count()
        )

        return {
            "total_contacts": total_contacts,
            "contacts_with_phone": contacts_with_phone,
            "contacts_with_email": contacts_with_email,
            "total_phone_numbers": total_phone_numbers,
            "total_emails": total_emails,
        }

