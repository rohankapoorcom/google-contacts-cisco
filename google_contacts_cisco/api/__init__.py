"""API endpoints package.

This package contains all FastAPI routers for the application:
- routes: OAuth authentication endpoints
- google: Google API related endpoints
- sync: Contact synchronization endpoints

Import routers directly from their modules to avoid circular imports:
    from google_contacts_cisco.api.routes import router as auth_router
    from google_contacts_cisco.api.sync import router as sync_router
"""

# Note: Direct router imports are done in main.py to avoid circular imports
# The api.schemas module can be safely imported for schema definitions
from .schemas import (
    GoogleConnectionsResponse,
    GoogleEmailAddress,
    GoogleMetadata,
    GoogleMetadataSource,
    GoogleName,
    GoogleOrganization,
    GooglePerson,
    GooglePhoneNumber,
)

__all__ = [
    "GoogleConnectionsResponse",
    "GooglePerson",
    "GoogleName",
    "GooglePhoneNumber",
    "GoogleEmailAddress",
    "GoogleOrganization",
    "GoogleMetadata",
    "GoogleMetadataSource",
]
