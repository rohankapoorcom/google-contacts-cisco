# Task 2.3: Contact Data Models

## Overview

Define Pydantic schemas for validating and transforming contact data from Google People API format to our internal database format. These schemas ensure type safety and data consistency throughout the application.

## Priority

**P0 (Critical)** - Required for MVP

## Dependencies

- Task 1.2: Database Setup
- Task 2.2: Google API Client

## Objectives

1. Create Pydantic schemas for Google API response parsing
2. Create schemas for internal contact representation
3. Implement transformation logic from Google format to database format
4. Handle missing or optional fields gracefully
5. Validate phone numbers and email addresses
6. Test schema validation and transformations

## Technical Context

### Google People API Person Resource Structure
```json
{
  "resourceName": "people/c1234567890",
  "etag": "%EgcBARkE...",
  "names": [{
    "displayName": "John Doe",
    "familyName": "Doe",
    "givenName": "John"
  }],
  "phoneNumbers": [{
    "value": "(555) 123-4567",
    "type": "mobile",
    "formattedType": "Mobile"
  }],
  "emailAddresses": [{
    "value": "john@example.com",
    "type": "work"
  }],
  "organizations": [{
    "name": "Acme Corp",
    "title": "Engineer"
  }],
  "metadata": {
    "sources": [{
      "type": "CONTACT",
      "id": "1234567890"
    }]
  }
}
```

### Data Flow
1. Google API → Raw JSON
2. Pydantic Schema → Validated Python objects
3. Transformation → Database models
4. Database → Storage

## Acceptance Criteria

- [ ] Pydantic schemas parse Google API responses correctly
- [ ] Schemas handle missing optional fields
- [ ] Phone number validation works
- [ ] Email validation works
- [ ] Display name generation handles various name configurations
- [ ] Transformation from Google to database format is tested
- [ ] Deleted contacts are marked properly
- [ ] Metadata and etag are preserved
- [ ] All schemas have proper type hints

## Implementation Steps

### 1. Create API Schemas (Google Format)

Create `google_contacts_cisco/api/schemas.py`:

```python
"""Pydantic schemas for API requests and responses."""
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, EmailStr


class GoogleName(BaseModel):
    """Name from Google People API."""
    display_name: Optional[str] = Field(None, alias="displayName")
    given_name: Optional[str] = Field(None, alias="givenName")
    family_name: Optional[str] = Field(None, alias="familyName")
    
    class Config:
        populate_by_name = True


class GooglePhoneNumber(BaseModel):
    """Phone number from Google People API."""
    value: str
    type: Optional[str] = None
    formatted_type: Optional[str] = Field(None, alias="formattedType")
    
    class Config:
        populate_by_name = True


class GoogleEmailAddress(BaseModel):
    """Email address from Google People API."""
    value: EmailStr
    type: Optional[str] = None
    
    class Config:
        populate_by_name = True


class GoogleOrganization(BaseModel):
    """Organization from Google People API."""
    name: Optional[str] = None
    title: Optional[str] = None
    
    class Config:
        populate_by_name = True


class GoogleMetadataSource(BaseModel):
    """Metadata source from Google People API."""
    type: str
    id: str
    etag: Optional[str] = None
    
    class Config:
        populate_by_name = True


class GoogleMetadata(BaseModel):
    """Metadata from Google People API."""
    sources: List[GoogleMetadataSource] = []
    deleted: Optional[bool] = None
    
    class Config:
        populate_by_name = True


class GooglePerson(BaseModel):
    """Person from Google People API."""
    resource_name: str = Field(..., alias="resourceName")
    etag: Optional[str] = None
    names: List[GoogleName] = []
    phone_numbers: List[GooglePhoneNumber] = Field(default_factory=list, alias="phoneNumbers")
    email_addresses: List[GoogleEmailAddress] = Field(default_factory=list, alias="emailAddresses")
    organizations: List[GoogleOrganization] = []
    metadata: Optional[GoogleMetadata] = None
    
    class Config:
        populate_by_name = True
    
    def get_display_name(self) -> str:
        """Get display name for contact.
        
        Returns:
            Display name, falling back to email or resource name
        """
        # Try names array first
        if self.names:
            name = self.names[0]
            if name.display_name:
                return name.display_name
            elif name.given_name and name.family_name:
                return f"{name.given_name} {name.family_name}"
            elif name.given_name:
                return name.given_name
            elif name.family_name:
                return name.family_name
        
        # Fall back to email
        if self.email_addresses:
            return self.email_addresses[0].value
        
        # Last resort: resource name
        return self.resource_name
    
    def is_deleted(self) -> bool:
        """Check if contact is deleted.
        
        Returns:
            True if contact is marked as deleted
        """
        return self.metadata and self.metadata.deleted is True
    
    def get_primary_etag(self) -> Optional[str]:
        """Get primary etag from metadata sources.
        
        Returns:
            Etag string or None
        """
        if self.etag:
            return self.etag
        
        if self.metadata and self.metadata.sources:
            for source in self.metadata.sources:
                if source.type == "CONTACT" and source.etag:
                    return source.etag
        
        return None


class GoogleConnectionsResponse(BaseModel):
    """Response from Google People API connections list."""
    connections: List[GooglePerson] = []
    next_page_token: Optional[str] = Field(None, alias="nextPageToken")
    next_sync_token: Optional[str] = Field(None, alias="nextSyncToken")
    total_people: Optional[int] = Field(None, alias="totalPeople")
    total_items: Optional[int] = Field(None, alias="totalItems")
    
    class Config:
        populate_by_name = True
```

