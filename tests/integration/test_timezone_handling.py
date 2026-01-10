"""Integration tests for timezone handling across the application.

This module tests that timestamps are consistently formatted with timezone
information throughout the application stack (database → services → API).
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from google_contacts_cisco.config import Settings
from google_contacts_cisco.main import app
from google_contacts_cisco.models.contact import Contact
from google_contacts_cisco.models.sync_state import SyncState, SyncStatus
from google_contacts_cisco.schemas.contact import ContactResponse
from google_contacts_cisco.services.sync_service import SyncService
from google_contacts_cisco.utils.datetime_utils import format_timestamp_for_display


class TestTimezoneHandling:
    """Test timezone handling across different components."""

    def test_database_stores_utc_timestamps(self, integration_db: Session):
        """Test that database stores UTC timestamps (SQLite stores as naive datetime).
        
        Note: SQLite stores timestamps without timezone info, but we treat them as UTC
        and convert to timezone-aware timestamps at the application layer.
        """
        # Create a contact
        contact = Contact(
            resource_name="people/test123",
            display_name="Test User",
        )
        integration_db.add(contact)
        integration_db.commit()
        integration_db.refresh(contact)

        # SQLite stores datetime without timezone info (known limitation)
        # We handle this by treating all database timestamps as UTC
        # and converting them to timezone-aware at the API layer
        assert contact.created_at is not None
        assert contact.updated_at is not None
        
        # Verify timestamps are reasonable (within last minute)
        from google_contacts_cisco.utils.datetime_utils import get_current_time_utc
        now = get_current_time_utc()
        
        # Convert naive datetime to timezone-aware for comparison
        if contact.created_at.tzinfo is None:
            created_at_utc = contact.created_at.replace(tzinfo=timezone.utc)
        else:
            created_at_utc = contact.created_at
            
        assert (now - created_at_utc).total_seconds() < 60

    def test_sync_state_stores_utc_timestamps(self, integration_db: Session):
        """Test that sync state stores UTC timestamps (SQLite stores as naive datetime).
        
        Note: SQLite stores timestamps without timezone info, but we treat them as UTC
        and handle timezone conversion at the application layer.
        """
        # Create a sync state with timezone-aware datetime
        now_utc = datetime.now(timezone.utc)
        sync_state = SyncState(
            sync_status=SyncStatus.IDLE,
            last_sync_at=now_utc,
        )
        integration_db.add(sync_state)
        integration_db.commit()
        integration_db.refresh(sync_state)

        # SQLite loses timezone info but we treat stored timestamps as UTC
        assert sync_state.last_sync_at is not None
        
        # Ensure timestamp value is preserved (compare times ignoring timezone)
        if sync_state.last_sync_at.tzinfo is None:
            # Convert to UTC for comparison
            stored_time_utc = sync_state.last_sync_at.replace(tzinfo=timezone.utc)
        else:
            stored_time_utc = sync_state.last_sync_at
            
        # Timestamps should be within 1 second due to precision loss
        assert abs((stored_time_utc - now_utc).total_seconds()) < 1

    def test_contact_response_formats_timestamps_with_timezone(self, integration_db: Session):
        """Test that ContactResponse formats timestamps with configured timezone."""
        # Create a contact with known timestamps
        utc_time = datetime(2026, 1, 9, 20, 30, 0, tzinfo=timezone.utc)
        contact = Contact(
            resource_name="people/test123",
            display_name="Test User",
            created_at=utc_time,
            updated_at=utc_time,
        )
        integration_db.add(contact)
        integration_db.commit()
        integration_db.refresh(contact)

        # Test with UTC timezone
        with patch('google_contacts_cisco.schemas.contact.get_settings') as mock_settings:
            mock_settings.return_value = Settings(timezone="UTC")
            response = ContactResponse.from_orm(contact)
            
            # Should include timezone info (UTC)
            assert response.created_at is not None
            assert "+00:00" in response.created_at or "Z" in response.created_at
            assert response.updated_at is not None
            assert "+00:00" in response.updated_at or "Z" in response.updated_at

        # Test with America/New_York timezone
        with patch('google_contacts_cisco.schemas.contact.get_settings') as mock_settings:
            mock_settings.return_value = Settings(timezone="America/New_York")
            response = ContactResponse.from_orm(contact)
            
            # Should include timezone info (Eastern Time)
            # In January, EST is UTC-5
            assert response.created_at is not None
            assert "-05:00" in response.created_at
            assert response.updated_at is not None
            assert "-05:00" in response.updated_at

    def test_api_responses_include_timezone_aware_timestamps(self, integration_db: Session):
        """Test that API response schemas format timestamps with timezone info."""
        # Create a contact with known timestamps
        utc_time = datetime(2026, 1, 9, 20, 30, 0, tzinfo=timezone.utc)
        contact = Contact(
            resource_name="people/test123",
            display_name="Test User",
            created_at=utc_time,
            updated_at=utc_time,
        )
        integration_db.add(contact)
        integration_db.commit()
        integration_db.refresh(contact)

        # Test that the response schema formats timestamps correctly
        with patch('google_contacts_cisco.schemas.contact.get_settings') as mock_settings:
            mock_settings.return_value = Settings(timezone="America/Chicago")
            response = ContactResponse.from_orm(contact)
            
            # Should include timezone info (CST is UTC-6 in January)
            assert response.created_at is not None
            assert "-06:00" in response.created_at
            assert response.updated_at is not None
            assert "-06:00" in response.updated_at


class TestTimezoneConfigValidation:
    """Test timezone configuration validation."""

    def test_valid_timezone_configuration(self):
        """Test that valid IANA timezones are accepted."""
        valid_timezones = [
            "UTC",
            "America/New_York",
            "Europe/London",
            "Asia/Tokyo",
            "Australia/Sydney",
        ]
        
        for tz in valid_timezones:
            settings = Settings(timezone=tz)
            assert settings.timezone == tz

    def test_invalid_timezone_falls_back_to_utc(self):
        """Test that invalid timezones fall back to UTC."""
        settings = Settings(timezone="Invalid/Timezone")
        assert settings.timezone == "UTC"

    def test_default_timezone_is_utc(self):
        """Test that default timezone is UTC."""
        settings = Settings()
        assert settings.timezone == "UTC"


class TestTimezoneConsistency:
    """Test timezone handling consistency across the application."""

    def test_all_models_use_utc_for_storage(self, integration_db: Session):
        """Test that all models store timestamps in UTC (SQLite stores as naive).
        
        Note: SQLite doesn't preserve timezone info, but our application treats
        all stored timestamps as UTC and handles timezone conversion at the API layer.
        """
        # Create various models
        contact = Contact(
            resource_name="people/test123",
            display_name="Test User",
        )
        sync_state = SyncState(
            sync_status=SyncStatus.IDLE,
            last_sync_at=datetime.now(timezone.utc),
        )
        
        integration_db.add_all([contact, sync_state])
        integration_db.commit()
        integration_db.refresh(contact)
        integration_db.refresh(sync_state)
        
        # All timestamps should exist and be treated as UTC
        assert contact.created_at is not None
        assert contact.updated_at is not None
        assert sync_state.last_sync_at is not None

    def test_timestamps_maintain_consistency_through_update(self, integration_db: Session):
        """Test that timestamps maintain UTC consistency through updates."""
        # Create a contact
        contact = Contact(
            resource_name="people/test123",
            display_name="Test User",
        )
        integration_db.add(contact)
        integration_db.commit()
        integration_db.refresh(contact)
        
        # Store original created_at, normalize to UTC if naive
        if contact.created_at.tzinfo is None:
            original_created = contact.created_at.replace(tzinfo=timezone.utc)
        else:
            original_created = contact.created_at
        
        # Small delay to ensure updated_at changes
        import time
        time.sleep(0.01)
        
        # Update the contact
        contact.display_name = "Updated User"
        integration_db.commit()
        integration_db.refresh(contact)
        
        # Normalize both timestamps for comparison
        if contact.created_at.tzinfo is None:
            created_utc = contact.created_at.replace(tzinfo=timezone.utc)
        else:
            created_utc = contact.created_at
            
        if contact.updated_at.tzinfo is None:
            updated_utc = contact.updated_at.replace(tzinfo=timezone.utc)
        else:
            updated_utc = contact.updated_at
        
        # created_at should not change
        assert created_utc == original_created
        
        # updated_at should be later than created_at
        assert updated_utc >= created_utc
