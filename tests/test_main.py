"""Test main application."""

from fastapi.testclient import TestClient

from google_contacts_cisco._version import __version__
from google_contacts_cisco.config import settings
from google_contacts_cisco.main import STATIC_DIR, app

client = TestClient(app)


def test_root():
    """Test root endpoint.

    When frontend is built, returns HTML.
    When frontend is not built, returns JSON with app info.
    """
    response = client.get("/")
    assert response.status_code == 200

    # Check if frontend is built
    if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
        # Frontend is built - serves HTML
        assert "text/html" in response.headers.get("content-type", "")
    else:
        # Frontend not built - returns JSON API info
        data = response.json()
        assert "message" in data
        assert settings.app_name in data["message"]
        assert "version" in data
        assert data["version"] == __version__


def test_health():
    """Test health check endpoint returns status and config info."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "debug" in data
    assert "config_valid" in data
    assert "config_errors" in data


def test_health_version_matches():
    """Test that health endpoint returns the correct version from _version.py."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == __version__
    # Verify version format is semantic versioning (X.Y.Z)
    version_parts = data["version"].split(".")
    assert len(version_parts) == 3
    assert all(part.isdigit() for part in version_parts)


def test_version():
    """Test version is available."""
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__.split(".")) == 3  # Major.Minor.Patch