### 2. Create Internal Contact Schemas

Create `google_contacts_cisco/schemas/contact.py`:

```python
"""Internal contact schemas."""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr, field_validator


class PhoneNumberSchema(BaseModel):
    """Phone number schema."""
    value: str
    display_value: str
    type: Optional[str] = None
    primary: bool = False
    
    @field_validator('value')
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        """Validate and normalize phone number."""
        # Remove common formatting characters
        normalized = ''.join(c for c in v if c.isdigit() or c == '+')
        if not normalized:
            raise ValueError("Phone number must contain at least one digit")
        return normalized


class ContactCreateSchema(BaseModel):
    """Schema for creating a contact."""
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
    """Schema for contact with database fields."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    synced_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ContactSearchResultSchema(BaseModel):
    """Schema for contact search results."""
    id: UUID
    display_name: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    organization: Optional[str] = None
    phone_numbers: List[PhoneNumberSchema] = []
    
    class Config:
        from_attributes = True
```

### 3. Create Transformation Functions

Create `google_contacts_cisco/services/contact_transformer.py`:

```python
"""Transform Google contacts to internal format."""
from typing import List
from datetime import datetime

from ..api.schemas import GooglePerson, GooglePhoneNumber
from ..schemas.contact import ContactCreateSchema, PhoneNumberSchema


def transform_google_person_to_contact(person: GooglePerson) -> ContactCreateSchema:
    """Transform Google Person to internal contact format.
    
    Args:
        person: GooglePerson from API
        
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
    phone_numbers = []
    for i, phone in enumerate(person.phone_numbers):
        phone_numbers.append(
            PhoneNumberSchema(
                value=phone.value,  # Will be normalized by validator
                display_value=phone.value,
                type=phone.type or phone.formatted_type or "other",
                primary=(i == 0)  # First phone is primary
            )
        )
    
    return ContactCreateSchema(
        resource_name=person.resource_name,
        etag=person.get_primary_etag(),
        given_name=given_name,
        family_name=family_name,
        display_name=person.get_display_name(),
        organization=organization,
        job_title=job_title,
        phone_numbers=phone_numbers,
        deleted=person.is_deleted()
    )


def transform_google_persons_batch(persons: List[GooglePerson]) -> List[ContactCreateSchema]:
    """Transform batch of Google Persons.
    
    Args:
        persons: List of GooglePerson from API
        
    Returns:
        List of ContactCreateSchema
    """
    return [transform_google_person_to_contact(person) for person in persons]
```

### 4. Create Tests

Create `tests/test_schemas.py`:

