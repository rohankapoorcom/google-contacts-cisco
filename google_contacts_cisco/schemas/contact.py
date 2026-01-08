"""Internal contact schemas.

These schemas are used for internal data representation and validation,
separate from the Google API-specific schemas.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, model_validator

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
        to E.164 format while preserving the display value.

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
                digits = "".join(c for c in value if c.isdigit() or c == "+")
                if not digits or (digits == "+" and len(digits) == 1):
                    raise ValueError(
                        f"Phone number must contain at least one digit: {value}"
                    )
                normalized = digits

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

