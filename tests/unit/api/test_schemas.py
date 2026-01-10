"""Test Google API schemas.

This module tests the Pydantic schemas for parsing Google People API responses.
"""
import pytest

from google_contacts_cisco.api.schemas import (
    GoogleConnectionsResponse,
    GoogleEmailAddress,
    GoogleMetadata,
    GoogleMetadataSource,
    GoogleName,
    GoogleOrganization,
    GooglePerson,
    GooglePhoneNumber,
)


class TestGoogleName:
    """Test GoogleName schema."""

    def test_parse_with_all_fields(self):
        """Test parsing name with all fields populated."""
        data = {
            "displayName": "John Doe",
            "givenName": "John",
            "familyName": "Doe",
        }
        name = GoogleName(**data)

        assert name.display_name == "John Doe"
        assert name.given_name == "John"
        assert name.family_name == "Doe"

    def test_parse_with_alias(self):
        """Test parsing with snake_case field names."""
        name = GoogleName(display_name="Jane Doe", given_name="Jane")

        assert name.display_name == "Jane Doe"
        assert name.given_name == "Jane"
        assert name.family_name is None

    def test_parse_with_optional_fields_missing(self):
        """Test parsing when optional fields are missing."""
        data = {}
        name = GoogleName(**data)

        assert name.display_name is None
        assert name.given_name is None
        assert name.family_name is None


class TestGooglePhoneNumber:
    """Test GooglePhoneNumber schema."""

    def test_parse_phone_number(self):
        """Test parsing phone number with all fields."""
        data = {
            "value": "(555) 123-4567",
            "type": "mobile",
            "formattedType": "Mobile",
        }
        phone = GooglePhoneNumber(**data)

        assert phone.value == "(555) 123-4567"
        assert phone.type == "mobile"
        assert phone.formatted_type == "Mobile"

    def test_parse_phone_number_minimal(self):
        """Test parsing phone number with only required value."""
        data = {"value": "5551234567"}
        phone = GooglePhoneNumber(**data)

        assert phone.value == "5551234567"
        assert phone.type is None
        assert phone.formatted_type is None

    def test_parse_with_snake_case(self):
        """Test parsing with snake_case formatted_type alias."""
        phone = GooglePhoneNumber(value="123", formatted_type="Work")
        assert phone.formatted_type == "Work"


