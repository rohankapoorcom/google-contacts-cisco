"""Unit tests for phone number utilities.

This module tests the phone number normalization and matching functionality
including E.164 normalization, display formatting, and search matching.
"""

import pytest

from google_contacts_cisco.utils.phone_utils import (
    PhoneNumberNormalizer,
    get_phone_normalizer,
)


class TestGetPhoneNormalizer:
    """Tests for get_phone_normalizer factory function."""

    def test_get_phone_normalizer_returns_instance(self):
        """Should return a PhoneNumberNormalizer instance."""
        normalizer = get_phone_normalizer()
        assert isinstance(normalizer, PhoneNumberNormalizer)

    def test_get_phone_normalizer_default_country(self):
        """Should use US as default country."""
        normalizer = get_phone_normalizer()
        assert normalizer.default_country == "US"

    def test_get_phone_normalizer_custom_country(self):
        """Should use provided country code."""
        normalizer = get_phone_normalizer("GB")
        assert normalizer.default_country == "GB"


class TestPhoneNumberNormalizerInit:
    """Tests for PhoneNumberNormalizer initialization."""

    def test_init_default_country(self):
        """Should default to US country code."""
        normalizer = PhoneNumberNormalizer()
        assert normalizer.default_country == "US"

    def test_init_custom_country(self):
        """Should accept custom country code."""
        normalizer = PhoneNumberNormalizer("DE")
        assert normalizer.default_country == "DE"


class TestNormalizeUSNumbers:
    """Tests for normalizing US phone numbers.

    Note: Uses 202 (Washington DC) area code as 555 is a fictional prefix
    that the phonenumbers library marks as invalid.
    """

    @pytest.fixture
    def normalizer(self):
        """Create a US phone normalizer."""
        return PhoneNumberNormalizer("US")

    def test_normalize_10_digit_us_number(self, normalizer):
        """Should normalize 10-digit US number to E.164."""
        normalized, display = normalizer.normalize("2025551234")
        assert normalized == "+12025551234"

    def test_normalize_us_with_dashes(self, normalizer):
        """Should normalize US number with dashes."""
        normalized, display = normalizer.normalize("202-555-1234")
        assert normalized == "+12025551234"

    def test_normalize_us_with_parentheses(self, normalizer):
        """Should normalize US number with parentheses."""
        normalized, display = normalizer.normalize("(202) 555-1234")
        assert normalized == "+12025551234"

    def test_normalize_us_with_country_code(self, normalizer):
        """Should normalize US number with country code prefix."""
        normalized, display = normalizer.normalize("+1 202 555 1234")
        assert normalized == "+12025551234"

    def test_normalize_us_with_1_prefix(self, normalizer):
        """Should normalize US number with 1- prefix."""
        normalized, display = normalizer.normalize("1-202-555-1234")
        assert normalized == "+12025551234"

    def test_normalize_us_with_dots(self, normalizer):
        """Should normalize US number with dot separators."""
        normalized, display = normalizer.normalize("202.555.1234")
        assert normalized == "+12025551234"

    def test_normalize_us_with_slashes(self, normalizer):
        """Should normalize US number with slash separators."""
        normalized, display = normalizer.normalize("202/555/1234")
        assert normalized == "+12025551234"

    def test_normalize_us_with_spaces(self, normalizer):
        """Should normalize US number with space separators."""
        normalized, display = normalizer.normalize("202 555 1234")
        assert normalized == "+12025551234"


class TestNormalizeInternationalNumbers:
    """Tests for normalizing international phone numbers."""

    @pytest.fixture
    def normalizer(self):
        """Create a US default normalizer."""
        return PhoneNumberNormalizer("US")

    def test_normalize_uk_number(self, normalizer):
        """Should normalize UK phone number."""
        normalized, display = normalizer.normalize("+44 20 7946 0958")
        assert normalized == "+442079460958"

    def test_normalize_french_number(self, normalizer):
        """Should normalize French phone number."""
        normalized, display = normalizer.normalize("+33 1 42 86 82 00")
        assert normalized == "+33142868200"

    def test_normalize_german_number(self, normalizer):
        """Should normalize German phone number."""
        normalized, display = normalizer.normalize("+49 30 12345678")
        assert normalized == "+493012345678"

    def test_normalize_australian_number(self, normalizer):
        """Should normalize Australian phone number."""
        normalized, display = normalizer.normalize("+61 2 1234 5678")
        assert normalized == "+61212345678"


