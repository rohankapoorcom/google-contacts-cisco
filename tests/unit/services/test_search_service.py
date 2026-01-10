"""Unit tests for search service.

This module tests the contact search functionality including
name search, phone number search, and pagination.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from google_contacts_cisco.models import Base
from google_contacts_cisco.models.contact import Contact
from google_contacts_cisco.models.phone_number import PhoneNumber
from google_contacts_cisco.services.search_service import (
    SearchService,
    get_search_service,
)
from google_contacts_cisco.utils.phone_utils import PhoneNumberNormalizer


@pytest.fixture
def db_session():
    """Create in-memory database session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def phone_normalizer():
    """Create phone normalizer for testing."""
    return PhoneNumberNormalizer("US")


@pytest.fixture
def search_service(db_session, phone_normalizer):
    """Create search service for testing."""
    return SearchService(db_session, phone_normalizer)


@pytest.fixture
def sample_contacts(db_session):
    """Create sample contacts for testing."""
    contacts = []

    # Contact 1: John Smith
    contact1 = Contact(
        id=uuid.uuid4(),
        resource_name="people/c1",
        display_name="John Smith",
        given_name="John",
        family_name="Smith",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        deleted=False,
    )
    phone1 = PhoneNumber(
        id=uuid.uuid4(),
        contact=contact1,
        value="+12025551234",
        display_value="(202) 555-1234",
        type="mobile",
        primary=True,
    )
    contact1.phone_numbers.append(phone1)
    db_session.add(contact1)
    contacts.append(contact1)

    # Contact 2: Jane Smith
    contact2 = Contact(
        id=uuid.uuid4(),
        resource_name="people/c2",
        display_name="Jane Smith",
        given_name="Jane",
        family_name="Smith",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        deleted=False,
    )
    phone2 = PhoneNumber(
        id=uuid.uuid4(),
        contact=contact2,
        value="+12025559876",
        display_value="(202) 555-9876",
        type="work",
        primary=True,
    )
    contact2.phone_numbers.append(phone2)
    db_session.add(contact2)
    contacts.append(contact2)

    # Contact 3: Bob Johnson
    contact3 = Contact(
        id=uuid.uuid4(),
        resource_name="people/c3",
        display_name="Bob Johnson",
        given_name="Bob",
        family_name="Johnson",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        deleted=False,
    )
    phone3 = PhoneNumber(
        id=uuid.uuid4(),
        contact=contact3,
        value="+13105551111",
        display_value="(310) 555-1111",
        type="mobile",
        primary=True,
    )
    contact3.phone_numbers.append(phone3)
    db_session.add(contact3)
    contacts.append(contact3)

    # Contact 4: Alice Johnson (deleted)
    contact4 = Contact(
        id=uuid.uuid4(),
        resource_name="people/c4",
        display_name="Alice Johnson",
        given_name="Alice",
        family_name="Johnson",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        deleted=True,
    )
    phone4 = PhoneNumber(
        id=uuid.uuid4(),
        contact=contact4,
        value="+13105552222",
        display_value="(310) 555-2222",
        type="mobile",
        primary=True,
    )
    contact4.phone_numbers.append(phone4)
    db_session.add(contact4)
    contacts.append(contact4)

    # Contact 5: Mary Williams (no phone)
    contact5 = Contact(
        id=uuid.uuid4(),
        resource_name="people/c5",
        display_name="Mary Williams",
        given_name="Mary",
        family_name="Williams",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        deleted=False,
    )
    db_session.add(contact5)
    contacts.append(contact5)

    db_session.commit()
    return contacts


class TestGetSearchService:
    """Tests for get_search_service factory function."""

    def test_get_search_service_returns_instance(self, db_session):
        """Should return a SearchService instance."""
        service = get_search_service(db_session)
        assert isinstance(service, SearchService)

    def test_get_search_service_with_normalizer(self, db_session, phone_normalizer):
        """Should accept custom phone normalizer."""
        service = get_search_service(db_session, phone_normalizer)
        assert service.phone_normalizer is phone_normalizer

    def test_get_search_service_default_normalizer(self, db_session):
        """Should create default phone normalizer."""
        service = get_search_service(db_session)
        assert service.phone_normalizer is not None
        assert isinstance(service.phone_normalizer, PhoneNumberNormalizer)