class TestGoogleEmailAddress:
    """Test GoogleEmailAddress schema."""

    def test_parse_email_address(self):
        """Test parsing valid email address."""
        data = {"value": "john@example.com", "type": "work"}
        email = GoogleEmailAddress(**data)

        assert email.value == "john@example.com"
        assert email.type == "work"

    def test_invalid_email_address(self):
        """Test that invalid email raises validation error."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            GoogleEmailAddress(value="not-an-email")

    def test_email_without_type(self):
        """Test parsing email without type."""
        email = GoogleEmailAddress(value="test@test.com")
        assert email.type is None


class TestGoogleOrganization:
    """Test GoogleOrganization schema."""

    def test_parse_organization(self):
        """Test parsing organization with all fields."""
        data = {"name": "Acme Corp", "title": "Engineer"}
        org = GoogleOrganization(**data)

        assert org.name == "Acme Corp"
        assert org.title == "Engineer"

    def test_parse_organization_partial(self):
        """Test parsing organization with only name."""
        org = GoogleOrganization(name="Acme Corp")

        assert org.name == "Acme Corp"
        assert org.title is None

    def test_parse_organization_empty(self):
        """Test parsing empty organization."""
        org = GoogleOrganization()

        assert org.name is None
        assert org.title is None


class TestGoogleMetadataSource:
    """Test GoogleMetadataSource schema."""

    def test_parse_metadata_source(self):
        """Test parsing metadata source."""
        data = {"type": "CONTACT", "id": "12345", "etag": "abc123"}
        source = GoogleMetadataSource(**data)

        assert source.type == "CONTACT"
        assert source.id == "12345"
        assert source.etag == "abc123"

    def test_parse_metadata_source_without_etag(self):
        """Test parsing metadata source without optional etag."""
        data = {"type": "PROFILE", "id": "67890"}
        source = GoogleMetadataSource(**data)

        assert source.etag is None


class TestGoogleMetadata:
    """Test GoogleMetadata schema."""

    def test_parse_metadata_with_sources(self):
        """Test parsing metadata with sources."""
        data = {
            "sources": [
                {"type": "CONTACT", "id": "123", "etag": "abc"},
                {"type": "PROFILE", "id": "456"},
            ],
            "deleted": False,
        }
        metadata = GoogleMetadata(**data)

        assert len(metadata.sources) == 2
        assert metadata.sources[0].type == "CONTACT"
        assert metadata.deleted is False

    def test_parse_metadata_deleted(self):
        """Test parsing metadata for deleted contact."""
        data = {"deleted": True, "sources": []}
        metadata = GoogleMetadata(**data)

        assert metadata.deleted is True
        assert len(metadata.sources) == 0

    def test_parse_metadata_empty(self):
        """Test parsing empty metadata."""
        metadata = GoogleMetadata()

        assert len(metadata.sources) == 0
        assert metadata.deleted is None


class TestGooglePerson:
    """Test GooglePerson schema."""

    def test_parse_full_person(self):
        """Test parsing a complete person from API response."""
        data = {
            "resourceName": "people/c123",
            "etag": "etag123",
            "names": [
                {
                    "displayName": "John Doe",
                    "givenName": "John",
                    "familyName": "Doe",
                }
            ],
            "phoneNumbers": [{"value": "(555) 123-4567", "type": "mobile"}],
            "emailAddresses": [{"value": "john@example.com", "type": "work"}],
            "organizations": [{"name": "Acme Corp", "title": "Engineer"}],
        }

        person = GooglePerson(**data)

        assert person.resource_name == "people/c123"
        assert person.etag == "etag123"
        assert len(person.names) == 1
        assert person.names[0].display_name == "John Doe"
        assert len(person.phone_numbers) == 1
        assert len(person.email_addresses) == 1
        assert len(person.organizations) == 1

    def test_parse_minimal_person(self):
        """Test parsing person with only required fields."""
        data = {"resourceName": "people/c456"}
        person = GooglePerson(**data)

        assert person.resource_name == "people/c456"
        assert person.etag is None
        assert len(person.names) == 0
        assert len(person.phone_numbers) == 0

    def test_get_display_name_with_display_name(self):
        """Test get_display_name returns displayName field."""
        person = GooglePerson(
            resourceName="people/c123",
            names=[GoogleName(displayName="John Doe")],
        )
        assert person.get_display_name() == "John Doe"

    def test_get_display_name_constructs_from_parts(self):
        """Test get_display_name constructs name from given and family name."""
        person = GooglePerson(
            resourceName="people/c123",
            names=[GoogleName(givenName="John", familyName="Doe")],
        )
        assert person.get_display_name() == "John Doe"

    def test_get_display_name_given_only(self):
        """Test get_display_name with only given name."""
        person = GooglePerson(
            resourceName="people/c123",
            names=[GoogleName(givenName="John")],
        )
        assert person.get_display_name() == "John"

    def test_get_display_name_family_only(self):
        """Test get_display_name with only family name."""
        person = GooglePerson(
            resourceName="people/c123",
            names=[GoogleName(familyName="Doe")],
        )
        assert person.get_display_name() == "Doe"

    def test_get_display_name_fallback_to_organization(self):
        """Test get_display_name falls back to organization name."""
        person = GooglePerson(
            resourceName="people/c123",
            organizations=[GoogleOrganization(name="Acme Corporation")],
        )
        assert person.get_display_name() == "Acme Corporation"

    def test_get_display_name_organization_before_email(self):
        """Test get_display_name uses organization before email."""
        person = GooglePerson(
            resourceName="people/c123",
            organizations=[GoogleOrganization(name="Acme Corp")],
            emailAddresses=[{"value": "info@acme.com"}],
        )
        assert person.get_display_name() == "Acme Corp"

    def test_get_display_name_personal_name_over_organization(self):
        """Test get_display_name prefers personal name over organization."""
        person = GooglePerson(
            resourceName="people/c123",
            names=[GoogleName(givenName="John")],
            organizations=[GoogleOrganization(name="Acme Corp")],
        )
        assert person.get_display_name() == "John"

    def test_get_display_name_empty_organization_name_skipped(self):
        """Test get_display_name skips empty organization name."""
        person = GooglePerson(
            resourceName="people/c123",
            organizations=[GoogleOrganization(name=None)],
            emailAddresses=[{"value": "test@test.com"}],
        )
        assert person.get_display_name() == "test@test.com"

    def test_get_display_name_empty_string_organization_skipped(self):
        """Test get_display_name skips empty string organization name."""
        person = GooglePerson(
            resourceName="people/c123",
            organizations=[GoogleOrganization(name="")],
            emailAddresses=[{"value": "test@test.com"}],
        )
        assert person.get_display_name() == "test@test.com"

    def test_get_display_name_whitespace_only_organization_skipped(self):
        """Test get_display_name skips whitespace-only organization name."""
        person = GooglePerson(
            resourceName="people/c123",
            organizations=[GoogleOrganization(name="   ")],
            emailAddresses=[{"value": "test@test.com"}],
        )
        assert person.get_display_name() == "test@test.com"

    def test_get_display_name_organization_with_whitespace_trimmed(self):
        """Test get_display_name trims whitespace from organization name."""
        person = GooglePerson(
            resourceName="people/c123",
            organizations=[GoogleOrganization(name="  Acme Corp  ")],
        )
        assert person.get_display_name() == "Acme Corp"

    def test_get_display_name_skips_empty_orgs_uses_later_org(self):
        """Test get_display_name skips empty organizations and uses first valid one."""
        person = GooglePerson(
            resourceName="people/c123",
            organizations=[
                GoogleOrganization(name=None),
                GoogleOrganization(name=""),
                GoogleOrganization(name="   "),
                GoogleOrganization(name="Valid Corp"),
                GoogleOrganization(name="Second Corp"),
            ],
        )
        assert person.get_display_name() == "Valid Corp"

    def test_get_display_name_multiple_organizations_uses_first(self):
        """Test get_display_name uses first organization when multiple exist."""
        person = GooglePerson(
            resourceName="people/c123",
            organizations=[
                GoogleOrganization(name="First Corp"),
                GoogleOrganization(name="Second Corp"),
            ],
        )
        assert person.get_display_name() == "First Corp"

    def test_get_display_name_fallback_to_email(self):
        """Test get_display_name falls back to email."""
        person = GooglePerson(
            resourceName="people/c123",
            emailAddresses=[{"value": "john@example.com"}],
        )
        assert person.get_display_name() == "john@example.com"

    def test_get_display_name_fallback_to_resource_name(self):
        """Test get_display_name falls back to resource name as last resort."""
        person = GooglePerson(resourceName="people/c123")
        assert person.get_display_name() == "people/c123"

    def test_is_deleted_true(self):
        """Test is_deleted returns True when metadata.deleted is True."""
        person = GooglePerson(
            resourceName="people/c123",
            metadata=GoogleMetadata(deleted=True),
        )
        assert person.is_deleted() is True

    def test_is_deleted_false(self):
        """Test is_deleted returns False when not deleted."""
        person = GooglePerson(
            resourceName="people/c123",
            metadata=GoogleMetadata(deleted=False),
        )
        assert person.is_deleted() is False

    def test_is_deleted_no_metadata(self):
        """Test is_deleted returns False when no metadata."""
        person = GooglePerson(resourceName="people/c123")
        assert person.is_deleted() is False

    def test_is_deleted_metadata_deleted_none(self):
        """Test is_deleted returns False when deleted is None."""
        person = GooglePerson(
            resourceName="people/c123",
            metadata=GoogleMetadata(),
        )
        assert person.is_deleted() is False

    def test_get_primary_etag_from_top_level(self):
        """Test get_primary_etag returns top-level etag."""
        person = GooglePerson(
            resourceName="people/c123",
            etag="top-level-etag",
        )
        assert person.get_primary_etag() == "top-level-etag"

    def test_get_primary_etag_from_metadata_source(self):
        """Test get_primary_etag returns etag from CONTACT source."""
        person = GooglePerson(
            resourceName="people/c123",
            metadata=GoogleMetadata(
                sources=[
                    GoogleMetadataSource(type="PROFILE", id="1"),
                    GoogleMetadataSource(type="CONTACT", id="2", etag="contact-etag"),
                ]
            ),
        )
        assert person.get_primary_etag() == "contact-etag"

    def test_get_primary_etag_prefers_top_level(self):
        """Test get_primary_etag prefers top-level over metadata source."""
        person = GooglePerson(
            resourceName="people/c123",
            etag="top-level-etag",
            metadata=GoogleMetadata(
                sources=[
                    GoogleMetadataSource(type="CONTACT", id="1", etag="source-etag"),
                ]
            ),
        )
        assert person.get_primary_etag() == "top-level-etag"

    def test_get_primary_etag_none_when_not_available(self):
        """Test get_primary_etag returns None when no etag available."""
        person = GooglePerson(
            resourceName="people/c123",
            metadata=GoogleMetadata(
                sources=[
                    GoogleMetadataSource(type="PROFILE", id="1"),
                ]
            ),
        )
        assert person.get_primary_etag() is None

    def test_get_primary_etag_no_metadata(self):
        """Test get_primary_etag returns None with no metadata."""
        person = GooglePerson(resourceName="people/c123")
        assert person.get_primary_etag() is None


class TestGoogleConnectionsResponse:
    """Test GoogleConnectionsResponse schema."""

    def test_parse_connections_response(self):
        """Test parsing connections list response."""
        data = {
            "connections": [
                {"resourceName": "people/c1", "names": [{"displayName": "Alice"}]},
                {"resourceName": "people/c2", "names": [{"displayName": "Bob"}]},
            ],
            "nextPageToken": "page2",
            "nextSyncToken": "sync123",
            "totalPeople": 100,
            "totalItems": 2,
        }

        response = GoogleConnectionsResponse(**data)

        assert len(response.connections) == 2
        assert response.connections[0].resource_name == "people/c1"
        assert response.next_page_token == "page2"
        assert response.next_sync_token == "sync123"
        assert response.total_people == 100
        assert response.total_items == 2

    def test_parse_empty_connections_response(self):
        """Test parsing empty connections response."""
        data = {}
        response = GoogleConnectionsResponse(**data)

        assert len(response.connections) == 0
        assert response.next_page_token is None
        assert response.next_sync_token is None
        assert response.total_people is None

    def test_parse_connections_with_snake_case(self):
        """Test parsing with snake_case field names."""
        response = GoogleConnectionsResponse(
            connections=[],
            next_page_token="token123",
            total_items=50,
        )

        assert response.next_page_token == "token123"
        assert response.total_items == 50

