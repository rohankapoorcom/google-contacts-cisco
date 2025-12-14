# Task 7.1: Unit Tests

## Overview

Create comprehensive unit tests for all services, utilities, models, and business logic to ensure code quality, prevent regressions, and enable confident refactoring. Achieve >80% code coverage with pytest.

## Priority

**P1 (High)** - Required for production readiness

## Dependencies

- All implementation tasks (1-19)
- Task 1.1: Environment Setup

## Objectives

1. Test all service classes (sync, search, XML formatter, OAuth)
2. Test utility functions (phone normalization, logging)
3. Test data models (Contact, PhoneNumber, EmailAddress)
4. Test repositories (ContactRepository)
5. Achieve >80% code coverage
6. Create comprehensive fixtures and mocks
7. Test edge cases and error conditions
8. Set up pytest configuration
9. Add coverage reporting
10. Document testing patterns

## Technical Context

### Testing Framework
- **pytest**: Main testing framework
- **pytest-cov**: Coverage reporting
- **pytest-asyncio**: Async test support
- **pytest-mock**: Mocking utilities
- **faker**: Generate test data

### Test Organization
```
tests/
├── unit/
│   ├── services/
│   │   ├── test_sync_service.py
│   │   ├── test_search_service.py
│   │   ├── test_xml_formatter.py
│   │   └── test_oauth_service.py
│   ├── utils/
│   │   ├── test_phone_utils.py
│   │   └── test_logger.py
│   ├── models/
│   │   ├── test_contact.py
│   │   ├── test_phone_number.py
│   │   └── test_email_address.py
│   └── repositories/
│       └── test_contact_repository.py
├── conftest.py
└── fixtures/
    └── sample_data.py
```

### Coverage Goals
- Overall: >80%
- Critical paths: >95%
- Services: >85%
- Utilities: >90%

## Acceptance Criteria

- [ ] All service classes have comprehensive tests
- [ ] All utility functions are tested
- [ ] All models are tested
- [ ] All repositories are tested
- [ ] Edge cases are covered
- [ ] Error conditions are tested
- [ ] Mocks are used appropriately
- [ ] Code coverage >80%
- [ ] Tests run fast (<30 seconds)
- [ ] Tests are maintainable and readable
- [ ] CI/CD integration configured

## Implementation Steps

### 1. Set Up pytest Configuration

Create `pyproject.toml` additions:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--strict-markers",
    "--cov=google_contacts_cisco",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-report=xml",
    "--cov-fail-under=80",
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "slow: Slow running tests",
]

[tool.coverage.run]
source = ["google_contacts_cisco"]
omit = [
    "*/tests/*",
    "*/conftest.py",
    "*/__init__.py",
    "*/main.py",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@abstractmethod",
]
```

### 2. Create Test Fixtures

Create `tests/conftest.py`:

```python
"""Pytest configuration and shared fixtures."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from uuid import uuid4
from datetime import datetime

from google_contacts_cisco.models.base import Base
from google_contacts_cisco.models.contact import Contact
from google_contacts_cisco.models.phone_number import PhoneNumber
from google_contacts_cisco.models.email_address import EmailAddress


@pytest.fixture(scope="session")
def engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(engine):
    """Create a fresh database session for each test."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def sample_contact():
    """Create a sample contact for testing."""
    return Contact(
        id=uuid4(),
        resource_name="people/c123456",
        display_name="John Doe",
        given_name="John",
        family_name="Doe",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        deleted=False
    )


@pytest.fixture
def sample_contact_with_phones(sample_contact):
    """Create a sample contact with phone numbers."""
    sample_contact.phone_numbers = [
        PhoneNumber(
            id=uuid4(),
            contact_id=sample_contact.id,
            value="+15551234567",
            display_value="(555) 123-4567",
            type="mobile",
            primary=True
        ),
        PhoneNumber(
            id=uuid4(),
            contact_id=sample_contact.id,
            value="+15559876543",
            display_value="(555) 987-6543",
            type="work",
            primary=False
        )
    ]
    return sample_contact


@pytest.fixture
def sample_contact_with_emails(sample_contact):
    """Create a sample contact with email addresses."""
    sample_contact.email_addresses = [
        EmailAddress(
            id=uuid4(),
            contact_id=sample_contact.id,
            value="john.doe@example.com",
            type="personal",
            primary=True
        ),
        EmailAddress(
            id=uuid4(),
            contact_id=sample_contact.id,
            value="john.doe@work.com",
            type="work",
            primary=False
        )
    ]
    return sample_contact