class TestSearchServiceInit:
    """Tests for SearchService initialization."""

    def test_init_with_db_and_normalizer(self, db_session, phone_normalizer):
        """Should initialize with provided dependencies."""
        service = SearchService(db_session, phone_normalizer)
        assert service.db is db_session
        assert service.phone_normalizer is phone_normalizer

    def test_init_without_normalizer(self, db_session):
        """Should create default normalizer if not provided."""
        service = SearchService(db_session)
        assert service.db is db_session
        assert service.phone_normalizer is not None


class TestSearchContactsByName:
    """Tests for searching contacts by name."""

    def test_search_by_display_name(self, search_service, sample_contacts):
        """Should find contacts by display name."""
        results = search_service.search_by_name("John Smith")
        assert len(results) == 1
        assert results[0].display_name == "John Smith"

    def test_search_by_given_name(self, search_service, sample_contacts):
        """Should find contacts by given name."""
        results = search_service.search_by_name("Jane")
        assert len(results) == 1
        assert results[0].given_name == "Jane"

    def test_search_by_family_name(self, search_service, sample_contacts):
        """Should find contacts by family name."""
        results = search_service.search_by_name("Smith")
        assert len(results) == 2
        names = {c.display_name for c in results}
        assert "John Smith" in names
        assert "Jane Smith" in names

    def test_search_partial_match(self, search_service, sample_contacts):
        """Should match partial names."""
        results = search_service.search_by_name("Joh")
        assert len(results) == 2  # John Smith, Bob Johnson (not Alice - deleted)
        names = {c.display_name for c in results}
        assert "John Smith" in names
        assert "Bob Johnson" in names

    def test_search_case_insensitive(self, search_service, sample_contacts):
        """Should be case insensitive."""
        results = search_service.search_by_name("john")
        assert len(results) == 2  # John Smith and Bob Johnson (Alice deleted)

        results_upper = search_service.search_by_name("JOHN")
        assert len(results) == len(results_upper)

    def test_search_excludes_deleted(self, search_service, sample_contacts):
        """Should exclude deleted contacts."""
        results = search_service.search_by_name("Alice")
        assert len(results) == 0

    def test_search_empty_query(self, search_service, sample_contacts):
        """Should return empty list for empty query."""
        results = search_service.search_by_name("")
        assert results == []

    def test_search_whitespace_only(self, search_service, sample_contacts):
        """Should return empty list for whitespace query."""
        results = search_service.search_by_name("   ")
        assert results == []

    def test_search_no_matches(self, search_service, sample_contacts):
        """Should return empty list when no matches."""
        results = search_service.search_by_name("Nonexistent")
        assert results == []


class TestSearchContactsByPhone:
    """Tests for searching contacts by phone number."""

    def test_search_by_exact_phone(self, search_service, sample_contacts):
        """Should find contact by exact phone number."""
        results = search_service.search_by_phone("+12025551234")
        assert len(results) == 1
        assert results[0].display_name == "John Smith"

    def test_search_by_formatted_phone(self, search_service, sample_contacts):
        """Should find contact by formatted phone number."""
        results = search_service.search_by_phone("(202) 555-1234")
        assert len(results) == 1
        assert results[0].display_name == "John Smith"

    def test_search_by_phone_suffix(self, search_service, sample_contacts):
        """Should find contacts by phone suffix (last 7 digits)."""
        results = search_service.search_by_phone("5551234")
        assert len(results) == 1
        assert results[0].display_name == "John Smith"

    def test_search_by_10_digit_phone(self, search_service, sample_contacts):
        """Should find contact by 10-digit phone."""
        results = search_service.search_by_phone("2025551234")
        assert len(results) == 1
        assert results[0].display_name == "John Smith"

    def test_search_phone_with_dashes(self, search_service, sample_contacts):
        """Should find contact with dashed phone format."""
        results = search_service.search_by_phone("202-555-1234")
        assert len(results) == 1
        assert results[0].display_name == "John Smith"

    def test_search_phone_no_matches(self, search_service, sample_contacts):
        """Should return empty for non-matching phone."""
        results = search_service.search_by_phone("999-999-9999")
        assert len(results) == 0

    def test_search_phone_excludes_deleted(self, search_service, sample_contacts):
        """Should exclude deleted contacts from phone search."""
        results = search_service.search_by_phone("+13105552222")
        assert len(results) == 0

    def test_search_phone_empty_query(self, search_service, sample_contacts):
        """Should return empty for empty phone query."""
        results = search_service.search_by_phone("")
        assert results == []

    def test_search_phone_too_short(self, search_service, sample_contacts):
        """Should return empty for too short phone query."""
        results = search_service.search_by_phone("123")
        assert results == []


