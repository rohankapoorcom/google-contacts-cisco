# Task 4.2: Phone Number Normalization

## Overview

Implement phone number normalization and search functionality to enable searching contacts by phone number. This includes normalizing phone numbers to E.164 format for consistent storage and comparison, and implementing search logic.

## Priority

**P1 (High)** - Required for search functionality

## Dependencies

- Task 1.2: Database Setup
- Task 2.1: Contact Data Models

## Objectives

1. Implement phone number normalization to E.164 format
2. Handle various input formats (local, international, with/without formatting)
3. Store normalized values in database for search
4. Implement phone number comparison logic
5. Handle invalid phone numbers gracefully
6. Add support for country-specific formatting
7. Test with various phone number formats
8. Optimize for search performance

## Technical Context

### Phone Number Formats
- **E.164**: International standard (+1234567890)
- **National**: Local format without country code
- **Formatted**: With parentheses, dashes, spaces
- **Extensions**: Business numbers with extensions

### Normalization Strategy
1. Parse input using `phonenumbers` library
2. Normalize to E.164 format for storage
3. Keep original display format for presentation
4. Handle country code defaults (US: +1)

### Search Strategy
- Normalize search input
- Compare against normalized values in database
- Support partial matching (last N digits)
- Return all matching contacts

## Acceptance Criteria

- [ ] Phone numbers are normalized to E.164 format
- [ ] Handles US, international, and formatted numbers
- [ ] Original display format is preserved
- [ ] Search works with various input formats
- [ ] Invalid numbers are handled without errors
- [ ] Normalization is idempotent
- [ ] Performance is acceptable for 10,000+ contacts
- [ ] Tests cover edge cases (extensions, special characters, etc.)

## Implementation Steps

### 1. Add phonenumbers Dependency

Update `pyproject.toml`:

```toml
[project]
dependencies = [
    "fastapi>=0.115.0",
    "sqlalchemy>=2.0.0",
    "lxml>=5.0.0",
    "google-auth>=2.35.0",
    "google-auth-oauthlib>=1.2.0",
    "google-api-python-client>=2.150.0",
    "aiohttp>=3.10.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.6.0",
    "phonenumbers>=8.13.0",  # Phone number parsing and validation
]
```

### 2. Create Phone Number Utility

Create `google_contacts_cisco/utils/phone_utils.py`:

