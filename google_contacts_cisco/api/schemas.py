"""Pydantic schemas for API requests and responses.

This module provides schemas for parsing and validating data from Google People API
responses and transforming them to internal formats.
"""
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class GoogleName(BaseModel):
    """Name from Google People API."""

    display_name: Optional[str] = Field(None, alias="displayName")
    given_name: Optional[str] = Field(None, alias="givenName")
    family_name: Optional[str] = Field(None, alias="familyName")

    model_config = {"populate_by_name": True}


class GooglePhoneNumber(BaseModel):
    """Phone number from Google People API."""

    value: str
    type: Optional[str] = None
    formatted_type: Optional[str] = Field(None, alias="formattedType")

    model_config = {"populate_by_name": True}


class GoogleEmailAddress(BaseModel):
    """Email address from Google People API."""

    value: EmailStr
    type: Optional[str] = None

    model_config = {"populate_by_name": True}


class GoogleOrganization(BaseModel):
    """Organization from Google People API."""

    name: Optional[str] = None
    title: Optional[str] = None

    model_config = {"populate_by_name": True}


class GoogleMetadataSource(BaseModel):
    """Metadata source from Google People API."""

    type: str
    id: str
    etag: Optional[str] = None

    model_config = {"populate_by_name": True}


class GoogleMetadata(BaseModel):
    """Metadata from Google People API."""

    sources: List[GoogleMetadataSource] = []
    deleted: Optional[bool] = None

    model_config = {"populate_by_name": True}


class GooglePerson(BaseModel):
    """Person from Google People API.

    This schema represents the structure of a person resource returned by
    the Google People API. It handles the camelCase field names from the API
    and provides utility methods for extracting common data.
    """

    resource_name: str = Field(..., alias="resourceName")
    etag: Optional[str] = None
    names: List[GoogleName] = []
    phone_numbers: List[GooglePhoneNumber] = Field(
        default_factory=list, alias="phoneNumbers"
    )
    email_addresses: List[GoogleEmailAddress] = Field(
        default_factory=list, alias="emailAddresses"
    )
    organizations: List[GoogleOrganization] = []
    metadata: Optional[GoogleMetadata] = None

    model_config = {"populate_by_name": True}

    def get_display_name(self) -> str:
        """Get display name for contact.

        Tries multiple sources in order of preference:
        1. The displayName field from the first name entry
        2. Constructed from givenName + familyName
        3. Just givenName
        4. Just familyName
        5. Organization name (for business contacts)
        6. First email address
        7. Resource name as last resort

        Returns:
            Display name string, guaranteed to be non-empty
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

        # Fall back to organization name for business contacts
        for org in self.organizations:
            if org.name and org.name.strip():
                return org.name.strip()

        # Fall back to email
        if self.email_addresses:
            return self.email_addresses[0].value

        # Last resort: resource name
        return self.resource_name

    def is_deleted(self) -> bool:
        """Check if contact is deleted.

        Returns:
            True if contact is marked as deleted in metadata
        """
        return self.metadata is not None and self.metadata.deleted is True

    def get_primary_etag(self) -> Optional[str]:
        """Get primary etag from metadata sources.

        Tries to get the etag in order of preference:
        1. Top-level etag field
        2. Etag from CONTACT type source in metadata

        Returns:
            Etag string or None if not available
        """
        if self.etag:
            return self.etag

        if self.metadata and self.metadata.sources:
            for source in self.metadata.sources:
                if source.type == "CONTACT" and source.etag:
                    return source.etag

        return None


class GoogleConnectionsResponse(BaseModel):
    """Response from Google People API connections list.

    This schema represents the paginated response from the
    people.connections.list API endpoint.
    """

    connections: List[GooglePerson] = []
    next_page_token: Optional[str] = Field(None, alias="nextPageToken")
    next_sync_token: Optional[str] = Field(None, alias="nextSyncToken")
    total_people: Optional[int] = Field(None, alias="totalPeople")
    total_items: Optional[int] = Field(None, alias="totalItems")

    model_config = {"populate_by_name": True}

