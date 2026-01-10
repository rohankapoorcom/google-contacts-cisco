"""Test contact transformation.

This module tests the contact transformation service that converts
Google Person data to internal contact format.
"""

from google_contacts_cisco.api.schemas import (
    GoogleMetadata,
    GoogleMetadataSource,
    GoogleName,
    GoogleOrganization,
    GooglePerson,
    GooglePhoneNumber,
)
from google_contacts_cisco.services.contact_transformer import (
    _transform_phone_numbers,
    transform_google_person_to_contact,
    transform_google_persons_batch,
)


class TestTransformGooglePersonToContact:
    """Test transform_google_person_to_contact function."""

    def test_transform_full_person(self):
        """Test transforming a complete Google Person."""
        person = GooglePerson(
            resourceName="people/c123",
            etag="etag123",
            names=[
                GoogleName(
                    displayName="John Doe",
                    givenName="John",
                    familyName="Doe",
                )
            ],
            phoneNumbers=[
                GooglePhoneNumber(value="(555) 123-4567", type="mobile")
            ],
            organizations=[GoogleOrganization(name="Acme Corp", title="Engineer")],
        )

        contact = transform_google_person_to_contact(person)

        assert contact.resource_name == "people/c123"
        assert contact.etag == "etag123"
        assert contact.display_name == "John Doe"
        assert contact.given_name == "John"
        assert contact.family_name == "Doe"
        assert contact.organization == "Acme Corp"
        assert contact.job_title == "Engineer"
        assert len(contact.phone_numbers) == 1
        assert contact.phone_numbers[0].value == "5551234567"  # Normalized
        assert contact.phone_numbers[0].display_value == "(555) 123-4567"
        assert contact.phone_numbers[0].primary is True
        assert contact.deleted is False

    def test_transform_minimal_person(self):
        """Test transforming a person with only required fields."""
        person = GooglePerson(resourceName="people/c123")

        contact = transform_google_person_to_contact(person)

        assert contact.resource_name == "people/c123"
        assert contact.display_name == "people/c123"  # Falls back to resource name
        assert contact.given_name is None
        assert contact.family_name is None
        assert contact.organization is None
        assert contact.job_title is None
        assert len(contact.phone_numbers) == 0
        assert contact.deleted is False

    def test_transform_person_no_display_name(self):
        """Test transforming person with given/family but no display name."""
        person = GooglePerson(
            resourceName="people/c123",
            names=[GoogleName(givenName="Jane", familyName="Smith")],
        )

        contact = transform_google_person_to_contact(person)

        # Should construct display name from parts
        assert contact.display_name == "Jane Smith"
        assert contact.given_name == "Jane"
        assert contact.family_name == "Smith"

    def test_transform_deleted_person(self):
        """Test transforming a deleted contact."""
        person = GooglePerson(
            resourceName="people/c123",
            names=[GoogleName(displayName="Deleted Contact")],
            metadata=GoogleMetadata(deleted=True, sources=[]),
        )

        contact = transform_google_person_to_contact(person)

        assert contact.deleted is True
        assert contact.display_name == "Deleted Contact"

    def test_transform_person_etag_from_metadata(self):
        """Test getting etag from metadata source."""
        person = GooglePerson(
            resourceName="people/c123",
            names=[GoogleName(displayName="Test")],
            metadata=GoogleMetadata(
                sources=[
                    GoogleMetadataSource(type="CONTACT", id="123", etag="source-etag")
                ]
            ),
        )

        contact = transform_google_person_to_contact(person)

        assert contact.etag == "source-etag"

    def test_transform_person_multiple_phone_numbers(self):
        """Test transforming person with multiple phone numbers."""
        person = GooglePerson(
            resourceName="people/c123",
            names=[GoogleName(displayName="Test")],
            phoneNumbers=[
                GooglePhoneNumber(value="5551111111", type="mobile"),
                GooglePhoneNumber(value="5552222222", type="work"),
                GooglePhoneNumber(value="5553333333", type="home"),
            ],
        )

        contact = transform_google_person_to_contact(person)

        assert len(contact.phone_numbers) == 3
        # First phone should be primary
        assert contact.phone_numbers[0].primary is True
        assert contact.phone_numbers[1].primary is False
        assert contact.phone_numbers[2].primary is False
        # Types should be preserved
        assert contact.phone_numbers[0].type == "mobile"
        assert contact.phone_numbers[1].type == "work"
        assert contact.phone_numbers[2].type == "home"

    def test_transform_person_phone_with_formatted_type(self):
        """Test phone number type falls back to formattedType."""
        person = GooglePerson(
            resourceName="people/c123",
            names=[GoogleName(displayName="Test")],
            phoneNumbers=[
                GooglePhoneNumber(value="5551234567", formattedType="Mobile")
            ],
        )

        contact = transform_google_person_to_contact(person)

        assert contact.phone_numbers[0].type == "Mobile"

    def test_transform_person_phone_default_type(self):
        """Test phone number defaults to 'other' when no type."""
        person = GooglePerson(
            resourceName="people/c123",
            names=[GoogleName(displayName="Test")],
            phoneNumbers=[GooglePhoneNumber(value="5551234567")],
        )

        contact = transform_google_person_to_contact(person)

        assert contact.phone_numbers[0].type == "other"

    def test_transform_person_only_organization_name(self):
        """Test transforming person with only organization name."""
        person = GooglePerson(
            resourceName="people/c123",
            names=[GoogleName(displayName="Test")],
            organizations=[GoogleOrganization(name="Acme Corp")],
        )

        contact = transform_google_person_to_contact(person)

        assert contact.organization == "Acme Corp"
        assert contact.job_title is None

    def test_transform_person_only_job_title(self):
        """Test transforming person with only job title."""
        person = GooglePerson(
            resourceName="people/c123",
            names=[GoogleName(displayName="Test")],
            organizations=[GoogleOrganization(title="Engineer")],
        )

        contact = transform_google_person_to_contact(person)

        assert contact.organization is None
        assert contact.job_title == "Engineer"

    def test_transform_business_contact_without_names(self):
        """Test transforming business contact with no personal names."""
        person = GooglePerson(
            resourceName="people/c123",
            organizations=[GoogleOrganization(name="Acme Corporation", title="Sales")],
            phoneNumbers=[GooglePhoneNumber(value="5551234567", type="work")],
        )

        contact = transform_google_person_to_contact(person)

        # Display name should use organization name
        assert contact.display_name == "Acme Corporation"
        assert contact.given_name is None
        assert contact.family_name is None
        assert contact.organization == "Acme Corporation"
        assert contact.job_title == "Sales"
        assert len(contact.phone_numbers) == 1

    def test_transform_business_contact_uses_organization_before_email(self):
        """Test business contact uses organization name before email."""
        person = GooglePerson(
            resourceName="people/c123",
            organizations=[GoogleOrganization(name="Tech Solutions Inc")],
            emailAddresses=[{"value": "info@techsolutions.com"}],
        )

        contact = transform_google_person_to_contact(person)

        # Should prefer organization name over email
        assert contact.display_name == "Tech Solutions Inc"
        assert contact.organization == "Tech Solutions Inc"