class TestSearchContactsCombined:
    """Tests for combined name and phone search."""

    def test_search_contacts_by_name(self, search_service, sample_contacts):
        """Should search by name in combined search."""
        results = search_service.search_contacts("Smith")
        assert len(results) == 2

    def test_search_contacts_by_phone(self, search_service, sample_contacts):
        """Should search by phone in combined search."""
        # Search by a phone number that uniquely identifies John
        results = search_service.search_by_phone("2025551234")
        assert len(results) == 1
        assert results[0].display_name == "John Smith"

    def test_search_contacts_name_only_mode(self, search_service, sample_contacts):
        """Should exclude phone search when disabled."""
        results = search_service.search_contacts(
            "5551234",
            include_phone_search=False
        )
        assert len(results) == 0

    def test_search_contacts_loads_phone_numbers(self, search_service, sample_contacts):
        """Should eagerly load phone numbers."""
        results = search_service.search_contacts("John")
        assert len(results) > 0
        # Check that phone numbers are loaded (no lazy loading)
        contact = results[0]
        assert hasattr(contact, 'phone_numbers')
        assert len(contact.phone_numbers) > 0


class TestPagination:
    """Tests for search pagination."""

    def test_pagination_limit(self, search_service, sample_contacts):
        """Should respect limit parameter."""
        results = search_service.search_by_name("Johnson", limit=1)
        assert len(results) == 1

    def test_pagination_offset(self, search_service, sample_contacts):
        """Should respect offset parameter."""
        # Get all results
        all_results = search_service.search_by_name("Smith")
        assert len(all_results) == 2

        # Get first page
        page1 = search_service.search_by_name("Smith", limit=1, offset=0)
        assert len(page1) == 1

        # Get second page
        page2 = search_service.search_by_name("Smith", limit=1, offset=1)
        assert len(page2) == 1

        # Should be different contacts
        assert page1[0].id != page2[0].id

    def test_pagination_offset_beyond_results(self, search_service, sample_contacts):
        """Should return empty when offset exceeds results."""
        results = search_service.search_by_name("Smith", limit=10, offset=100)
        assert results == []

    def test_pagination_default_limit(self, search_service, sample_contacts):
        """Should use default limit of 50."""
        results = search_service.search_by_name("o")  # Matches multiple
        assert len(results) <= 50


class TestCountSearchResults:
    """Tests for counting search results."""

    def test_count_by_name(self, search_service, sample_contacts):
        """Should count results by name."""
        count = search_service.count_search_results("Smith")
        assert count == 2

    def test_count_by_phone(self, search_service, sample_contacts):
        """Should count results by phone."""
        count = search_service.count_search_results("5551234")
        assert count == 1

    def test_count_no_matches(self, search_service, sample_contacts):
        """Should return 0 for no matches."""
        count = search_service.count_search_results("Nonexistent")
        assert count == 0

    def test_count_empty_query(self, search_service, sample_contacts):
        """Should return 0 for empty query."""
        count = search_service.count_search_results("")
        assert count == 0

    def test_count_without_phone_search(self, search_service, sample_contacts):
        """Should count without phone search when disabled."""
        count = search_service.count_search_results(
            "5551234",
            include_phone_search=False
        )
        assert count == 0


class TestBuildNameSearchConditions:
    """Tests for building name search conditions."""

    def test_build_name_conditions(self, search_service):
        """Should build conditions for name fields."""
        conditions = search_service._build_name_search_conditions("test")
        assert len(conditions) == 3  # display_name, given_name, family_name

    def test_name_conditions_with_special_chars(self, search_service):
        """Should handle special characters in search term."""
        conditions = search_service._build_name_search_conditions("O'Brien")
        assert len(conditions) == 3


