"""Data access repositories package.

This package provides repository classes for database operations,
implementing the Repository pattern for data access abstraction.
"""

from .contact_repository import ContactRepository
from .sync_repository import SyncRepository

__all__ = ["ContactRepository", "SyncRepository"]