class TestTransformPhoneNumbers:
    """Test _transform_phone_numbers helper function."""

    def test_transform_empty_phone_list(self):
        """Test transforming person with no phone numbers."""
        person = GooglePerson(resourceName="people/c123")

        phones = _transform_phone_numbers(person)

        assert len(phones) == 0

    def test_transform_skips_invalid_phone(self):
        """Test that invalid phone numbers are skipped."""
        person = GooglePerson(
            resourceName="people/c123",
            phoneNumbers=[
                GooglePhoneNumber(value="5551234567", type="mobile"),
                GooglePhoneNumber(value="not-a-number", type="invalid"),
                GooglePhoneNumber(value="5559876543", type="work"),
            ],
        )

        phones = _transform_phone_numbers(person)

        # Only valid phones should be included
        assert len(phones) == 2
        assert phones[0].value == "5551234567"
        assert phones[1].value == "5559876543"

    def test_transform_phone_primary_assignment(self):
        """Test that primary is assigned based on original list index.

        The implementation marks primary based on the index in the original
        Google phone numbers list (i=0 is primary). When the first phone is
        invalid and skipped, no phone gets marked as primary since there's
        no valid phone at index 0.
        """
        person = GooglePerson(
            resourceName="people/c123",
            phoneNumbers=[
                GooglePhoneNumber(value="abc", type="invalid"),  # Will be skipped
                GooglePhoneNumber(value="5551111111", type="mobile"),
                GooglePhoneNumber(value="5552222222", type="work"),
            ],
        )

        phones = _transform_phone_numbers(person)

        # Only valid phones are included
        assert len(phones) == 2
        # Primary is assigned based on original index (i=0), and since first
        # phone was invalid and skipped, neither remaining phone is primary
        assert phones[0].primary is False
        assert phones[1].primary is False