@pytest.fixture
def multiple_contacts(db_session):
    """Create multiple contacts for list testing."""
    contacts = []
    for i in range(5):
        contact = Contact(
            id=uuid4(),
            resource_name=f"people/c{i}",
            display_name=f"Contact {i}",
            given_name=f"First{i}",
            family_name=f"Last{i}"
        )
        contacts.append(contact)
        db_session.add(contact)
    
    db_session.commit()
    return contacts


@pytest.fixture
def mock_google_api_response():
    """Mock Google People API response."""
    return {
        "resourceName": "people/c123456",
        "etag": "etag123",
        "names": [{
            "displayName": "John Doe",
            "givenName": "John",
            "familyName": "Doe"
        }],
        "phoneNumbers": [{
            "value": "+15551234567",
            "formattedValue": "(555) 123-4567",
            "type": "mobile"
        }],
        "emailAddresses": [{
            "value": "john@example.com",
            "type": "personal"
        }]
    }
```

### 3. Test Phone Number Normalization

Create `tests/unit/utils/test_phone_utils.py`:

```python
"""Test phone number utilities."""
import pytest
from google_contacts_cisco.utils.phone_utils import PhoneNumberNormalizer


@pytest.fixture
def normalizer():
    """Create phone normalizer instance."""
    return PhoneNumberNormalizer(default_country="US")


class TestPhoneNumberNormalization:
    """Test phone number normalization."""
    
    def test_normalize_us_number(self, normalizer):
        """Test normalizing US phone numbers."""
        test_cases = [
            ("5551234567", "+15551234567"),
            ("555-123-4567", "+15551234567"),
            ("(555) 123-4567", "+15551234567"),
            ("+1 555 123 4567", "+15551234567"),
            ("1-555-123-4567", "+15551234567"),
        ]
        
        for input_num, expected in test_cases:
            normalized, _ = normalizer.normalize(input_num)
            assert normalized == expected, f"Failed for {input_num}"
    
    def test_normalize_international(self, normalizer):
        """Test international numbers."""
        test_cases = [
            ("+44 20 7946 0958", "+442079460958"),  # UK
            ("+33 1 42 86 82 00", "+33142868200"),   # France
            ("+49 30 12345678", "+493012345678"),    # Germany
        ]
        
        for input_num, expected in test_cases:
            normalized, _ = normalizer.normalize(input_num)
            assert normalized == expected
    
    def test_normalize_invalid(self, normalizer):
        """Test invalid phone numbers."""
        invalid = ["123", "abc", "000-000-0000", ""]
        
        for num in invalid:
            normalized, _ = normalizer.normalize(num)
            assert normalized is None
    
    def test_preserve_display_format(self, normalizer):
        """Test preserving custom display format."""
        normalized, display = normalizer.normalize(
            "5551234567",
            display_value="Custom: 555.123.4567"
        )
        
        assert normalized == "+15551234567"
        assert display == "Custom: 555.123.4567"
    
    def test_normalize_with_extension(self, normalizer):
        """Test numbers with extensions."""
        test_cases = [
            "555-123-4567 ext 123",
            "555-123-4567 x123",
            "555-123-4567 extension 123",
        ]
        
        for num in test_cases:
            normalized, _ = normalizer.normalize(num)
            assert normalized == "+15551234567"
    
    def test_phone_matching(self, normalizer):
        """Test phone number matching."""
        stored = "+15551234567"
        
        # Exact matches
        assert normalizer.matches(stored, "5551234567")
        assert normalizer.matches(stored, "+1 555-123-4567")
        assert normalizer.matches(stored, "(555) 123-4567")
        
        # Suffix matches
        assert normalizer.matches(stored, "1234567")
        assert normalizer.matches(stored, "123-4567")
        
        # Non-matches
        assert not normalizer.matches(stored, "5551234568")
        assert not normalizer.matches(stored, "123")
    
    def test_idempotent(self, normalizer):
        """Test normalization is idempotent."""
        input_num = "(555) 123-4567"
        
        normalized1, _ = normalizer.normalize(input_num)
        normalized2, _ = normalizer.normalize(normalized1)
        
        assert normalized1 == normalized2 == "+15551234567"
    
    @pytest.mark.parametrize("country,number,expected", [
        ("US", "2025551234", "+12025551234"),
        ("GB", "2079460958", "+442079460958"),
        ("DE", "3012345678", "+493012345678"),
    ])
    def test_country_defaults(self, country, number, expected):
        """Test different country defaults."""
        normalizer = PhoneNumberNormalizer(default_country=country)
        normalized, _ = normalizer.normalize(number)
        assert normalized == expected


