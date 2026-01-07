"""Google People API client.

This module provides a wrapper around the Google People API for managing contacts.
It handles:
- Contact list retrieval with pagination
- Single contact retrieval
- Connection testing
- Retry logic with exponential backoff for rate limits and server errors
"""

import time
from typing import Any, Callable, Iterator, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build  # type: ignore[import-untyped]
from googleapiclient.errors import HttpError  # type: ignore[import-untyped]

from ..auth.oauth import get_credentials
from ..utils.logger import get_logger

logger = get_logger(__name__)


# Person fields to retrieve from Google Contacts
PERSON_FIELDS = [
    "names",
    "emailAddresses",
    "phoneNumbers",
    "organizations",
    "metadata",
]


class GoogleClientError(Exception):
    """Base exception for Google client errors."""

    pass


class CredentialsError(GoogleClientError):
    """Raised when credentials are invalid or unavailable."""

    pass


class RateLimitError(GoogleClientError):
    """Raised when rate limit is exceeded and retries are exhausted."""

    pass


class ServerError(GoogleClientError):
    """Raised when server errors persist after retries."""

    pass


class SyncTokenExpiredError(GoogleClientError):
    """Raised when the sync token has expired (410 Gone)."""

    pass


class GoogleContactsClient:
    """Client for Google People API.

    This client provides methods to interact with the Google People API,
    including listing all contacts with pagination, fetching individual
    contacts, and testing the connection.

    Attributes:
        credentials: OAuth2 credentials for API access
        service: Google API service instance
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff time in seconds
    """

    def __init__(
        self,
        credentials: Optional[Credentials] = None,
        max_retries: int = 5,
        initial_backoff: float = 1.0,
    ):
        """Initialize Google Contacts client.

        Args:
            credentials: OAuth credentials (if None, loads from storage)
            max_retries: Maximum number of retry attempts for transient errors
            initial_backoff: Initial backoff time in seconds for retries

        Raises:
            CredentialsError: If no valid credentials available
        """
        self.credentials = credentials or get_credentials()
        if not self.credentials:
            raise CredentialsError(
                "No valid credentials available. Please authenticate first."
            )

        self._service: Optional[Resource] = None
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff

    @property
    def service(self) -> Resource:
        """Get or create the Google API service instance.

        Returns:
            Google API service resource

        Note:
            Service is lazily initialized on first access.
        """
        if self._service is None:
            self._service = build("people", "v1", credentials=self.credentials)
        return self._service

    def list_connections(
        self,
        page_size: int = 100,
        sync_token: Optional[str] = None,
    ) -> Iterator[dict[str, Any]]:
        """List all connections with pagination.

        Retrieves contacts from the authenticated user's Google Contacts,
        handling pagination automatically. Follows Google's recommendation
        for sequential requests to avoid rate limits.

        Args:
            page_size: Number of contacts per page (max 1000, recommended 100-500)
            sync_token: Token for incremental sync (if available)

        Yields:
            Dictionary containing 'connections' list and 'nextSyncToken'

        Raises:
            SyncTokenExpiredError: If sync token is expired (410 Gone)
            RateLimitError: If rate limit exceeded after max retries
            ServerError: If server errors persist after max retries
            HttpError: For other API errors
        """
        page_token: Optional[str] = None
        request_count = 0

        while True:
            # Build request parameters
            request_params: dict[str, Any] = {
                "resourceName": "people/me",
                "pageSize": min(page_size, 1000),  # Ensure max 1000
                "personFields": ",".join(PERSON_FIELDS),
                "requestSyncToken": True,  # Always request sync token
            }

            if sync_token:
                request_params["syncToken"] = sync_token

            if page_token:
                request_params["pageToken"] = page_token

            try:
                # Make request with retry logic
                # Copy params for lambda closure
                params_copy = request_params.copy()

                def make_request() -> dict[str, Any]:
                    result: dict[str, Any] = (
                        self.service.people()
                        .connections()
                        .list(**params_copy)
                        .execute()
                    )
                    return result

                response = self._make_request_with_retry(make_request)

                request_count += 1
                connections = response.get("connections", [])
                logger.info(
                    "Retrieved page %d (%d contacts)", request_count, len(connections)
                )

                yield response

                # Check if there are more pages
                page_token = response.get("nextPageToken")
                if not page_token:
                    logger.info(
                        "Completed listing connections: %d page(s) retrieved",
                        request_count,
                    )
                    break

                # Small delay between requests (sequential, as recommended by Google)
                time.sleep(0.1)

            except HttpError as e:
                if e.resp.status == 410:
                    # Sync token expired
                    logger.warning("Sync token expired, need to do full sync")
                    raise SyncTokenExpiredError(
                        "Sync token expired. A full sync is required."
                    ) from e
                else:
                    logger.exception("Error listing connections")
                    raise

    def get_person(self, resource_name: str) -> dict[str, Any]:
        """Get a single person by resource name.

        Args:
            resource_name: Person's resource name (e.g., 'people/c12345')

        Returns:
            Person data dictionary containing requested fields

        Raises:
            HttpError: If API request fails
        """
        try:
            person = self._make_request_with_retry(
                lambda: self.service.people()
                .get(
                    resourceName=resource_name,
                    personFields=",".join(PERSON_FIELDS),
                )
                .execute()
            )
            logger.debug("Retrieved person: %s", resource_name)
            return person
        except HttpError:
            logger.exception("Error getting person %s", resource_name)
            raise

    def test_connection(self) -> bool:
        """Test connection to Google People API.

        Makes a minimal API request to verify credentials and connectivity.

        Returns:
            True if connection successful

        Raises:
            HttpError: If connection fails
        """
        try:
            # Try to get just one contact with minimal fields
            self.service.people().connections().list(
                resourceName="people/me",
                pageSize=1,
                personFields="names",
            ).execute()
            logger.info("Successfully connected to Google People API")
            return True
        except HttpError:
            logger.exception("Connection test failed")
            raise

    def get_total_connections_count(self) -> int:
        """Get approximate total number of connections.

        Makes a minimal request to estimate total contacts.

        Returns:
            Total number of connections (may be approximate)

        Raises:
            HttpError: If API request fails
        """
        try:
            response = self.service.people().connections().list(
                resourceName="people/me",
                pageSize=1,
                personFields="names",
            ).execute()
            total: int = response.get("totalItems", 0) or response.get("totalPeople", 0)
            logger.debug("Total connections count: %d", total)
            return total
        except HttpError:
            logger.exception("Error getting connection count")
            raise

    def _make_request_with_retry(
        self,
        request_func: Callable[[], dict[str, Any]],
        retry_count: int = 0,
    ) -> dict[str, Any]:
        """Make API request with retry logic.

        Implements exponential backoff for rate limits (429) and
        server errors (5xx).

        Args:
            request_func: Function that makes the API request
            retry_count: Current retry attempt (internal use)

        Returns:
            API response dictionary

        Raises:
            RateLimitError: If rate limit exceeded after max retries
            ServerError: If server errors persist after max retries
            HttpError: For other API errors (no retry)
        """
        try:
            return request_func()
        except HttpError as e:
            status = e.resp.status

            if status == 429:  # Rate limit
                if retry_count < self.max_retries:
                    backoff = self.initial_backoff * (2**retry_count)
                    logger.warning(
                        "Rate limit hit, backing off for %.1f seconds (attempt %d/%d)",
                        backoff,
                        retry_count + 1,
                        self.max_retries,
                    )
                    time.sleep(backoff)
                    return self._make_request_with_retry(request_func, retry_count + 1)
                else:
                    logger.exception(
                        "Max retries exceeded for rate limit after %d attempts",
                        self.max_retries,
                    )
                    raise RateLimitError(
                        f"Rate limit exceeded after {self.max_retries} retries"
                    ) from e

            elif status >= 500:  # Server error
                if retry_count < self.max_retries:
                    backoff = self.initial_backoff * (2**retry_count)
                    logger.warning(
                        "Server error %d, retrying in %.1f seconds (attempt %d/%d)",
                        status,
                        backoff,
                        retry_count + 1,
                        self.max_retries,
                    )
                    time.sleep(backoff)
                    return self._make_request_with_retry(request_func, retry_count + 1)
                else:
                    logger.exception(
                        "Max retries exceeded for server error after %d attempts",
                        self.max_retries,
                    )
                    msg = (
                        f"Server error {status} persisted "
                        f"after {self.max_retries} retries"
                    )
                    raise ServerError(msg) from e

            elif status == 401:  # Unauthorized
                logger.exception("Unauthorized - credentials may have expired")
                raise

            else:
                # Other errors - don't retry
                logger.exception("API error %d", status)
                raise


def get_google_client(
    credentials: Optional[Credentials] = None,
) -> GoogleContactsClient:
    """Get Google Contacts client instance.

    Factory function to create a configured GoogleContactsClient.

    Args:
        credentials: OAuth credentials (if None, loads from storage)

    Returns:
        GoogleContactsClient instance

    Raises:
        CredentialsError: If no valid credentials available
    """
    return GoogleContactsClient(credentials)