class TestTransformGooglePersonsBatch:
    """Test transform_google_persons_batch function."""

    def test_transform_empty_batch(self):
        """Test transforming empty batch."""
        contacts = transform_google_persons_batch([])

        assert len(contacts) == 0

    def test_transform_single_person_batch(self):
        """Test transforming batch with single person."""
        persons = [
            GooglePerson(
                resourceName="people/c1",
                names=[GoogleName(displayName="Alice")],
            )
        ]

        contacts = transform_google_persons_batch(persons)

        assert len(contacts) == 1
        assert contacts[0].display_name == "Alice"

    def test_transform_multiple_persons_batch(self):
        """Test transforming batch with multiple persons."""
        persons = [
            GooglePerson(
                resourceName="people/c1",
                names=[GoogleName(displayName="Alice")],
            ),
            GooglePerson(
                resourceName="people/c2",
                names=[GoogleName(displayName="Bob")],
            ),
            GooglePerson(
                resourceName="people/c3",
                names=[GoogleName(displayName="Charlie")],
            ),
        ]

        contacts = transform_google_persons_batch(persons)

        assert len(contacts) == 3
        assert contacts[0].display_name == "Alice"
        assert contacts[1].display_name == "Bob"
        assert contacts[2].display_name == "Charlie"
        assert contacts[0].resource_name == "people/c1"
        assert contacts[1].resource_name == "people/c2"
        assert contacts[2].resource_name == "people/c3"

    def test_transform_batch_preserves_all_data(self):
        """Test that batch transform preserves all contact data."""
        persons = [
            GooglePerson(
                resourceName="people/c1",
                etag="etag1",
                names=[GoogleName(displayName="Alice", givenName="Alice")],
                phoneNumbers=[GooglePhoneNumber(value="5551111111", type="mobile")],
                organizations=[GoogleOrganization(name="Corp A")],
            ),
            GooglePerson(
                resourceName="people/c2",
                etag="etag2",
                names=[GoogleName(displayName="Bob", familyName="Smith")],
                phoneNumbers=[GooglePhoneNumber(value="5552222222", type="work")],
                organizations=[GoogleOrganization(title="Manager")],
            ),
        ]

        contacts = transform_google_persons_batch(persons)

        assert contacts[0].etag == "etag1"
        assert contacts[0].given_name == "Alice"
        assert contacts[0].organization == "Corp A"
        assert contacts[0].phone_numbers[0].value == "5551111111"

        assert contacts[1].etag == "etag2"
        assert contacts[1].family_name == "Smith"
        assert contacts[1].job_title == "Manager"
        assert contacts[1].phone_numbers[0].value == "5552222222"