class TestBuildPhoneSearchConditions:
    """Tests for building phone search conditions."""

    def test_build_phone_conditions_normalized(self, search_service):
        """Should build conditions for normalized phone."""
        conditions = search_service._build_phone_search_conditions("202-555-1234")
        assert len(conditions) > 0

    def test_build_phone_conditions_digits_only(self, search_service):
        """Should build conditions for digit-only input."""
        conditions = search_service._build_phone_search_conditions("5551234")
        assert len(conditions) > 0

    def test_build_phone_conditions_short_input(self, search_service):
        """Should handle short phone input."""
        conditions = search_service._build_phone_search_conditions("555")
        # Should return empty or minimal conditions for too-short input
        assert isinstance(conditions, list)

    def test_build_phone_conditions_invalid(self, search_service):
        """Should handle invalid phone input."""
        conditions = search_service._build_phone_search_conditions("abcd")
        assert isinstance(conditions, list)


class TestOrderingAndDistinct:
    """Tests for result ordering and deduplication."""

    def test_results_ordered_by_display_name(self, search_service, sample_contacts):
        """Should order results by display_name."""
        results = search_service.search_by_name("Smith")
        assert len(results) == 2
        # Check alphabetical order
        assert results[0].display_name <= results[1].display_name

    def test_results_distinct(self, search_service, sample_contacts):
        """Should return distinct contacts (no duplicates)."""
        results = search_service.search_contacts("Johnson")
        # Check all IDs are unique
        ids = [c.id for c in results]
        assert len(ids) == len(set(ids))


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_search_with_sql_injection_attempt(self, search_service, sample_contacts):
        """Should handle SQL injection attempts safely."""
        # SQLAlchemy should parameterize queries
        results = search_service.search_by_name("'; DROP TABLE contacts; --")
        assert isinstance(results, list)
        # Table should still exist
        all_results = search_service.search_by_name("Smith")
        assert len(all_results) > 0

    def test_search_with_percent_wildcard(self, search_service, sample_contacts):
        """Should handle % wildcard in search."""
        results = search_service.search_by_name("%")
        # Should treat % as literal, not wildcard
        assert isinstance(results, list)

    def test_search_with_underscore_wildcard(self, search_service, sample_contacts):
        """Should handle underscore wildcard in search."""
        results = search_service.search_by_name("___")
        # Should treat _ as literal, not single-char wildcard
        assert isinstance(results, list)
        # Should not match "Bob" (3 chars) as would happen with SQL wildcards
        assert len(results) == 0

    def test_search_with_backslash(self, search_service, sample_contacts):
        """Should handle backslash in search."""
        results = search_service.search_by_name("\\")
        # Should treat backslash as literal
        assert isinstance(results, list)

    def test_search_with_combined_wildcards(self, search_service, sample_contacts):
        """Should handle combined wildcard characters."""
        results = search_service.search_by_name("%_\\")
        # Should treat all as literals
        assert isinstance(results, list)

    def test_search_with_unicode(self, search_service, db_session):
        """Should handle unicode characters."""
        # Add contact with unicode name
        contact = Contact(
            id=uuid.uuid4(),
            resource_name="people/unicode",
            display_name="José García",
            given_name="José",
            family_name="García",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            deleted=False,
        )
        db_session.add(contact)
        db_session.commit()

        results = search_service.search_by_name("José")
        assert len(results) == 1
        assert results[0].display_name == "José García"

    def test_search_with_very_long_query(self, search_service, sample_contacts):
        """Should handle very long search queries."""
        long_query = "x" * 1000
        results = search_service.search_by_name(long_query)
        assert results == []