```python
"""Test schemas."""
import pytest
from pydantic import ValidationError

from google_contacts_cisco.api.schemas import GooglePerson, GoogleName, GooglePhoneNumber
from google_contacts_cisco.schemas.contact import ContactCreateSchema, PhoneNumberSchema


def test_google_person_parsing():
    """Test parsing Google Person from API response."""
    data = {
        "resourceName": "people/c123",
        "etag": "etag123",
        "names": [{
            "displayName": "John Doe",
            "givenName": "John",
            "familyName": "Doe"
        }],
        "phoneNumbers": [{
            "value": "(555) 123-4567",
            "type": "mobile"
        }]
    }
    
    person = GooglePerson(**data)
    
    assert person.resource_name == "people/c123"
    assert person.etag == "etag123"
    assert len(person.names) == 1
    assert person.names[0].display_name == "John Doe"
    assert len(person.phone_numbers) == 1


def test_google_person_get_display_name():
    """Test display name generation."""
    # With display name
    person1 = GooglePerson(
        resourceName="people/c123",
        names=[GoogleName(displayName="John Doe")]
    )
    assert person1.get_display_name() == "John Doe"
    
    # With given and family name
    person2 = GooglePerson(
        resourceName="people/c123",
        names=[GoogleName(givenName="John", familyName="Doe")]
    )
    assert person2.get_display_name() == "John Doe"
    
    # With only given name
    person3 = GooglePerson(
        resourceName="people/c123",
        names=[GoogleName(givenName="John")]
    )
    assert person3.get_display_name() == "John"
    
    # Fallback to email
    person4 = GooglePerson(
        resourceName="people/c123",
        emailAddresses=[{"value": "john@example.com"}]
    )
    assert person4.get_display_name() == "john@example.com"


def test_phone_number_normalization():
    """Test phone number normalization."""
    phone = PhoneNumberSchema(
        value="(555) 123-4567",
        display_value="(555) 123-4567",
        type="mobile"
    )
    
    # Should strip formatting
    assert phone.value == "5551234567"
    assert phone.display_value == "(555) 123-4567"


def test_phone_number_validation_invalid():
    """Test phone number validation with invalid input."""
    with pytest.raises(ValidationError):
        PhoneNumberSchema(
            value="not-a-number",
            display_value="not-a-number"
        )


def test_contact_create_schema():
    """Test contact creation schema."""
    contact = ContactCreateSchema(
        resource_name="people/c123",
        etag="etag123",
        given_name="John",
        family_name="Doe",
        display_name="John Doe",
        phone_numbers=[
            PhoneNumberSchema(
                value="5551234567",
                display_value="(555) 123-4567",
                type="mobile",
                primary=True
            )
        ]
    )
    
    assert contact.resource_name == "people/c123"
    assert contact.display_name == "John Doe"
    assert len(contact.phone_numbers) == 1
    assert contact.phone_numbers[0].primary is True
```

Create `tests/test_contact_transformer.py`:

```python
"""Test contact transformation."""
from google_contacts_cisco.api.schemas import GooglePerson, GoogleName, GooglePhoneNumber
from google_contacts_cisco.services.contact_transformer import transform_google_person_to_contact


def test_transform_google_person():
    """Test transforming Google Person to internal format."""
    person = GooglePerson(
        resourceName="people/c123",
        etag="etag123",
        names=[GoogleName(
            displayName="John Doe",
            givenName="John",
            familyName="Doe"
        )],
        phoneNumbers=[GooglePhoneNumber(
            value="(555) 123-4567",
            type="mobile"
        )],
        organizations=[{
            "name": "Acme Corp",
            "title": "Engineer"
        }]
    )
    
    contact = transform_google_person_to_contact(person)
    
    assert contact.resource_name == "people/c123"
    assert contact.display_name == "John Doe"
    assert contact.given_name == "John"
    assert contact.family_name == "Doe"
    assert contact.organization == "Acme Corp"
    assert contact.job_title == "Engineer"
    assert len(contact.phone_numbers) == 1
    assert contact.phone_numbers[0].value == "5551234567"  # Normalized
    assert contact.phone_numbers[0].primary is True


def test_transform_deleted_contact():
    """Test transforming deleted contact."""
    person = GooglePerson(
        resourceName="people/c123",
        names=[GoogleName(displayName="Deleted Contact")],
        metadata={
            "deleted": True,
            "sources": []
        }
    )
    
    contact = transform_google_person_to_contact(person)
    
    assert contact.deleted is True
```


## Testing Requirements

**⚠️ Critical**: This task is not complete until comprehensive unit tests are written and passing.

### Test Coverage Requirements
- All functions and methods must have tests
- Both success and failure paths must be covered
- Edge cases and boundary conditions must be tested
- **Minimum coverage: 80% for this module**
- **Target coverage: 85%+ for services, 90%+ for utilities**

### Test Files to Create
Create test file(s) in `tests/unit/` matching your implementation structure:

```
Implementation File              →  Test File
─────────────────────────────────────────────────────────────
[implementation path]            →  tests/unit/[same structure]/test_[filename].py
```

