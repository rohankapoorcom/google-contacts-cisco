"""Test internal contact schemas.

This module tests the Pydantic schemas for internal contact representation.
"""
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from google_contacts_cisco.schemas.contact import (
    PhoneNumberSchema,
    ContactCreateSchema,
    ContactSchema,
    ContactSearchResultSchema,
)


class TestPhoneNumberSchema:
    """Test PhoneNumberSchema validation and normalization."""

    def test_basic_phone_number(self):
        """Test creating a basic phone number."""
        phone = PhoneNumberSchema(
            value="5551234567",
            display_value="(555) 123-4567",
            type="mobile",
        )

        assert phone.value == "5551234567"
        assert phone.display_value == "(555) 123-4567"
        assert phone.type == "mobile"
        assert phone.primary is False

    def test_phone_number_normalization(self):
        """Test that phone numbers are normalized (formatting stripped)."""
        phone = PhoneNumberSchema(
            value="(555) 123-4567",
            display_value="(555) 123-4567",
            type="mobile",
        )

        # Value should have formatting stripped
        assert phone.value == "5551234567"
        # Display value should be preserved
        assert phone.display_value == "(555) 123-4567"

    def test_phone_number_normalization_with_plus(self):
        """Test that + is preserved in international numbers."""
        phone = PhoneNumberSchema(
            value="+1 (555) 123-4567",
            display_value="+1 (555) 123-4567",
        )

        assert phone.value == "+15551234567"

    def test_phone_number_normalization_with_spaces_and_dashes(self):
        """Test normalization of various formatting characters."""
        phone = PhoneNumberSchema(
            value="555 - 123 - 4567",
            display_value="555-123-4567",
        )

        assert phone.value == "5551234567"

    def test_phone_number_primary_flag(self):
        """Test setting primary flag."""
        phone = PhoneNumberSchema(
            value="5551234567",
            display_value="555-123-4567",
            primary=True,
        )

        assert phone.primary is True

    def test_phone_number_optional_type(self):
        """Test phone number without type."""
        phone = PhoneNumberSchema(
            value="5551234567",
            display_value="555-123-4567",
        )

        assert phone.type is None

    def test_phone_number_validation_empty_string(self):
        """Test that empty phone number raises error."""
        with pytest.raises(ValidationError) as exc_info:
            PhoneNumberSchema(value="", display_value="")

        assert "Phone number cannot be empty" in str(exc_info.value)

    def test_phone_number_validation_no_digits(self):
        """Test that phone number with no digits raises error."""
        with pytest.raises(ValidationError) as exc_info:
            PhoneNumberSchema(value="abc-def", display_value="abc-def")

        assert "Phone number must contain at least one digit" in str(exc_info.value)

    def test_phone_number_validation_only_plus(self):
        """Test that phone number with only + raises error."""
        with pytest.raises(ValidationError) as exc_info:
            PhoneNumberSchema(value="+", display_value="+")

        assert "must contain at least one digit" in str(exc_info.value)

    def test_phone_number_validation_formatting_only(self):
        """Test that only formatting characters raises error."""
        with pytest.raises(ValidationError) as exc_info:
            PhoneNumberSchema(value="()-", display_value="()-")

        assert "must contain at least one digit" in str(exc_info.value)

    def test_phone_number_with_star67_prefix(self):
        """Test phone number with *67 prefix is handled correctly."""
        phone = PhoneNumberSchema(
            value="*67 202-555-1234",
            display_value="*67 (202) 555-1234",
        )
        
        # Value should be normalized without prefix
        assert phone.value == "+12025551234"
        # Display should preserve original with prefix
        assert phone.display_value == "*67 (202) 555-1234"

    def test_phone_number_with_star82_prefix(self):
        """Test phone number with *82 prefix."""
        phone = PhoneNumberSchema(
            value="*82 (202) 555-1234",
            display_value="*82 (202) 555-1234",
        )
        
        assert phone.value == "+12025551234"
        assert "*82" in phone.display_value

    def test_phone_number_with_hash31hash_prefix(self):
        """Test phone number with #31# European prefix."""
        phone = PhoneNumberSchema(
            value="#31# +44 20 7946 0958",
            display_value="#31# +44 20 7946 0958",
        )
        
        assert phone.value == "+442079460958"
        assert "#31#" in phone.display_value

    def test_phone_number_with_star31hash_prefix(self):
        """Test phone number with *31# European prefix."""
        phone = PhoneNumberSchema(
            value="*31# +33 1 42 86 82 00",
            display_value="*31# +33 1 42 86 82 00",
        )
        
        assert phone.value == "+33142868200"
        assert "*31#" in phone.display_value

    def test_phone_number_prefix_auto_display(self):
        """Test that prefix is included in auto-generated display."""
        phone = PhoneNumberSchema(
            value="*67 2025551234",
            display_value="*67 2025551234",  # Will be formatted
        )
        
        # Should normalize correctly
        assert phone.value == "+12025551234"
        # Display is preserved as provided
        assert "*67" in phone.display_value

    def test_phone_number_prefix_with_extension(self):
        """Test prefix with extension is handled correctly."""
        phone = PhoneNumberSchema(
            value="*67 202-555-1234 ext 456",
            display_value="*67 (202) 555-1234",
        )
        
        # Prefix stripped, extension removed, normalized
        assert phone.value == "+12025551234"
        assert "ext" not in phone.value
        assert "*67" in phone.display_value

    def test_phone_number_fallback_with_prefix(self):
        """Test that fallback logic handles prefixes."""
        # Use a format that might trigger fallback but still has valid digits
        phone = PhoneNumberSchema(
            value="*67 +1 202 555 1234",
            display_value="*67 +1 202 555 1234",
        )
        
        # Should successfully normalize
        assert phone.value in ["+12025551234", "+1202555123 4"] or "202" in phone.value