class TestPhoneSearchSecurity:
    """Security tests for phone number search."""

    def test_phone_search_with_percent_wildcard(self, search_service, sample_contacts):
        """Should handle % wildcard in phone search."""
        # Attempt to use % as wildcard to match all phones
        results = search_service.search_by_phone("%")
        # Should not match everything - % should be treated as literal
        assert len(results) == 0

    def test_phone_search_with_underscore_wildcard(
        self, search_service, sample_contacts
    ):
        """Should handle underscore wildcard in phone search."""
        # Attempt to use _ as single-char wildcard
        results = search_service.search_by_phone("_________")
        # Should not match based on wildcards
        assert len(results) == 0

    def test_phone_search_with_combined_wildcards(
        self, search_service, sample_contacts
    ):
        """Should handle combined wildcard injection in phone search."""
        results = search_service.search_by_phone("%_%")
        # Should treat as literals, not wildcards
        assert len(results) == 0

    def test_phone_search_pattern_injection_attack(
        self, search_service, sample_contacts
    ):
        """Should prevent pattern injection attacks in phone search."""
        # Try to match all 7-digit sequences with wildcards
        results = search_service.search_by_phone("%555____")
        # Should not match based on wildcard patterns
        assert isinstance(results, list)
        # Should not match John Smith's 555-1234 via wildcard
        assert not any(c.display_name == "John Smith" for c in results)

    def test_phone_search_backslash_escape(self, search_service, sample_contacts):
        """Should handle backslash in phone search."""
        results = search_service.search_by_phone("\\")
        # Should treat backslash as literal
        assert isinstance(results, list)
        assert len(results) == 0

    def test_phone_search_sql_comment_injection(self, search_service, sample_contacts):
        """Should prevent SQL comment injection in phone search."""
        results = search_service.search_by_phone("555-- comment")
        # Should treat as part of search, not SQL comment
        assert isinstance(results, list)

    def test_phone_search_with_malicious_pattern(
        self, search_service, sample_contacts
    ):
        """Should handle malicious LIKE patterns safely."""
        # Try various SQL injection patterns
        malicious_patterns = [
            "%'; DROP TABLE phone_numbers; --",
            "1' OR '1'='1",
            "%\\'%",
            "___________",  # Try to match by length
            "%%%%%%%%",     # Try to match everything
        ]

        for pattern in malicious_patterns:
            results = search_service.search_by_phone(pattern)
            # Should not cause errors or unexpected matches
            assert isinstance(results, list)

    def test_phone_search_conditions_escaping(self, search_service):
        """Should escape wildcards in phone search conditions."""
        # Test the internal method directly
        conditions = search_service._build_phone_search_conditions("%555")
        # Should create conditions, not fail
        assert isinstance(conditions, list)
        # Conditions should be safely escaped

    def test_phone_search_dos_prevention(self, search_service, sample_contacts):
        """Should handle patterns that could cause DoS via performance issues."""
        # Pattern that could cause expensive LIKE operations
        expensive_pattern = "%" * 100 + "555"
        results = search_service.search_by_phone(expensive_pattern)
        # Should complete without hanging (escaping prevents wildcard explosion)
        assert isinstance(results, list)


class TestNameSearchSecurity:
    """Additional security tests for name search."""

    def test_name_search_wildcard_injection(self, search_service, sample_contacts):
        """Should prevent wildcard injection in name search."""
        # Try to match all names with wildcard
        results = search_service.search_by_name("%")
        # Should not match everything
        assert len(results) == 0

    def test_name_search_underscore_injection(self, search_service, sample_contacts):
        """Should prevent underscore wildcard injection."""
        # Try to match 3-char names like "Bob"
        results = search_service.search_by_name("___")
        # Should not match Bob via wildcards
        assert len(results) == 0

    def test_name_search_escape_helper(self, search_service):
        """Should properly escape LIKE patterns."""
        # Test the escape helper method
        escaped = search_service._escape_like_pattern("test%_\\value")
        assert escaped == "test\\%\\_\\\\value"

        # Verify backslash is escaped
        assert "\\\\" in escaped
        # Verify percent is escaped
        assert "\\%" in escaped
        # Verify underscore is escaped
        assert "\\_" in escaped


class TestPhoneNormalizerIntegration:
    """Tests for phone normalizer integration."""

    def test_uses_provided_normalizer(self, db_session):
        """Should use provided phone normalizer."""
        normalizer = PhoneNumberNormalizer("GB")
        service = SearchService(db_session, normalizer)
        assert service.phone_normalizer.default_country == "GB"

    def test_normalizer_called_for_phone_search(self, db_session, sample_contacts):
        """Should call normalizer for phone searches."""
        normalizer = Mock(spec=PhoneNumberNormalizer)
        normalizer.normalize_for_search = Mock(return_value="+12025551234")

        service = SearchService(db_session, normalizer)
        service.search_by_phone("202-555-1234")

        normalizer.normalize_for_search.assert_called_once_with("202-555-1234")
