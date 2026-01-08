"""Internal contact schemas.

These schemas are used for internal data representation and validation,
separate from the Google API-specific schemas.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


class PhoneNumberSchema(BaseModel):
    """Phone number schema for internal use.

    Validates and normalizes phone numbers for storage and search.
    """

    value: str
    display_value: str
    type: Optional[str] = None
    primary: bool = False

    @field_validator("value", mode="before")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        """Validate and normalize phone number.

        Strips all formatting characters (parentheses, dashes, spaces)
        and keeps only digits and the leading + sign.

        Args:
            v: Raw phone number string

        Returns:
            Normalized phone number containing only digits and optional +

        Raises:
            ValueError: If the phone number contains no digits
        """
        if not v:
            raise ValueError("Phone number cannot be empty")

        # Remove common formatting characters, keep + and digits
        normalized = "".join(c for c in v if c.isdigit() or c == "+")
        if not normalized or (normalized == "+" and len(normalized) == 1):
            raise ValueError("Phone number must contain at least one digit")
        return normalized


class ContactCreateSchema(BaseModel):
    """Schema for creating a contact.

    Used when syncing contacts from Google to the local database.
    """

    resource_name: str
    etag: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    display_name: str
    organization: Optional[str] = None
    job_title: Optional[str] = None
    phone_numbers: List[PhoneNumberSchema] = []
    deleted: bool = False


class ContactSchema(ContactCreateSchema):
    """Schema for contact with database fields.

    Extends ContactCreateSchema with fields that are populated by the database.
    """

    id: UUID
    created_at: datetime
    updated_at: datetime
    synced_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ContactSearchResultSchema(BaseModel):
    """Schema for contact search results.

    A lighter-weight schema for returning search results.
    """

    id: UUID
    display_name: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    organization: Optional[str] = None
    phone_numbers: List[PhoneNumberSchema] = []

    model_config = {"from_attributes": True}


# API Response Schemas

class PhoneNumberResponse(BaseModel):
    """Phone number response schema for API."""

    id: UUID
    value: str
    display_value: str
    type: str
    primary: bool

    model_config = {"from_attributes": True}


class EmailAddressResponse(BaseModel):
    """Email address response schema for API."""

    id: UUID
    value: str
    type: str
    primary: bool

    model_config = {"from_attributes": True}


class ContactResponse(BaseModel):
    """Contact response schema for API."""

    id: str
    display_name: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    phone_numbers: List[PhoneNumberResponse]
    email_addresses: List[EmailAddressResponse] = []
    updated_at: Optional[str] = None

    @classmethod
    def from_orm(cls, contact):
        """Create response from ORM model."""
        # Get email addresses if the relationship exists
        email_addresses = []
        if hasattr(contact, 'email_addresses'):
            email_addresses = [
                EmailAddressResponse.model_validate(e)
                for e in contact.email_addresses
            ]

        return cls(
            id=str(contact.id),
            display_name=contact.display_name,
            given_name=contact.given_name,
            family_name=contact.family_name,
            phone_numbers=[
                PhoneNumberResponse.model_validate(p)
                for p in contact.phone_numbers
            ],
            email_addresses=email_addresses,
            updated_at=contact.updated_at.isoformat() if contact.updated_at else None
        )


class ContactListResponse(BaseModel):
    """Paginated contact list response."""

    contacts: List[ContactResponse]
    total: int
    offset: int
    limit: int
    has_more: bool