class TestNormalizeWithExtensions:
    """Tests for normalizing numbers with extensions."""

    @pytest.fixture
    def normalizer(self):
        """Create a US normalizer."""
        return PhoneNumberNormalizer("US")

    def test_normalize_with_ext(self, normalizer):
        """Should strip 'ext' extension."""
        normalized, display = normalizer.normalize("202-555-1234 ext 123")
        assert normalized == "+12025551234"

    def test_normalize_with_x(self, normalizer):
        """Should strip 'x' extension."""
        normalized, display = normalizer.normalize("202-555-1234 x123")
        assert normalized == "+12025551234"

    def test_normalize_with_extension_word(self, normalizer):
        """Should strip 'extension' word."""
        normalized, display = normalizer.normalize("202-555-1234 extension 123")
        assert normalized == "+12025551234"

    def test_normalize_with_ext_dot(self, normalizer):
        """Should strip 'ext.' extension with dot."""
        normalized, display = normalizer.normalize("202-555-1234 ext. 456")
        assert normalized == "+12025551234"


class TestNormalizeInvalidNumbers:
    """Tests for handling invalid phone numbers."""

    @pytest.fixture
    def normalizer(self):
        """Create a US normalizer."""
        return PhoneNumberNormalizer("US")

    def test_normalize_too_short(self, normalizer):
        """Should return None for numbers too short."""
        normalized, display = normalizer.normalize("123")
        assert normalized is None

    def test_normalize_letters_only(self, normalizer):
        """Should return None for non-numeric input."""
        normalized, display = normalizer.normalize("abcdefghij")
        assert normalized is None

    def test_normalize_all_zeros(self, normalizer):
        """Should return None for invalid all-zeros number."""
        normalized, display = normalizer.normalize("000-000-0000")
        assert normalized is None

    def test_normalize_empty_string(self, normalizer):
        """Should return None for empty string."""
        normalized, display = normalizer.normalize("")
        assert normalized is None

    def test_normalize_none_equivalent(self, normalizer):
        """Should return None for whitespace-only input."""
        normalized, display = normalizer.normalize("   ")
        assert normalized is None

    def test_invalid_returns_original_display(self, normalizer):
        """Invalid number should preserve original as display."""
        normalized, display = normalizer.normalize("invalid-phone")
        assert normalized is None
        assert display == "invalid-phone"


class TestDisplayFormatting:
    """Tests for display value formatting."""

    @pytest.fixture
    def normalizer(self):
        """Create a US normalizer."""
        return PhoneNumberNormalizer("US")

    def test_us_display_format(self, normalizer):
        """US numbers should be formatted as (XXX) XXX-XXXX."""
        normalized, display = normalizer.normalize("2025551234")
        assert normalized == "+12025551234"
        assert display == "(202) 555-1234"

    def test_international_display_includes_country(self, normalizer):
        """International numbers should include country code in display."""
        normalized, display = normalizer.normalize("+442079460958")
        assert normalized == "+442079460958"
        assert "+44" in display

    def test_preserve_custom_display(self, normalizer):
        """Should preserve custom display value when provided."""
        normalized, display = normalizer.normalize(
            "2025551234", display_value="Custom: 202.555.1234"
        )
        assert normalized == "+12025551234"
        assert display == "Custom: 202.555.1234"


