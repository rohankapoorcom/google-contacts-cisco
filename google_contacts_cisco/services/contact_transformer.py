"""Transform Google contacts to internal format.

This module provides functions to convert Google People API response
data into the internal contact format used by the application.
"""
from typing import List

from ..api.schemas import GooglePerson
from ..schemas.contact import ContactCreateSchema, PhoneNumberSchema


def transform_google_person_to_contact(person: GooglePerson) -> ContactCreateSchema:
    """Transform Google Person to internal contact format.

    Extracts relevant fields from the Google Person resource and creates
    a ContactCreateSchema suitable for database storage.

    Args:
        person: GooglePerson parsed from API response

    Returns:
        ContactCreateSchema ready for database insertion
    """
    # Extract names
    given_name = None
    family_name = None
    if person.names:
        name = person.names[0]
        given_name = name.given_name
        family_name = name.family_name

    # Extract organization info
    organization = None
    job_title = None
    if person.organizations:
        org = person.organizations[0]
        organization = org.name
        job_title = org.title

    # Transform phone numbers
    phone_numbers = _transform_phone_numbers(person)

    return ContactCreateSchema(
        resource_name=person.resource_name,
        etag=person.get_primary_etag(),
        given_name=given_name,
        family_name=family_name,
        display_name=person.get_display_name(),
        organization=organization,
        job_title=job_title,
        phone_numbers=phone_numbers,
        deleted=person.is_deleted(),
    )


def _transform_phone_numbers(person: GooglePerson) -> List[PhoneNumberSchema]:
    """Transform phone numbers from Google Person.

    Args:
        person: GooglePerson with phone numbers

    Returns:
        List of PhoneNumberSchema objects
    """
    phone_numbers = []
    for i, phone in enumerate(person.phone_numbers):
        try:
            phone_schema = PhoneNumberSchema(
                value=phone.value,  # Will be normalized by validator
                display_value=phone.value,
                type=phone.type or phone.formatted_type or "other",
                primary=(i == 0),  # First phone is primary
            )
            phone_numbers.append(phone_schema)
        except ValueError:
            # Skip invalid phone numbers (e.g., ones with no digits)
            continue
    return phone_numbers


def transform_google_persons_batch(
    persons: List[GooglePerson],
) -> List[ContactCreateSchema]:
    """Transform batch of Google Persons.

    Convenience function for transforming multiple contacts at once.

    Args:
        persons: List of GooglePerson from API

    Returns:
        List of ContactCreateSchema
    """
    return [transform_google_person_to_contact(person) for person in persons]