class TestPhoneNumberSearch:
    """Test phone number search utilities."""
    
    def test_search_normalization(self, normalizer):
        """Test normalization for search."""
        result = normalizer.normalize_for_search("(555) 123-4567")
        assert result == "+15551234567"
    
    def test_looks_like_phone(self, normalizer):
        """Test phone number detection."""
        assert normalizer._looks_like_phone("5551234567")
        assert normalizer._looks_like_phone("555-123-4567")
        assert normalizer._looks_like_phone("+1 555-123-4567")
        
        assert not normalizer._looks_like_phone("John Doe")
        assert not normalizer._looks_like_phone("123")
        assert not normalizer._looks_like_phone("abc123")
```

### 4. Test XML Formatter

Create `tests/unit/services/test_xml_formatter.py`:

```python
"""Test XML formatter service."""
import pytest
from lxml import etree
from uuid import uuid4

from google_contacts_cisco.services.xml_formatter import (
    CiscoXMLFormatter,
    GROUP_MAPPINGS
)
from google_contacts_cisco.models.contact import Contact
from google_contacts_cisco.models.phone_number import PhoneNumber


@pytest.fixture
def formatter():
    """Create XML formatter."""
    return CiscoXMLFormatter(base_url="http://test.example.com")


@pytest.fixture
def contact_with_phones():
    """Create contact with phone numbers."""
    contact = Contact(
        id=uuid4(),
        resource_name="people/c123",
        display_name="John Doe",
        given_name="John",
        family_name="Doe"
    )
    
    contact.phone_numbers = [
        PhoneNumber(
            id=uuid4(),
            contact_id=contact.id,
            value="+15551234567",
            display_value="(555) 123-4567",
            type="mobile",
            primary=True
        ),
        PhoneNumber(
            id=uuid4(),
            contact_id=contact.id,
            value="+15559876543",
            display_value="(555) 987-6543",
            type="work",
            primary=False
        )
    ]
    
    return contact


class TestMainDirectory:
    """Test main directory menu generation."""
    
    def test_generate_main_directory(self, formatter):
        """Test main directory XML generation."""
        xml_str = formatter.generate_main_directory()
        
        root = etree.fromstring(xml_str.encode('utf-8'))
        
        assert root.tag == "CiscoIPPhoneMenu"
        assert root.find("Title") is not None
        
        menu_items = root.findall("MenuItem")
        assert len(menu_items) == len(GROUP_MAPPINGS)
        
        # Check first menu item structure
        first_item = menu_items[0]
        assert first_item.find("Name") is not None
        assert first_item.find("URL") is not None
    
    def test_main_directory_has_softkeys(self, formatter):
        """Test soft keys in main directory."""
        xml_str = formatter.generate_main_directory()
        root = etree.fromstring(xml_str.encode('utf-8'))
        
        softkeys = root.findall("SoftKeyItem")
        assert len(softkeys) >= 2  # At least Exit and View
        
        # Check softkey structure
        for softkey in softkeys:
            assert softkey.find("Name") is not None
            assert softkey.find("Position") is not None
            assert softkey.find("URL") is not None


class TestGroupDirectory:
    """Test group directory menu generation."""
    
    def test_generate_group_directory(self, formatter, contact_with_phones):
        """Test group directory generation."""
        contacts = [contact_with_phones]
        xml_str = formatter.generate_group_directory("2ABC", contacts)
        
        root = etree.fromstring(xml_str.encode('utf-8'))
        
        assert root.tag == "CiscoIPPhoneMenu"
        assert root.find("Title").text == "2ABC"
        
        menu_items = root.findall("MenuItem")
        assert len(menu_items) == 1
        assert menu_items[0].find("Name").text == "John Doe"
    
    def test_group_directory_urls(self, formatter, contact_with_phones):
        """Test URLs in group directory."""
        contacts = [contact_with_phones]
        xml_str = formatter.generate_group_directory("2ABC", contacts)
        
        root = etree.fromstring(xml_str.encode('utf-8'))
        menu_items = root.findall("MenuItem")
        
        url = menu_items[0].find("URL").text
        assert str(contact_with_phones.id) in url
        assert url.startswith("http://test.example.com/directory/contacts/")