class TestSearchNormalization:
    """Tests for normalize_for_search method."""

    @pytest.fixture
    def normalizer(self):
        """Create a US normalizer."""
        return PhoneNumberNormalizer("US")

    def test_search_normalization_dashes(self, normalizer):
        """Should normalize dashed number for search."""
        normalized = normalizer.normalize_for_search("202-555-1234")
        assert normalized == "+12025551234"

    def test_search_normalization_parentheses(self, normalizer):
        """Should normalize parenthesized number for search."""
        normalized = normalizer.normalize_for_search("(202) 555-1234")
        assert normalized == "+12025551234"

    def test_search_normalization_plain(self, normalizer):
        """Should normalize plain number for search."""
        normalized = normalizer.normalize_for_search("2025551234")
        assert normalized == "+12025551234"

    def test_search_normalization_invalid(self, normalizer):
        """Should return None for invalid search input."""
        normalized = normalizer.normalize_for_search("invalid")
        assert normalized is None


class TestPhoneMatching:
    """Tests for phone number matching logic."""

    @pytest.fixture
    def normalizer(self):
        """Create a US normalizer."""
        return PhoneNumberNormalizer("US")

    def test_exact_match_plain(self, normalizer):
        """Should match exact plain numbers."""
        stored = "+12025551234"
        assert normalizer.matches(stored, "2025551234")

    def test_exact_match_with_country_code(self, normalizer):
        """Should match with country code prefix."""
        stored = "+12025551234"
        assert normalizer.matches(stored, "+1 202-555-1234")

    def test_exact_match_formatted(self, normalizer):
        """Should match formatted numbers."""
        stored = "+12025551234"
        assert normalizer.matches(stored, "(202) 555-1234")

    def test_suffix_match_7_digits(self, normalizer):
        """Should match on last 7 digits."""
        stored = "+12025551234"
        assert normalizer.matches(stored, "5551234")

    def test_suffix_match_formatted(self, normalizer):
        """Should match suffix with formatting."""
        stored = "+12025551234"
        assert normalizer.matches(stored, "555-1234")

    def test_no_match_different_number(self, normalizer):
        """Should not match different numbers."""
        stored = "+12025551234"
        assert not normalizer.matches(stored, "2025551235")

    def test_no_match_too_short(self, normalizer):
        """Should not match suffixes shorter than minimum."""
        stored = "+12025551234"
        assert not normalizer.matches(stored, "123")

    def test_no_match_empty_stored(self, normalizer):
        """Should not match with empty stored number."""
        assert not normalizer.matches("", "2025551234")

    def test_no_match_empty_search(self, normalizer):
        """Should not match with empty search number."""
        assert not normalizer.matches("+12025551234", "")


class TestIdempotency:
    """Tests for normalization idempotency."""

    @pytest.fixture
    def normalizer(self):
        """Create a US normalizer."""
        return PhoneNumberNormalizer("US")

    def test_normalize_already_e164(self, normalizer):
        """Normalizing E.164 should return same E.164."""
        normalized1, _ = normalizer.normalize("+12025551234")
        normalized2, _ = normalizer.normalize(normalized1)
        assert normalized1 == normalized2 == "+12025551234"

    def test_normalize_formatted_twice(self, normalizer):
        """Normalizing formatted number twice should be idempotent."""
        input_num = "(202) 555-1234"
        normalized1, _ = normalizer.normalize(input_num)
        normalized2, _ = normalizer.normalize(normalized1)
        assert normalized1 == normalized2 == "+12025551234"

    def test_normalize_international_twice(self, normalizer):
        """Normalizing international number twice should be idempotent."""
        normalized1, _ = normalizer.normalize("+442079460958")
        normalized2, _ = normalizer.normalize(normalized1)
        assert normalized1 == normalized2 == "+442079460958"


