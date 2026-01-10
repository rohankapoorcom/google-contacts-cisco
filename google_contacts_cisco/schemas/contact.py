"""Internal contact schemas.

These schemas are used for internal data representation and validation,
separate from the Google API-specific schemas.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator

from ..utils.phone_utils import get_phone_normalizer


class PhoneNumberSchema(BaseModel):
    """Phone number schema for internal use.

    Validates and normalizes phone numbers to E.164 format for storage and search.
    """

    value: str
    display_value: str
    type: Optional[str] = None
    primary: bool = False

    @model_validator(mode="before")
    @classmethod
    def normalize_phone_number(cls, data):
        """Normalize phone number to E.164 format.

        Uses the phone normalization utility to convert the phone number
        to E.164 format while preserving the display value. Handles dialing
        prefixes like *67, *82, #31# by stripping them before normalization.

        Args:
            data: Dictionary with phone number data

        Returns:
            Dictionary with normalized value and display_value

        Raises:
            ValueError: If the phone number cannot be normalized
        """
        if isinstance(data, dict):
            value = data.get("value")
            display_value = data.get("display_value")

            if not value:
                raise ValueError("Phone number cannot be empty")

            normalizer = get_phone_normalizer()
            normalized, formatted_display = normalizer.normalize(value, display_value)

            if normalized is None:
                # Fallback to simple digit extraction if normalization fails
                # This handles edge cases where phonenumbers library can't parse
                # Reuse _clean_input to strip prefixes and extensions
                cleaned_value, _detected_prefix = normalizer._clean_input(value)

                # Extract digits; keep a single leading '+' if present
                digits_only = "".join(c for c in cleaned_value if c.isdigit())
                if cleaned_value.strip().startswith("+") and digits_only:
                    normalized = f"+{digits_only}"
                else:
                    normalized = digits_only

                if not normalized or normalized == "+":
                    raise ValueError(
                        f"Phone number must contain at least one digit: {value}"
                    )

            # Update the data with normalized values
            data["value"] = normalized
            # Use original display_value if provided, otherwise use formatted
            if not display_value:
                data["display_value"] = formatted_display

        return data


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

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        """Validate that display_name is not empty or only whitespace.

        Args:
            v: The display_name value

        Returns:
            Validated display_name (stripped of leading/trailing whitespace)

        Raises:
            ValueError: If display_name is empty or only whitespace
        """
        if not v or not v.strip():
            raise ValueError("display_name cannot be empty or only whitespace")
        return v.strip()


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
    type: Optional[str] = None
    primary: bool

    model_config = {"from_attributes": True}


class EmailAddressResponse(BaseModel):
    """Email address response schema for API."""

    id: UUID
    value: str
    type: Optional[str] = None
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

