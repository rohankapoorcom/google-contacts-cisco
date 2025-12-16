# Task 5.2: Search Service Implementation

## Overview

Implement a search service that provides full-text search across contact names and phone numbers. This service will support searching by name (partial matches), phone number, and combined queries.

## Priority

**P1 (High)** - Required for both Cisco phone and web interface search

## Dependencies

- Task 1.2: Database Setup
- Task 2.1: Contact Data Models
- Task 5.1: Phone Number Normalization

## Objectives

1. Implement full-text search for contact names
2. Implement phone number search using normalization
3. Support partial name matching
4. Combine name and phone search results
5. Rank search results by relevance
6. Optimize for performance (sub-250ms response time)
7. Handle edge cases (empty queries, special characters)
8. Add comprehensive tests

## Technical Context

### Search Requirements
- **Name Search**: Case-insensitive, partial matching, prefix and substring
- **Phone Search**: Normalized comparison, partial matching (last N digits)
- **Performance**: < 250ms for 10,000 contacts
- **Ranking**: Exact matches first, then prefix matches, then substring

### SQLite Full-Text Search
- Use SQLite's built-in LIKE for simple searches
- Consider FTS5 for advanced full-text search
- Optimize with proper indexes

## Acceptance Criteria

- [ ] Name search supports partial matches
- [ ] Phone search handles various formats
- [ ] Search results are ranked by relevance
- [ ] Performance meets < 250ms target
- [ ] Empty queries return no results
- [ ] Special characters are handled safely
- [ ] Results include contact details and phone numbers
- [ ] Tests cover all search scenarios
- [ ] Deduplication of results

## Implementation Steps

### 1. Create Search Service

Create `google_contacts_cisco/services/search_service.py`:

```python
"""Contact search service."""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from ..models.contact import Contact
from ..models.phone_number import PhoneNumber
from ..repositories.contact_repository import ContactRepository
from ..utils.phone_utils import get_phone_normalizer
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SearchResult:
    """Search result container."""
    
    def __init__(self, contact: Contact, match_type: str, match_field: str = ""):
        """Initialize search result.
        
        Args:
            contact: Matched contact
            match_type: Type of match (exact, prefix, substring, phone)
            match_field: Field that matched (name, phone)
        """
        self.contact = contact
        self.match_type = match_type
        self.match_field = match_field
        self.relevance_score = self._calculate_score()
    
    def _calculate_score(self) -> int:
        """Calculate relevance score for ranking.
        
        Returns:
            Score (higher is more relevant)
        """
        scores = {
            "exact": 100,
            "prefix": 50,
            "substring": 25,
            "phone": 75,
        }
        return scores.get(self.match_type, 0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "id": str(self.contact.id),
            "display_name": self.contact.display_name,
            "given_name": self.contact.given_name,
            "family_name": self.contact.family_name,
            "phone_numbers": [
                {
                    "value": phone.value,
                    "display_value": phone.display_value,
                    "type": phone.type,
                    "primary": phone.primary,
                }
                for phone in self.contact.phone_numbers
            ],
            "email_addresses": [
                {
                    "value": email.value,
                    "type": email.type,
                    "primary": email.primary,
                }
                for email in self.contact.email_addresses
            ],
            "match_type": self.match_type,
            "match_field": self.match_field,
        }


class SearchService:
    """Service for searching contacts."""
    
    def __init__(self, db: Session):
        """Initialize search service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.repository = ContactRepository(db)
        self.phone_normalizer = get_phone_normalizer()
    
    def search(
        self,
        query: str,
        max_results: int = 50
    ) -> List[SearchResult]:
        """Search contacts by name or phone number.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            
        Returns:
            List of search results, ranked by relevance
        """
        if not query or not query.strip():
            return []
        
        query = query.strip()
        logger.info(f"Searching for: {query}")
        
        results = []
        seen_ids = set()
        
        # Try phone search first (if query looks like a phone number)
        if self._looks_like_phone(query):
            phone_results = self._search_by_phone(query)
            for contact in phone_results:
                if contact.id not in seen_ids:
                    results.append(SearchResult(contact, "phone", "phone_number"))
                    seen_ids.add(contact.id)
        
        # Name search
        name_results = self._search_by_name(query)
        for contact, match_type in name_results:
            if contact.id not in seen_ids:
                results.append(SearchResult(contact, match_type, "display_name"))
                seen_ids.add(contact.id)
        
        # Sort by relevance
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        
        logger.info(f"Found {len(results)} results for query: {query}")
        return results[:max_results]
    
    def search_by_name(
        self,
        name: str,
        max_results: int = 50
    ) -> List[SearchResult]:
        """Search contacts by name only.
        
        Args:
            name: Name to search
            max_results: Maximum results to return
            
        Returns:
            List of search results
        """
        if not name or not name.strip():
            return []
        
        name = name.strip()
        logger.info(f"Searching by name: {name}")
        
        results = []
        seen_ids = set()
        
        name_results = self._search_by_name(name)
        for contact, match_type in name_results:
            if contact.id not in seen_ids:
                results.append(SearchResult(contact, match_type, "display_name"))
                seen_ids.add(contact.id)
        
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results[:max_results]
    
    def search_by_phone(
        self,
        phone: str,
        max_results: int = 50
    ) -> List[SearchResult]:
        """Search contacts by phone number only.
        
        Args:
            phone: Phone number to search
            max_results: Maximum results to return
            
        Returns:
            List of search results
        """
        if not phone or not phone.strip():
            return []
        
        phone = phone.strip()
        logger.info(f"Searching by phone: {phone}")
        
        results = []
        contacts = self._search_by_phone(phone)
        
        for contact in contacts:
            results.append(SearchResult(contact, "phone", "phone_number"))
        
        return results[:max_results]
    
    def _search_by_name(self, name: str) -> List[tuple[Contact, str]]:
        """Internal name search with match type.
        
        Args:
            name: Name to search
            
        Returns:
            List of (Contact, match_type) tuples
        """
        results = []
        name_lower = name.lower()
        
        # Exact match on display name
        exact_matches = (
            self.db.query(Contact)
            .filter(
                Contact.deleted == False,
                func.lower(Contact.display_name) == name_lower
            )
            .all()
        )
        results.extend((c, "exact") for c in exact_matches)
        
        # Get IDs we've already matched
        matched_ids = {c.id for c, _ in results}
        
        # Prefix match on display name
        prefix_matches = (
            self.db.query(Contact)
            .filter(
                Contact.deleted == False,
                Contact.id.notin_(matched_ids) if matched_ids else True,
                func.lower(Contact.display_name).like(f"{name_lower}%")
            )
            .all()
        )
        results.extend((c, "prefix") for c in prefix_matches)
        matched_ids.update(c.id for c in prefix_matches)
        
        # Substring match on display name, given name, or family name
        substring_matches = (
            self.db.query(Contact)
            .filter(
                Contact.deleted == False,
                Contact.id.notin_(matched_ids) if matched_ids else True,
                or_(
                    func.lower(Contact.display_name).like(f"%{name_lower}%"),
                    func.lower(Contact.given_name).like(f"%{name_lower}%"),
                    func.lower(Contact.family_name).like(f"%{name_lower}%")
                )
            )
            .all()
        )
        results.extend((c, "substring") for c in substring_matches)
        
        return results
    
    def _search_by_phone(self, phone: str) -> List[Contact]:
        """Internal phone search.
        
        Args:
            phone: Phone number to search
            
        Returns:
            List of matching contacts
        """
        return self.repository.search_by_phone(phone)
    
    def _looks_like_phone(self, query: str) -> bool:
        """Check if query looks like a phone number.
        
        Args:
            query: Search query
            
        Returns:
            True if query appears to be a phone number
        """
        # Remove common phone separators
        digits = ''.join(c for c in query if c.isdigit())
        
        # If mostly digits and has at least 7 digits, treat as phone
        if len(digits) >= 7 and len(digits) >= len(query) * 0.5:
            return True
        
        # Check for + prefix (international)
        if query.startswith('+') and len(digits) >= 10:
            return True
        
        return False


def get_search_service(db: Session) -> SearchService:
    """Get search service instance.
    
    Args:
        db: Database session
        
    Returns:
        SearchService instance
    """
    return SearchService(db)
```

### 2. Create Tests