class TestContactDirectory:
    """Test individual contact directory generation."""
    
    def test_generate_contact_directory(self, formatter, contact_with_phones):
        """Test contact directory generation."""
        xml_str = formatter.generate_contact_directory(contact_with_phones)
        
        root = etree.fromstring(xml_str.encode('utf-8'))
        
        assert root.tag == "CiscoIPPhoneDirectory"
        assert root.find("Title").text == "John Doe"
        
        entries = root.findall("DirectoryEntry")
        assert len(entries) == 2  # Two phone numbers
    
    def test_contact_directory_phone_order(self, formatter, contact_with_phones):
        """Test primary phone appears first."""
        xml_str = formatter.generate_contact_directory(contact_with_phones)
        
        root = etree.fromstring(xml_str.encode('utf-8'))
        entries = root.findall("DirectoryEntry")
        
        first_entry = entries[0]
        name = first_entry.find("Name").text
        
        assert "Mobile" in name
        assert "Primary" in name
    
    def test_contact_directory_softkeys(self, formatter, contact_with_phones):
        """Test contact directory soft keys."""
        xml_str = formatter.generate_contact_directory(contact_with_phones)
        
        root = etree.fromstring(xml_str.encode('utf-8'))
        softkeys = root.findall("SoftKeyItem")
        
        assert len(softkeys) == 3  # Exit, Back, Call
        
        softkey_names = [sk.find("Name").text for sk in softkeys]
        assert "Exit" in softkey_names
        assert "Back" in softkey_names
        assert "Call" in softkey_names
    
    def test_contact_without_phones(self, formatter):
        """Test contact with no phone numbers."""
        contact = Contact(
            id=uuid4(),
            resource_name="people/test",
            display_name="No Phone Contact"
        )
        contact.phone_numbers = []
        
        xml_str = formatter.generate_contact_directory(contact)
        root = etree.fromstring(xml_str.encode('utf-8'))
        
        entries = root.findall("DirectoryEntry")
        assert len(entries) == 1
        assert "No phone numbers" in entries[0].find("Name").text


class TestGroupMapping:
    """Test contact to group mapping."""
    
    @pytest.mark.parametrize("name,expected_group", [
        ("Alice", "2ABC"),
        ("Bob", "2ABC"),
        ("Charlie", "2ABC"),
        ("David", "3DEF"),
        ("John", "5JKL"),
        ("Zara", "9WXYZ"),
        ("123 Company", "1"),
        ("@Special", "0"),
    ])
    def test_contact_mapping(self, formatter, name, expected_group):
        """Test contact to group mapping."""
        contact = Contact(
            id=uuid4(),
            resource_name="people/test",
            display_name=name
        )
        
        group = formatter.map_contact_to_group(contact)
        assert group == expected_group


class TestXMLEscaping:
    """Test XML character escaping."""
    
    def test_escape_special_characters(self, formatter):
        """Test XML entity escaping."""
        contact = Contact(
            id=uuid4(),
            resource_name="people/test",
            display_name="John & Jane <Company>"
        )
        contact.phone_numbers = []
        
        xml_str = formatter.generate_contact_directory(contact)
        
        # Should contain escaped characters
        assert "&amp;" in xml_str
        assert "&lt;" in xml_str
        assert "&gt;" in xml_str
        
        # Should parse as valid XML
        root = etree.fromstring(xml_str.encode('utf-8'))
        assert root is not None
    
    def test_no_unescaped_characters(self, formatter):
        """Test that dangerous characters are not unescaped."""
        contact = Contact(
            id=uuid4(),
            resource_name="people/test",
            display_name="Test<script>alert('xss')</script>"
        )
        contact.phone_numbers = []
        
        xml_str = formatter.generate_contact_directory(contact)
        
        # Should not contain unescaped script tags
        assert "<script>" not in xml_str
        assert "&lt;script&gt;" in xml_str