class TestCountryDefaults:
    """Tests for different country defaults."""

    def test_us_default(self):
        """US default should add +1 country code."""
        normalizer = PhoneNumberNormalizer(default_country="US")
        normalized, _ = normalizer.normalize("2025551234")
        assert normalized == "+12025551234"

    def test_gb_default(self):
        """GB default should add +44 country code."""
        normalizer = PhoneNumberNormalizer(default_country="GB")
        normalized, _ = normalizer.normalize("2079460958")
        assert normalized == "+442079460958"

    def test_de_default(self):
        """DE default should add +49 country code."""
        normalizer = PhoneNumberNormalizer(default_country="DE")
        normalized, _ = normalizer.normalize("3012345678")
        assert normalized == "+493012345678"


class TestSpecialCharacters:
    """Tests for handling special characters in phone numbers."""

    @pytest.fixture
    def normalizer(self):
        """Create a US normalizer."""
        return PhoneNumberNormalizer("US")

    def test_dot_separators(self, normalizer):
        """Should handle dot separators."""
        normalized, _ = normalizer.normalize("202.555.1234")
        assert normalized == "+12025551234"

    def test_slash_separators(self, normalizer):
        """Should handle slash separators."""
        normalized, _ = normalizer.normalize("202/555/1234")
        assert normalized == "+12025551234"

    def test_space_separators(self, normalizer):
        """Should handle space separators."""
        normalized, _ = normalizer.normalize("202 555 1234")
        assert normalized == "+12025551234"

    def test_dash_separators(self, normalizer):
        """Should handle dash separators."""
        normalized, _ = normalizer.normalize("202-555-1234")
        assert normalized == "+12025551234"

    def test_mixed_separators(self, normalizer):
        """Should handle mixed separators."""
        normalized, _ = normalizer.normalize("(202) 555.1234")
        assert normalized == "+12025551234"


class TestDigitOnlyMatch:
    """Tests for digit-only fallback matching."""

    @pytest.fixture
    def normalizer(self):
        """Create a US normalizer."""
        return PhoneNumberNormalizer("US")

    def test_digit_only_suffix_match(self, normalizer):
        """Should match stored number suffix with digits only."""
        assert normalizer._digit_only_match("+12025551234", "5551234")

    def test_digit_only_reverse_suffix(self, normalizer):
        """Should match search suffix against stored."""
        assert normalizer._digit_only_match("5551234", "+12025551234")

    def test_digit_only_no_match(self, normalizer):
        """Should not match unrelated digit sequences."""
        assert not normalizer._digit_only_match("+12025551234", "9876543")

    def test_digit_only_empty_stored(self, normalizer):
        """Should not match with empty stored."""
        assert not normalizer._digit_only_match("", "5551234")

    def test_digit_only_empty_search(self, normalizer):
        """Should not match with empty search."""
        assert not normalizer._digit_only_match("+12025551234", "")


class TestSuffixMatch:
    """Tests for suffix matching logic."""

    @pytest.fixture
    def normalizer(self):
        """Create a US normalizer."""
        return PhoneNumberNormalizer("US")

    def test_suffix_match_7_digits(self, normalizer):
        """Should match with 7 digit suffix."""
        assert normalizer._suffix_match("+12025551234", "+12025551234")

    def test_suffix_match_exact_min(self, normalizer):
        """Should match with exactly min_digits."""
        # Default min_digits is 7
        assert normalizer._suffix_match("+12025551234", "5551234")

    def test_suffix_match_below_min(self, normalizer):
        """Should not match with fewer than min_digits."""
        assert not normalizer._suffix_match("+12025551234", "551234")

    def test_suffix_match_custom_min(self, normalizer):
        """Should respect custom min_digits."""
        # 5 digits shouldn't match with default min=7
        assert not normalizer._suffix_match("+12025551234", "51234", min_digits=7)
        # But should match with min=5
        assert normalizer._suffix_match("+12025551234", "51234", min_digits=5)


