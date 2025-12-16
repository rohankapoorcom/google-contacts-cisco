"""Test main application."""
import pytest
from httpx import AsyncClient, ASGITransport

from google_contacts_cisco.main import app
from google_contacts_cisco._version import __version__


@pytest.mark.asyncio
async def test_root():
    """Test root endpoint."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Google Contacts Cisco Directory API"}


@pytest.mark.asyncio
async def test_health():
    """Test health check endpoint."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


def test_version():
    """Test version is available."""
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__.split(".")) == 3  # Major.Minor.Patch