class TestHelpGeneration:
    """Test help text generation."""
    
    def test_generate_main_help(self, formatter):
        """Test main directory help."""
        xml_str = formatter.generate_help("main")
        
        root = etree.fromstring(xml_str.encode('utf-8'))
        
        assert root.tag == "CiscoIPPhoneText"
        assert root.find("Title").text == "Help"
        assert "Directory Help" in root.find("Text").text
    
    def test_generate_group_help(self, formatter):
        """Test group directory help."""
        xml_str = formatter.generate_help("group/2ABC")
        
        root = etree.fromstring(xml_str.encode('utf-8'))
        assert "Group 2ABC Help" in root.find("Text").text
    
    def test_generate_contact_help(self, formatter):
        """Test contact directory help."""
        xml_str = formatter.generate_help("contact")
        
        root = etree.fromstring(xml_str.encode('utf-8'))
        assert "Contact Help" in root.find("Text").text
```

### 5. Test Search Service

Create `tests/unit/services/test_search_service.py`:

```python
"""Test search service."""
import pytest
from uuid import uuid4

from google_contacts_cisco.services.search_service import (
    SearchService,
    SearchResult
)
from google_contacts_cisco.models.contact import Contact
from google_contacts_cisco.models.phone_number import PhoneNumber


@pytest.fixture
def search_service(db_session):
    """Create search service instance."""
    return SearchService(db_session)


@pytest.fixture
def searchable_contacts(db_session):
    """Create contacts for searching."""
    contacts = [
        Contact(
            id=uuid4(),
            resource_name="people/c1",
            display_name="John Doe",
            given_name="John",
            family_name="Doe"
        ),
        Contact(
            id=uuid4(),
            resource_name="people/c2",
            display_name="Jane Doe",
            given_name="Jane",
            family_name="Doe"
        ),
        Contact(
            id=uuid4(),
            resource_name="people/c3",
            display_name="John Smith",
            given_name="John",
            family_name="Smith"
        ),
    ]
    
    # Add phone to first contact
    contacts[0].phone_numbers.append(
        PhoneNumber(
            id=uuid4(),
            contact_id=contacts[0].id,
            value="+15551234567",
            display_value="(555) 123-4567",
            type="mobile",
            primary=True
        )
    )
    
    for contact in contacts:
        db_session.add(contact)
    
    db_session.commit()
    return contacts


class TestBasicSearch:
    """Test basic search functionality."""
    
    def test_search_by_name(self, search_service, searchable_contacts):
        """Test searching by name."""
        results = search_service.search("John")
        
        assert len(results) >= 2
        names = [r.contact.display_name for r in results]
        assert "John Doe" in names
        assert "John Smith" in names
    
    def test_exact_match(self, search_service, searchable_contacts):
        """Test exact name match."""
        results = search_service.search("John Doe")
        
        assert len(results) >= 1
        assert results[0].match_type == "exact"
        assert results[0].contact.display_name == "John Doe"
    
    def test_prefix_match(self, search_service, searchable_contacts):
        """Test prefix matching."""
        results = search_service.search("Jo")
        
        assert len(results) >= 2
        # All results should start with "Jo"
        for result in results:
            assert result.contact.display_name.lower().startswith("jo")
    
    def test_case_insensitive(self, search_service, searchable_contacts):
        """Test case-insensitive search."""
        results_upper = search_service.search("JOHN")
        results_lower = search_service.search("john")
        
        assert len(results_upper) == len(results_lower)
    
    def test_empty_query(self, search_service, searchable_contacts):
        """Test empty query returns no results."""
        results = search_service.search("")
        assert len(results) == 0
        
        results = search_service.search("   ")
        assert len(results) == 0


class TestPhoneSearch:
    """Test phone number search."""
    
    def test_search_by_phone(self, search_service, searchable_contacts):
        """Test searching by phone number."""
        results = search_service.search("555-123-4567")
        
        assert len(results) >= 1
        assert results[0].contact.display_name == "John Doe"
        assert results[0].match_type == "phone"
    
    def test_search_partial_phone(self, search_service, searchable_contacts):
        """Test partial phone search."""
        results = search_service.search("1234567")
        
        assert len(results) >= 1
        assert results[0].contact.display_name == "John Doe"


