"""Business logic services package.

This package provides service classes that encapsulate business logic,
including contact transformation, Google API client, and synchronization.
"""

from .contact_transformer import (
    transform_google_person_to_contact,
    transform_google_persons_batch,
)
from .google_client import (
    CredentialsError,
    GoogleClientError,
    GoogleContactsClient,
    RateLimitError,
    ServerError,
    SyncTokenExpiredError,
    get_google_client,
)
from .sync_service import SyncService, SyncStatistics, get_sync_service

__all__ = [
    # Contact transformer
    "transform_google_person_to_contact",
    "transform_google_persons_batch",
    # Google client
    "GoogleContactsClient",
    "GoogleClientError",
    "CredentialsError",
    "RateLimitError",
    "ServerError",
    "SyncTokenExpiredError",
    "get_google_client",
    # Sync service
    "SyncService",
    "SyncStatistics",
    "get_sync_service",
]
