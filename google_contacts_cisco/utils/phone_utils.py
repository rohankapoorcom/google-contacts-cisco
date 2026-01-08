"""Phone number utilities for normalization and search.

This module provides phone number normalization to E.164 format
for consistent storage and comparison, and implements search logic
for finding contacts by phone number.
"""

import re
from typing import Optional, Tuple

import phonenumbers
from phonenumbers import NumberParseException

from .logger import get_logger

logger = get_logger(__name__)


class PhoneNumberNormalizer:
    """Normalize and validate phone numbers.

    This class provides methods for normalizing phone numbers to E.164 format,
    preserving display values, and matching phone numbers for search.
    """

    def __init__(self, default_country: str = "US"):
        """Initialize normalizer.

        Args:
            default_country: Default country code for parsing (ISO 3166-1 alpha-2)
        """
        self.default_country = default_country

    def normalize(
        self, phone_number: str, display_value: Optional[str] = None
    ) -> Tuple[Optional[str], str]:
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
                logger.warning("Invalid phone number: %s", phone_number)
                return None, final_display

            # Convert to E.164 format
            normalized = phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )

            # If no display value provided, format nicely
            if not display_value:
                final_display = self._format_display(parsed)

            logger.debug("Normalized %s to %s", phone_number, normalized)
            return normalized, final_display

        except NumberParseException as e:
            logger.warning("Failed to parse phone number %s: %s", phone_number, e)
            return None, final_display
        except Exception as e:
            logger.error("Error normalizing phone number %s: %s", phone_number, e)
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

        Supports exact E.164 matching and suffix matching (last N digits).

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
            Cleaned string with extensions removed
        """
        # Remove common separators but keep + for international
        cleaned = phone_number.strip()

        # Handle extensions (remove them for normalization)
        ext_pattern = r"\s*(ext|extension|x)\s*\.?\s*\d+$"
        cleaned = re.sub(ext_pattern, "", cleaned, flags=re.IGNORECASE)

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
                parsed, phonenumbers.PhoneNumberFormat.NATIONAL
            )
        else:
            return phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
            )

    def _digit_only_match(self, stored: str, search: str) -> bool:
        """Match using digits only (fallback).

        Args:
            stored: Stored number
            search: Search input

        Returns:
            True if digits match (suffix matching)
        """
        stored_digits = re.sub(r"\D", "", stored)
        search_digits = re.sub(r"\D", "", search)

        if not stored_digits or not search_digits:
            return False

        # Match if search is suffix of stored
        return stored_digits.endswith(search_digits) or search_digits.endswith(
            stored_digits
        )

    def _suffix_match(self, stored: str, search: str, min_digits: int = 7) -> bool:
        """Match phone numbers by suffix (last N digits).

        Args:
            stored: Stored E.164 number
            search: Search E.164 number
            min_digits: Minimum digits to match

        Returns:
            True if suffixes match
        """
        stored_digits = re.sub(r"\D", "", stored)
        search_digits = re.sub(r"\D", "", search)

        # Need at least min_digits to match
        if len(search_digits) < min_digits:
            return False

        # Check if one is suffix of other
        return stored_digits.endswith(search_digits) or search_digits.endswith(
            stored_digits
        )


def get_phone_normalizer(default_country: str = "US") -> PhoneNumberNormalizer:
    """Get phone number normalizer instance.

    Args:
        default_country: Default country code (ISO 3166-1 alpha-2)

    Returns:
        PhoneNumberNormalizer instance
    """
    return PhoneNumberNormalizer(default_country)