class TestSearchRanking:
    """Test search result ranking."""
    
    def test_relevance_ranking(self, search_service, searchable_contacts):
        """Test results are ranked by relevance."""
        results = search_service.search("Doe")
        
        if len(results) > 1:
            scores = [r.relevance_score for r in results]
            assert scores == sorted(scores, reverse=True)
    
    def test_exact_before_prefix(self):
        """Test exact matches rank higher than prefix."""
        contact = Contact(
            id=uuid4(),
            resource_name="people/test",
            display_name="Test"
        )
        
        exact = SearchResult(contact, "exact")
        prefix = SearchResult(contact, "prefix")
        
        assert exact.relevance_score > prefix.relevance_score
    
    def test_prefix_before_substring(self):
        """Test prefix matches rank higher than substring."""
        contact = Contact(
            id=uuid4(),
            resource_name="people/test",
            display_name="Test"
        )
        
        prefix = SearchResult(contact, "prefix")
        substring = SearchResult(contact, "substring")
        
        assert prefix.relevance_score > substring.relevance_score


class TestSearchResult:
    """Test SearchResult class."""
    
    def test_to_dict(self, searchable_contacts):
        """Test SearchResult serialization."""
        contact = searchable_contacts[0]
        result = SearchResult(contact, "exact", "display_name")
        
        result_dict = result.to_dict()
        
        assert "id" in result_dict
        assert "display_name" in result_dict
        assert "phone_numbers" in result_dict
        assert "match_type" in result_dict
        assert result_dict["match_type"] == "exact"


class TestSearchEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_no_results(self, search_service, searchable_contacts):
        """Test query with no matches."""
        results = search_service.search("Nonexistent Name")
        assert len(results) == 0
    
    def test_max_results(self, search_service, searchable_contacts):
        """Test max_results parameter."""
        results = search_service.search("o", max_results=1)
        assert len(results) <= 1
    
    def test_deduplication(self, search_service, searchable_contacts):
        """Test results are deduplicated."""
        results = search_service.search("John")
        
        # Check no duplicate IDs
        ids = [r.contact.id for r in results]
        assert len(ids) == len(set(ids))
```

### 6. Run Coverage Report

Create `scripts/test.sh`:

```bash
#!/bin/bash
# Run tests with coverage

echo "Running unit tests..."
uv run pytest tests/unit -v --cov=google_contacts_cisco --cov-report=term-missing --cov-report=html

echo ""
echo "Coverage report generated in htmlcov/index.html"
echo "Open htmlcov/index.html in your browser to view detailed coverage"
```

## Verification

After completing this task:

1. **Run All Tests**:
   ```bash
   uv run pytest tests/unit -v
   ```

2. **Run With Coverage**:
   ```bash
   uv run pytest tests/unit --cov=google_contacts_cisco --cov-report=term-missing
   ```

3. **Generate HTML Coverage Report**:
   ```bash
   uv run pytest tests/unit --cov=google_contacts_cisco --cov-report=html
   # Open htmlcov/index.html
   ```

4. **Run Specific Test File**:
   ```bash
   uv run pytest tests/unit/utils/test_phone_utils.py -v
   ```

5. **Run Tests Matching Pattern**:
   ```bash
   uv run pytest -k "test_phone" -v
   ```

6. **Check Coverage Threshold**:
   ```bash
   uv run pytest --cov=google_contacts_cisco --cov-fail-under=80
   # Will fail if coverage < 80%
   ```

## Notes

- **Fast Tests**: Unit tests should run in <30 seconds
- **Isolated**: Each test is independent, no shared state
- **Fixtures**: Use pytest fixtures for reusable test data
- **Mocking**: Mock external dependencies (Google API, file system)
- **Parametrize**: Use `@pytest.mark.parametrize` for multiple test cases
- **Coverage**: Focus on critical paths and edge cases
- **Maintainability**: Tests should be easy to read and understand

## Common Issues

1. **Slow Tests**: Reduce database operations, use in-memory SQLite
2. **Flaky Tests**: Avoid time-dependent assertions, use freezegun
3. **Import Errors**: Ensure test paths are correct
4. **Fixture Scope**: Use appropriate scope (function, class, module, session)
5. **Mock Leaks**: Reset mocks between tests
6. **Coverage Gaps**: Check htmlcov report for uncovered lines

## Best Practices

- One assertion per test when possible
- Test behavior, not implementation
- Use descriptive test names
- Group related tests in classes
- Test both success and failure paths
- Test edge cases and boundaries
- Keep tests simple and readable
- Don't test external libraries

## Related Documentation

- pytest: https://docs.pytest.org/
- pytest-cov: https://pytest-cov.readthedocs.io/
- pytest-mock: https://pytest-mock.readthedocs.io/
- Coverage.py: https://coverage.readthedocs.io/

## Estimated Time

8-10 hours