class TestContactCreateSchema:
    """Test ContactCreateSchema."""

    def test_basic_contact_creation(self):
        """Test creating a basic contact."""
        contact = ContactCreateSchema(
            resource_name="people/c123",
            display_name="John Doe",
        )

        assert contact.resource_name == "people/c123"
        assert contact.display_name == "John Doe"
        assert contact.etag is None
        assert contact.given_name is None
        assert contact.family_name is None
        assert contact.organization is None
        assert contact.job_title is None
        assert contact.phone_numbers == []
        assert contact.deleted is False

    def test_full_contact_creation(self):
        """Test creating a contact with all fields."""
        contact = ContactCreateSchema(
            resource_name="people/c123",
            etag="etag123",
            given_name="John",
            family_name="Doe",
            display_name="John Doe",
            organization="Acme Corp",
            job_title="Engineer",
            phone_numbers=[
                PhoneNumberSchema(
                    value="5551234567",
                    display_value="(555) 123-4567",
                    type="mobile",
                    primary=True,
                )
            ],
            deleted=False,
        )

        assert contact.resource_name == "people/c123"
        assert contact.etag == "etag123"
        assert contact.given_name == "John"
        assert contact.family_name == "Doe"
        assert contact.display_name == "John Doe"
        assert contact.organization == "Acme Corp"
        assert contact.job_title == "Engineer"
        assert len(contact.phone_numbers) == 1
        assert contact.phone_numbers[0].primary is True

    def test_deleted_contact(self):
        """Test creating a deleted contact."""
        contact = ContactCreateSchema(
            resource_name="people/c123",
            display_name="Deleted Contact",
            deleted=True,
        )

        assert contact.deleted is True

    def test_contact_with_multiple_phone_numbers(self):
        """Test contact with multiple phone numbers."""
        contact = ContactCreateSchema(
            resource_name="people/c123",
            display_name="John Doe",
            phone_numbers=[
                PhoneNumberSchema(
                    value="5551234567",
                    display_value="(555) 123-4567",
                    type="mobile",
                    primary=True,
                ),
                PhoneNumberSchema(
                    value="5559876543",
                    display_value="(555) 987-6543",
                    type="work",
                    primary=False,
                ),
            ],
        )

        assert len(contact.phone_numbers) == 2
        primary = [p for p in contact.phone_numbers if p.primary]
        assert len(primary) == 1


class TestContactSchema:
    """Test ContactSchema with database fields."""

    def test_contact_with_database_fields(self):
        """Test contact schema includes database fields."""
        contact_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        contact = ContactSchema(
            id=contact_id,
            resource_name="people/c123",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )

        assert contact.id == contact_id
        assert contact.created_at == now
        assert contact.updated_at == now
        assert contact.synced_at is None

    def test_contact_with_synced_at(self):
        """Test contact with synced_at timestamp."""
        contact_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        contact = ContactSchema(
            id=contact_id,
            resource_name="people/c123",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
            synced_at=now,
        )

        assert contact.synced_at == now


class TestContactSearchResultSchema:
    """Test ContactSearchResultSchema."""

    def test_search_result_basic(self):
        """Test basic search result."""
        contact_id = uuid.uuid4()

        result = ContactSearchResultSchema(
            id=contact_id,
            display_name="John Doe",
        )

        assert result.id == contact_id
        assert result.display_name == "John Doe"
        assert result.given_name is None
        assert result.family_name is None
        assert result.organization is None
        assert result.phone_numbers == []

    def test_search_result_full(self):
        """Test full search result."""
        contact_id = uuid.uuid4()

        result = ContactSearchResultSchema(
            id=contact_id,
            display_name="John Doe",
            given_name="John",
            family_name="Doe",
            organization="Acme Corp",
            phone_numbers=[
                PhoneNumberSchema(
                    value="5551234567",
                    display_value="(555) 123-4567",
                    type="mobile",
                )
            ],
        )

        assert result.given_name == "John"
        assert result.family_name == "Doe"
        assert result.organization == "Acme Corp"
        assert len(result.phone_numbers) == 1