```python
"""Phone number utilities for normalization and search."""
import re
from typing import Optional, Tuple
import phonenumbers
from phonenumbers import NumberParseException

from ..utils.logger import get_logger

logger = get_logger(__name__)


class PhoneNumberNormalizer:
    """Normalize and validate phone numbers."""
    
    def __init__(self, default_country: str = "US"):
        """Initialize normalizer.
        
        Args:
            default_country: Default country code for parsing (ISO 3166-1 alpha-2)
        """
        self.default_country = default_country
    
    def normalize(self, phone_number: str, display_value: Optional[str] = None) -> Tuple[Optional[str], str]:
        """Normalize phone number to E.164 format.
        
        Args:
            phone_number: Raw phone number string
            display_value: Optional display format (if different from phone_number)
            
        Returns:
            Tuple of (normalized_value, display_value)
            - normalized_value: E.164 format or None if invalid
            - display_value: Original or formatted display value
        """
        if not phone_number:
            return None, ""
        
        # Clean input
        cleaned = self._clean_input(phone_number)
        
        # Store display value
        final_display = display_value or phone_number
        
        try:
            # Parse phone number
            parsed = phonenumbers.parse(cleaned, self.default_country)
            
            # Validate
            if not phonenumbers.is_valid_number(parsed):
                logger.warning(f"Invalid phone number: {phone_number}")
                return None, final_display
            
            # Convert to E.164 format
            normalized = phonenumbers.format_number(
                parsed,
                phonenumbers.PhoneNumberFormat.E164
            )
            
            # If no display value provided, format nicely
            if not display_value:
                final_display = self._format_display(parsed)
            
            logger.debug(f"Normalized {phone_number} to {normalized}")
            return normalized, final_display
            
        except NumberParseException as e:
            logger.warning(f"Failed to parse phone number {phone_number}: {e}")
            return None, final_display
        except Exception as e:
            logger.error(f"Error normalizing phone number {phone_number}: {e}")
            return None, final_display
    
    def normalize_for_search(self, phone_number: str) -> Optional[str]:
        """Normalize phone number for search (strips all formatting).
        
        Args:
            phone_number: Phone number to normalize
            
        Returns:
            Normalized E.164 format or None if invalid
        """
        normalized, _ = self.normalize(phone_number)
        return normalized
    
    def matches(self, stored_number: str, search_number: str) -> bool:
        """Check if two phone numbers match.
        
        Args:
            stored_number: Normalized number from database
            search_number: User input to search
            
        Returns:
            True if numbers match
        """
        if not stored_number or not search_number:
            return False
        
        # Normalize search input
        normalized_search = self.normalize_for_search(search_number)
        if not normalized_search:
            # If normalization fails, try digit-only comparison
            return self._digit_only_match(stored_number, search_number)
        
        # Exact match on E.164
        if stored_number == normalized_search:
            return True
        
        # Try suffix matching (last N digits)
        return self._suffix_match(stored_number, normalized_search)
    
    def _clean_input(self, phone_number: str) -> str:
        """Clean phone number input.
        
        Args:
            phone_number: Raw input
            
        Returns:
            Cleaned string
        """
        # Remove common separators but keep + for international
        cleaned = phone_number.strip()
        
        # Handle extensions (remove them for normalization)
        ext_pattern = r'\s*(ext|extension|x)\s*\.?\s*\d+$'
        cleaned = re.sub(ext_pattern, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned
    
    def _format_display(self, parsed: phonenumbers.PhoneNumber) -> str:
        """Format phone number for display.
        
        Args:
            parsed: Parsed phone number
            
        Returns:
            Formatted display string
        """
        # Use national format for domestic, international for foreign
        if parsed.country_code == 1:  # US/Canada
            return phonenumbers.format_number(
                parsed,
                phonenumbers.PhoneNumberFormat.NATIONAL
            )
        else:
            return phonenumbers.format_number(
                parsed,
                phonenumbers.PhoneNumberFormat.INTERNATIONAL
            )
    
    def _digit_only_match(self, stored: str, search: str) -> bool:
        """Match using digits only (fallback).
        
        Args:
            stored: Stored number
            search: Search input
            
        Returns:
            True if digits match
        """
        stored_digits = re.sub(r'\D', '', stored)
        search_digits = re.sub(r'\D', '', search)
        
        if not stored_digits or not search_digits:
            return False
        
        # Match if search is suffix of stored
        return stored_digits.endswith(search_digits) or search_digits.endswith(stored_digits)
    
    def _suffix_match(self, stored: str, search: str, min_digits: int = 7) -> bool:
        """Match phone numbers by suffix (last N digits).
        
        Args:
            stored: Stored E.164 number
            search: Search E.164 number
            min_digits: Minimum digits to match
            
        Returns:
            True if suffixes match
        """
        stored_digits = re.sub(r'\D', '', stored)
        search_digits = re.sub(r'\D', '', search)
        
        # Need at least min_digits to match
        if len(search_digits) < min_digits:
            return False
        
        # Check if one is suffix of other
        return stored_digits.endswith(search_digits) or search_digits.endswith(stored_digits)


def get_phone_normalizer(default_country: str = "US") -> PhoneNumberNormalizer:
    """Get phone number normalizer instance.
    
    Args:
        default_country: Default country code
        
    Returns:
        PhoneNumberNormalizer instance
    """
    return PhoneNumberNormalizer(default_country)
```

### 3. Update Contact Repository for Search

Update `google_contacts_cisco/repositories/contact_repository.py`:

```python
def search_by_phone(self, phone_number: str) -> List[Contact]:
    """Search contacts by phone number.
    
    Args:
        phone_number: Phone number to search (any format)
        
    Returns:
        List of matching contacts
    """
    from ..utils.phone_utils import get_phone_normalizer
    
    normalizer = get_phone_normalizer()
    
    # Normalize search input
    normalized = normalizer.normalize_for_search(phone_number)
    
    if normalized:
        # Search by normalized value
        return (
            self.db.query(Contact)
            .join(PhoneNumber)
            .filter(
                Contact.deleted == False,
                PhoneNumber.value == normalized
            )
            .distinct()
            .all()
        )
    else:
        # Fallback: search by digits only
        digits = re.sub(r'\D', '', phone_number)
        if len(digits) >= 7:
            # Use LIKE for suffix matching
            pattern = f"%{digits}"
            return (
                self.db.query(Contact)
                .join(PhoneNumber)
                .filter(
                    Contact.deleted == False,
                    PhoneNumber.value.like(pattern)
                )
                .distinct()
                .all()
            )
    
    return []
```