class TestCleanInput:
    """Tests for input cleaning logic."""

    @pytest.fixture
    def normalizer(self):
        """Create a US normalizer."""
        return PhoneNumberNormalizer("US")

    def test_clean_strips_whitespace(self, normalizer):
        """Should strip leading/trailing whitespace."""
        cleaned, prefix = normalizer._clean_input("  202-555-1234  ")
        assert cleaned == "202-555-1234"
        assert prefix is None

    def test_clean_removes_ext(self, normalizer):
        """Should remove 'ext' extension."""
        cleaned, prefix = normalizer._clean_input("202-555-1234 ext 123")
        assert "ext" not in cleaned.lower()
        assert "123" not in cleaned.split()[-1] if len(cleaned.split()) > 1 else True
        assert prefix is None

    def test_clean_removes_x_extension(self, normalizer):
        """Should remove 'x' extension."""
        cleaned, prefix = normalizer._clean_input("202-555-1234 x123")
        assert "x123" not in cleaned
        assert prefix is None

    def test_clean_preserves_plus(self, normalizer):
        """Should preserve + for international numbers."""
        cleaned, prefix = normalizer._clean_input("+1 202-555-1234")
        assert cleaned.startswith("+")
        assert prefix is None


class TestFormatDisplay:
    """Tests for display formatting."""

    @pytest.fixture
    def normalizer(self):
        """Create a US normalizer."""
        return PhoneNumberNormalizer("US")

    def test_format_us_national(self, normalizer):
        """US numbers should format as national."""
        import phonenumbers

        parsed = phonenumbers.parse("+12025551234", "US")
        display = normalizer._format_display(parsed)
        # Should be in national format: (202) 555-1234
        assert "202" in display
        assert "555" in display
        assert "1234" in display

    def test_format_international(self, normalizer):
        """Non-US numbers should include country code."""
        import phonenumbers

        parsed = phonenumbers.parse("+442079460958", "US")
        display = normalizer._format_display(parsed)
        assert "+44" in display