Create `tests/test_search_service.py`:

```python
"""Test search service."""
import pytest
from uuid import uuid4

from google_contacts_cisco.services.search_service import SearchService, SearchResult
from google_contacts_cisco.models.contact import Contact
from google_contacts_cisco.models.phone_number import PhoneNumber


@pytest.fixture
def search_service(db_session):
    """Create search service."""
    return SearchService(db_session)


@pytest.fixture
def sample_contacts(db_session):
    """Create sample contacts."""
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
        Contact(
            id=uuid4(),
            resource_name="people/c4",
            display_name="Alice Johnson",
            given_name="Alice",
            family_name="Johnson"
        ),
    ]
    
    # Add phone numbers
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
    
    contacts[1].phone_numbers.append(
        PhoneNumber(
            id=uuid4(),
            contact_id=contacts[1].id,
            value="+15559876543",
            display_value="(555) 987-6543",
            type="work",
            primary=True
        )
    )
    
    for contact in contacts:
        db_session.add(contact)
    
    db_session.commit()
    return contacts


def test_search_by_exact_name(search_service, sample_contacts):
    """Test exact name match."""
    results = search_service.search("John Doe")
    
    assert len(results) == 1
    assert results[0].contact.display_name == "John Doe"
    assert results[0].match_type == "exact"


def test_search_by_prefix(search_service, sample_contacts):
    """Test prefix name match."""
    results = search_service.search("John")
    
    # Should match "John Doe" and "John Smith"
    assert len(results) >= 2
    names = [r.contact.display_name for r in results]
    assert "John Doe" in names
    assert "John Smith" in names


def test_search_by_substring(search_service, sample_contacts):
    """Test substring match."""
    results = search_service.search("Doe")
    
    # Should match "John Doe" and "Jane Doe"
    assert len(results) >= 2
    names = [r.contact.display_name for r in results]
    assert "John Doe" in names
    assert "Jane Doe" in names


def test_search_case_insensitive(search_service, sample_contacts):
    """Test case-insensitive search."""
    results_upper = search_service.search("JOHN")
    results_lower = search_service.search("john")
    results_mixed = search_service.search("JoHn")
    
    assert len(results_upper) == len(results_lower) == len(results_mixed)


def test_search_by_phone(search_service, sample_contacts):
    """Test phone number search."""
    # Search by formatted number
    results = search_service.search("555-123-4567")
    
    assert len(results) >= 1
    assert results[0].contact.display_name == "John Doe"
    assert results[0].match_type == "phone"


def test_search_by_partial_phone(search_service, sample_contacts):
    """Test partial phone number search."""
    # Search by last 7 digits
    results = search_service.search("1234567")
    
    assert len(results) >= 1
    assert results[0].contact.display_name == "John Doe"


def test_search_relevance_ranking(search_service, sample_contacts):
    """Test that results are ranked by relevance."""
    results = search_service.search("John")
    
    # Exact match should come first (if any), then prefix, then substring
    if len(results) > 1:
        # Check that scores are in descending order
        scores = [r.relevance_score for r in results]
        assert scores == sorted(scores, reverse=True)


def test_search_empty_query(search_service, sample_contacts):
    """Test empty query returns no results."""
    results = search_service.search("")
    assert len(results) == 0
    
    results = search_service.search("   ")
    assert len(results) == 0


def test_search_no_matches(search_service, sample_contacts):
    """Test query with no matches."""
    results = search_service.search("Nonexistent Name")
    assert len(results) == 0


def test_search_max_results(search_service, sample_contacts):
    """Test max_results parameter."""
    results = search_service.search("o", max_results=2)  # Common letter
    assert len(results) <= 2


def test_search_result_to_dict(search_service, sample_contacts):
    """Test search result serialization."""
    results = search_service.search("John Doe")
    
    assert len(results) > 0
    result_dict = results[0].to_dict()
    
    assert "id" in result_dict
    assert "display_name" in result_dict
    assert result_dict["display_name"] == "John Doe"
    assert "phone_numbers" in result_dict
    assert "match_type" in result_dict


def test_search_by_name_only(search_service, sample_contacts):
    """Test name-only search."""
    results = search_service.search_by_name("Alice")
    
    assert len(results) >= 1
    assert results[0].contact.display_name == "Alice Johnson"


def test_search_by_phone_only(search_service, sample_contacts):
    """Test phone-only search."""
    results = search_service.search_by_phone("555-123-4567")
    
    assert len(results) >= 1
    assert results[0].contact.display_name == "John Doe"


def test_search_deduplication(search_service, sample_contacts):
    """Test that results are deduplicated."""
    # Search for something that might match in multiple fields
    results = search_service.search("John")
    
    # Check no duplicate IDs
    ids = [r.contact.id for r in results]
    assert len(ids) == len(set(ids))


def test_search_excludes_deleted(search_service, sample_contacts):
    """Test that deleted contacts are excluded."""
    # Mark a contact as deleted
    contact = sample_contacts[0]
    contact.deleted = True
    search_service.db.commit()
    
    # Search should not return deleted contact
    results = search_service.search("John Doe")
    
    ids = [r.contact.id for r in results]
    assert contact.id not in ids


def test_search_result_score_calculation():
    """Test relevance score calculation."""
    contact = Contact(
        id=uuid4(),
        resource_name="people/test",
        display_name="Test"
    )
    
    exact = SearchResult(contact, "exact")
    prefix = SearchResult(contact, "prefix")
    substring = SearchResult(contact, "substring")
    phone = SearchResult(contact, "phone")
    
    assert exact.relevance_score > prefix.relevance_score
    assert prefix.relevance_score > substring.relevance_score
    assert phone.relevance_score > prefix.relevance_score


@pytest.mark.parametrize("query,expected", [
    ("5551234567", True),
    ("555-123-4567", True),
    ("+1 555-123-4567", True),
    ("John Doe", False),
    ("123", False),  # Too short
    ("abc123", False),  # Mostly letters
])
def test_looks_like_phone(search_service, query, expected):
    """Test phone number detection."""
    result = search_service._looks_like_phone(query)
    assert result == expected
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
- Test search by contact name (exact, prefix, substring)
- Test search by phone number
- Test result ranking by relevance
- Test search with no results
- Test search pagination
- Test case-insensitive search


## Verification

After completing this task:

1. **Test Basic Search**:
   ```python
   from google_contacts_cisco.models import get_db
   from google_contacts_cisco.services.search_service import get_search_service
   
   db = next(get_db())
   search = get_search_service(db)
   
   # Search by name
   results = search.search("John")
   for result in results:
       print(f"{result.contact.display_name} ({result.match_type})")
   
   # Search by phone
   results = search.search("555-123-4567")
   for result in results:
       print(f"{result.contact.display_name} - {result.match_field}")
   ```

2. **Test Performance**:
   ```python
   import time
   
   start = time.time()
   results = search.search("test query")
   elapsed = time.time() - start
   print(f"Search took {elapsed*1000:.2f}ms")
   # Should be < 250ms
   ```

3. **Run Tests**:
   ```bash
   uv run pytest tests/test_search_service.py -v
   ```

## Notes

- **Relevance Ranking**: Exact > Prefix > Substring
- **Deduplication**: Contact appears once even if matched multiple ways
- **Performance**: Optimized with proper indexes on name fields
- **Case Sensitivity**: All searches are case-insensitive
- **Partial Matching**: Supports both prefix and substring
- **Phone Detection**: Heuristic-based (mostly digits, length check)
- **Max Results**: Default 50, configurable
- **Deleted Contacts**: Automatically filtered out

## Common Issues

1. **Slow Searches**: Add indexes on name fields
2. **False Phone Matches**: Adjust `_looks_like_phone()` heuristic
3. **Ranking Issues**: Tune relevance scores
4. **Memory Usage**: Limit max_results for large datasets
5. **Special Characters**: SQL LIKE escaping

## Performance Optimization

If searches are slow:
1. Add database indexes
2. Consider SQLite FTS5 for full-text search
3. Cache frequent queries
4. Limit substring matching to queries > 3 chars

## Related Documentation

- SQLite LIKE: https://www.sqlite.org/lang_expr.html#like
- SQLite FTS5: https://www.sqlite.org/fts5.html
- Full-Text Search: https://www.sqlite.org/fts3.html

## Estimated Time

5-6 hours