### 4. Update Sync to Normalize Numbers

Update `google_contacts_cisco/services/sync/full_sync.py`:

```python
from ...utils.phone_utils import get_phone_normalizer

# In _sync_phone_numbers method:
def _sync_phone_numbers(self, contact: Contact, phone_data: List[Dict]):
    """Sync phone numbers for contact."""
    normalizer = get_phone_normalizer()
    
    # Clear existing
    contact.phone_numbers.clear()
    
    for idx, phone_dict in enumerate(phone_data):
        raw_value = phone_dict.get('value', '')
        display_value = phone_dict.get('formattedValue', raw_value)
        
        # Normalize
        normalized_value, final_display = normalizer.normalize(
            raw_value,
            display_value
        )
        
        # Create phone number record
        phone = PhoneNumber(
            contact_id=contact.id,
            value=normalized_value or raw_value,  # Fallback to raw if normalization fails
            display_value=final_display,
            type=phone_dict.get('type', 'other').lower(),
            primary=idx == 0  # First is primary
        )
        
        contact.phone_numbers.append(phone)
```

### 5. Create Tests

Create `tests/test_phone_utils.py`:

```python
"""Test phone number utilities."""
import pytest
from google_contacts_cisco.utils.phone_utils import PhoneNumberNormalizer, get_phone_normalizer


@pytest.fixture
def normalizer():
    """Create phone normalizer."""
    return get_phone_normalizer()


def test_normalize_us_number(normalizer):
    """Test normalizing US phone numbers."""
    test_cases = [
        ("5551234567", "+15551234567"),
        ("555-123-4567", "+15551234567"),
        ("(555) 123-4567", "+15551234567"),
        ("+1 555 123 4567", "+15551234567"),
        ("1-555-123-4567", "+15551234567"),
    ]
    
    for input_num, expected in test_cases:
        normalized, display = normalizer.normalize(input_num)
        assert normalized == expected, f"Failed for {input_num}"


def test_normalize_international_number(normalizer):
    """Test normalizing international numbers."""
    test_cases = [
        ("+44 20 7946 0958", "+442079460958"),  # UK
        ("+33 1 42 86 82 00", "+33142868200"),  # France
        ("+49 30 12345678", "+493012345678"),   # Germany
    ]
    
    for input_num, expected in test_cases:
        normalized, display = normalizer.normalize(input_num)
        assert normalized == expected, f"Failed for {input_num}"


def test_normalize_with_extension(normalizer):
    """Test normalizing numbers with extensions."""
    test_cases = [
        "555-123-4567 ext 123",
        "555-123-4567 x123",
        "555-123-4567 extension 123",
    ]
    
    for input_num in test_cases:
        normalized, display = normalizer.normalize(input_num)
        assert normalized == "+15551234567"  # Extension should be removed


def test_normalize_invalid_number(normalizer):
    """Test handling invalid numbers."""
    invalid_numbers = [
        "123",  # Too short
        "abcdefghij",  # Not a number
        "000-000-0000",  # Invalid
        "",  # Empty
    ]
    
    for input_num in invalid_numbers:
        normalized, display = normalizer.normalize(input_num)
        assert normalized is None, f"Should be invalid: {input_num}"


def test_display_formatting(normalizer):
    """Test display formatting."""
    # US numbers should be formatted as (XXX) XXX-XXXX
    normalized, display = normalizer.normalize("5551234567")
    assert normalized == "+15551234567"
    assert display == "(555) 123-4567"
    
    # International should include country code
    normalized, display = normalizer.normalize("+442079460958")
    assert normalized == "+442079460958"
    assert "+44" in display


def test_preserve_custom_display(normalizer):
    """Test preserving custom display format."""
    normalized, display = normalizer.normalize(
        "5551234567",
        display_value="Custom: 555.123.4567"
    )
    assert normalized == "+15551234567"
    assert display == "Custom: 555.123.4567"


def test_search_normalization(normalizer):
    """Test normalization for search."""
    test_cases = [
        ("555-123-4567", "+15551234567"),
        ("(555) 123-4567", "+15551234567"),
        ("5551234567", "+15551234567"),
    ]
    
    for input_num, expected in test_cases:
        normalized = normalizer.normalize_for_search(input_num)
        assert normalized == expected


def test_phone_matching(normalizer):
    """Test phone number matching."""
    stored = "+15551234567"
    
    # Exact matches
    assert normalizer.matches(stored, "5551234567")
    assert normalizer.matches(stored, "+1 555-123-4567")
    assert normalizer.matches(stored, "(555) 123-4567")
    
    # Suffix matches
    assert normalizer.matches(stored, "1234567")  # Last 7 digits
    assert normalizer.matches(stored, "123-4567")
    
    # Non-matches
    assert not normalizer.matches(stored, "5551234568")
    assert not normalizer.matches(stored, "123")  # Too short


def test_idempotent_normalization(normalizer):
    """Test that normalization is idempotent."""
    input_num = "(555) 123-4567"
    
    # First normalization
    normalized1, _ = normalizer.normalize(input_num)
    
    # Second normalization of result
    normalized2, _ = normalizer.normalize(normalized1)
    
    assert normalized1 == normalized2 == "+15551234567"


def test_special_characters(normalizer):
    """Test handling special characters."""
    test_cases = [
        "555.123.4567",
        "555/123/4567",
        "555 123 4567",
        "555-123-4567",
    ]
    
    expected = "+15551234567"
    for input_num in test_cases:
        normalized, _ = normalizer.normalize(input_num)
        assert normalized == expected


@pytest.mark.parametrize("country,number,expected", [
    ("US", "2025551234", "+12025551234"),
    ("GB", "2079460958", "+442079460958"),
    ("DE", "3012345678", "+493012345678"),
])
def test_country_defaults(country, number, expected):
    """Test different country defaults."""
    normalizer = PhoneNumberNormalizer(default_country=country)
    normalized, _ = normalizer.normalize(number)
    assert normalized == expected
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
- Test US number normalization to E.164
- Test international number normalization
- Test invalid number handling
- Test phone number matching (suffix, format variations)
- Test idempotency of normalization


## Verification

After completing this task:

1. **Test Normalization**:
   ```python
   from google_contacts_cisco.utils.phone_utils import get_phone_normalizer
   
   normalizer = get_phone_normalizer()
   
   # Test various formats
   print(normalizer.normalize("555-123-4567"))
   # Output: ('+15551234567', '(555) 123-4567')
   
   print(normalizer.normalize("+44 20 7946 0958"))
   # Output: ('+442079460958', '+44 20 7946 0958')
   ```

2. **Test Search**:
   ```python
   from google_contacts_cisco.models import get_db
   from google_contacts_cisco.repositories.contact_repository import ContactRepository
   
   db = next(get_db())
   repo = ContactRepository(db)
   
   # Search by phone
   results = repo.search_by_phone("555-123-4567")
   print(f"Found {len(results)} contacts")
   ```

3. **Run Tests**:
   ```bash
   uv run pytest tests/test_phone_utils.py -v
   ```

## Notes

- **phonenumbers Library**: Industry-standard library by Google
- **E.164 Format**: International standard (+[country][number])
- **Display vs. Storage**: Store normalized, display original
- **Search Flexibility**: Handle partial matches, various formats
- **Performance**: Normalization is fast, but cache if needed
- **Country Codes**: Default to US, but support international
- **Extensions**: Strip for normalization, but could preserve in display
- **Validation**: Invalid numbers are stored but flagged

## Common Issues

1. **Invalid Numbers**: Log warnings but don't fail sync
2. **International Numbers**: Require + prefix or country code
3. **Extensions**: Need special handling
4. **Short Codes**: May not normalize (SMS services)
5. **Performance**: Normalization is I/O bound, consider batching

## Related Documentation

- phonenumbers: https://github.com/daviddrysdale/python-phonenumbers
- E.164 Format: https://en.wikipedia.org/wiki/E.164
- libphonenumber: https://github.com/google/libphonenumber

## Estimated Time

4-5 hours

