"""Contact repository for database operations.

This module provides data access operations for Contact and PhoneNumber entities,
including CRUD operations, upsert logic, and query methods.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.contact import Contact
from ..models.phone_number import PhoneNumber
from ..schemas.contact import ContactCreateSchema
from ..utils.logger import get_logger

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

