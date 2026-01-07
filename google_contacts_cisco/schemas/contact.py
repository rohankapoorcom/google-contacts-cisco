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