class TestPhoneNumberPrefixes:
    """Tests for handling dialing prefixes like *67, *82, #31#."""

    @pytest.fixture
    def normalizer(self):
        """Create a US normalizer."""
        return PhoneNumberNormalizer("US")

    # North American prefix tests
    def test_normalize_with_star67_prefix(self, normalizer):
        """Should handle *67 (hide caller ID) prefix."""
        normalized, display = normalizer.normalize("*67 202-555-1234")
        assert normalized == "+12025551234"
        assert "*67" in display
        assert "202" in display

    def test_normalize_with_star82_prefix(self, normalizer):
        """Should handle *82 (show caller ID) prefix."""
        normalized, display = normalizer.normalize("*82 (202) 555-1234")
        assert normalized == "+12025551234"
        assert "*82" in display

    def test_normalize_with_star66_prefix(self, normalizer):
        """Should handle *66 (repeat last call) prefix."""
        normalized, display = normalizer.normalize("*66 202-555-1234")
        assert normalized == "+12025551234"
        assert "*66" in display

    def test_normalize_with_star69_prefix(self, normalizer):
        """Should handle *69 (return last call) prefix."""
        normalized, _ = normalizer.normalize("*69 2025551234")
        assert normalized == "+12025551234"

    # European prefix tests
    def test_normalize_with_hash31hash_prefix(self, normalizer):
        """Should handle #31# (European hide caller ID) prefix."""
        normalized, display = normalizer.normalize("#31# +44 20 7946 0958")
        assert normalized == "+442079460958"
        assert "#31#" in display

    def test_normalize_with_star31hash_prefix(self, normalizer):
        """Should handle *31# (European show caller ID) prefix."""
        normalized, display = normalizer.normalize("*31# +33 1 42 86 82 00")
        assert normalized == "+33142868200"
        assert "*31#" in display

    # Prefix with different formats
    def test_prefix_with_parentheses_format(self, normalizer):
        """Should handle prefix with (XXX) XXX-XXXX format."""
        normalized, display = normalizer.normalize("*67 (202) 555-1234")
        assert normalized == "+12025551234"
        assert "*67" in display

    def test_prefix_with_spaces(self, normalizer):
        """Should handle prefix with spaces in number."""
        normalized, _ = normalizer.normalize("*67   202 555 1234")
        assert normalized == "+12025551234"

    def test_prefix_no_space_after(self, normalizer):
        """Should handle prefix without space after it when followed by non-digit."""
        # Use parenthesis right after prefix (common format)
        normalized, display = normalizer.normalize("*67(202) 555-1234")
        assert normalized == "+12025551234"
        assert "*67" in display

    def test_prefix_with_international_format(self, normalizer):
        """Should handle prefix with international number."""
        normalized, _ = normalizer.normalize("*67 +1 202 555 1234")
        assert normalized == "+12025551234"

    # Mixed prefix and extension tests
    def test_prefix_and_extension(self, normalizer):
        """Should handle both prefix and extension."""
        normalized, display = normalizer.normalize("*67 202-555-1234 ext 456")
        assert normalized == "+12025551234"
        assert "*67" in display
        assert "ext" not in normalized

    # Edge cases
    def test_prefix_only_no_number(self, normalizer):
        """Should return None for prefix only."""
        normalized, _ = normalizer.normalize("*67")
        assert normalized is None

    def test_prefix_with_invalid_number(self, normalizer):
        """Should return None for prefix with invalid number."""
        normalized, display = normalizer.normalize("*67 123")
        assert normalized is None
        # Display should preserve original
        assert "*67 123" == display

    def test_multiple_prefixes(self, normalizer):
        """Should handle first prefix only."""
        # This is an edge case - multiple prefixes aren't valid but we handle gracefully
        normalized, _ = normalizer.normalize("*67 *82 202-555-1234")
        assert normalized == "+12025551234"

    # Display value preservation
    def test_prefix_preserves_custom_display(self, normalizer):
        """Should preserve custom display value even with prefix."""
        normalized, display = normalizer.normalize(
            "*67 2025551234",
            display_value="Hidden: (202) 555-1234"
        )
        assert normalized == "+12025551234"
        assert display == "Hidden: (202) 555-1234"

    def test_prefix_in_auto_display(self, normalizer):
        """Should include prefix in auto-generated display value."""
        normalized, display = normalizer.normalize("*67 2025551234")
        assert normalized == "+12025551234"
        assert "*67" in display
        assert "202" in display

    # Clean input tests
    def test_clean_input_extracts_prefix(self, normalizer):
        """Should extract prefix from input."""
        cleaned, prefix = normalizer._clean_input("*67 202-555-1234")
        assert prefix == "*67"
        assert "202" in cleaned
        assert "*67" not in cleaned

    def test_clean_input_no_prefix(self, normalizer):
        """Should return None prefix when no prefix present."""
        cleaned, prefix = normalizer._clean_input("202-555-1234")
        assert prefix is None
        assert "202" in cleaned

    def test_clean_input_hash_prefix(self, normalizer):
        """Should extract hash-style prefix."""
        cleaned, prefix = normalizer._clean_input("#31# +44 20 7946 0958")
        assert prefix == "#31#"
        assert "+44" in cleaned

    def test_clean_input_whitespace_handling(self, normalizer):
        """Should handle various whitespace around prefix."""
        cleaned, prefix = normalizer._clean_input("  *67   202-555-1234")
        assert prefix == "*67"
        assert cleaned.strip() == "202-555-1234"

    # Search with prefixes
    def test_search_with_prefix(self, normalizer):
        """Should normalize search input with prefix."""
        normalized = normalizer.normalize_for_search("*67 202-555-1234")
        assert normalized == "+12025551234"

    def test_match_with_prefix_in_search(self, normalizer):
        """Should match when search input has prefix."""
        stored = "+12025551234"
        assert normalizer.matches(stored, "*67 202-555-1234")

    def test_match_with_prefix_in_both(self, normalizer):
        """Should match regardless of prefix presence."""
        stored = "+12025551234"
        # Stored never has prefix (normalized), search might
        # Use full number with prefix to ensure valid parsing
        assert normalizer.matches(stored, "*67 202-555-1234")