### Test Structure Template
```python
"""Test [module name].

This module tests the [feature] implementation from this task.
"""
import pytest
from google_contacts_cisco.[module] import [Component]


class Test[FeatureName]:
    """Test [feature] functionality."""
    
    def test_typical_use_case(self):
        """Test the main success path."""
        # Arrange
        input_data = ...
        
        # Act
        result = component.method(input_data)
        
        # Assert
        assert result == expected
    
    def test_handles_invalid_input(self):
        """Test error handling for invalid input."""
        with pytest.raises(ValueError):
            component.method(invalid_input)
    
    def test_edge_case_empty_data(self):
        """Test behavior with empty/null data."""
        result = component.method([])
        assert result == []
    
    def test_edge_case_boundary_values(self):
        """Test boundary conditions."""
        ...
```

### What to Test
- ✅ **Success paths**: Typical use cases and expected inputs
- ✅ **Error paths**: Invalid inputs, exceptions, error conditions
- ✅ **Edge cases**: Empty data, null values, boundary conditions, large datasets
- ✅ **Side effects**: Database changes, file operations, API calls
- ✅ **Return values**: Correct types, formats, and values
- ✅ **State changes**: Object state, system state

### Testing Best Practices
- Use descriptive test names that explain what is being tested
- Follow Arrange-Act-Assert pattern
- Use fixtures from `tests/conftest.py` for common test data
- Mock external dependencies (APIs, databases, file system)
- Keep tests independent (no shared state)
- Make tests fast (< 5 seconds per test file)
- Test behavior, not implementation details

### Running Your Tests
```bash
# Run tests for this specific module
uv run pytest tests/unit/[your_test_file].py -v

# Run with coverage report
uv run pytest tests/unit/[your_test_file].py \
    --cov=google_contacts_cisco.[your_module] \
    --cov-report=term-missing

# Run in watch mode (re-run on file changes)
uv run pytest-watch tests/unit/[your_directory]/ -v
```

### Acceptance Criteria Additions
- [ ] All new code has corresponding tests
- [ ] Tests cover success cases, error cases, and edge cases
- [ ] All tests pass (`pytest tests/unit/[module]/ -v`)
- [ ] Coverage is >80% for this module
- [ ] Tests are independent and can run in any order
- [ ] External dependencies are properly mocked
- [ ] Test names clearly describe what is being tested

### Example Test Scenarios for This Task
- Test Contact model creation and relationships
- Test PhoneNumber model with normalization
- Test EmailAddress model validation
- Test cascade deletes
- Test model serialization to dict


## Verification

After completing this task:

1. **Test Schema Parsing**:
   ```python
   from google_contacts_cisco.api.schemas import GooglePerson
   
   # Parse Google API response
   data = {
       "resourceName": "people/c123",
       "names": [{"displayName": "John Doe"}],
       "phoneNumbers": [{"value": "(555) 123-4567"}]
   }
   
   person = GooglePerson(**data)
   print(person.get_display_name())  # "John Doe"
   ```

2. **Test Transformation**:
   ```python
   from google_contacts_cisco.services.contact_transformer import transform_google_person_to_contact
   
   contact = transform_google_person_to_contact(person)
   print(contact.display_name)  # "John Doe"
   print(contact.phone_numbers[0].value)  # "5551234567"
   ```

3. **Run Tests**:
   ```bash
   pytest tests/test_schemas.py tests/test_contact_transformer.py -v
   ```

## Notes

- **Pydantic V2**: Using Pydantic 2.x features (Config, validators)
- **Alias Support**: Google uses camelCase, we use snake_case internally
- **Phone Normalization**: Strips formatting for database storage, preserves original for display
- **Display Name**: Multiple fallback strategies ensure every contact has a name
- **Type Safety**: All schemas fully typed for mypy compliance
- **Validation**: Pydantic validates data automatically

## Common Issues

1. **Missing Names**: Some contacts have no name - fallback to email or resource name
2. **Multiple Phone Numbers**: Mark first as primary by default
3. **Phone Formatting**: Google returns various formats - normalize for search
4. **Deleted Contacts**: Check metadata.deleted flag
5. **Missing Etag**: May be in metadata.sources instead of top level

## Related Documentation

- Pydantic: https://docs.pydantic.dev/
- Google Person Resource: https://developers.google.com/people/api/rest/v1/people#Person
- Phone Number Formats: https://en.wikipedia.org/wiki/National_conventions_for_writing_telephone_numbers

## Estimated Time

3-4 hours

