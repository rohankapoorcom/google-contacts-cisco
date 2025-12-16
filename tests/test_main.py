"""Test main application."""
from fastapi.testclient import TestClient
from google_contacts_cisco.main import app
from google_contacts_cisco._version import __version__

client = TestClient(app)


def test_root():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Google Contacts Cisco Directory API"}


def test_health():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_version():
    """Test version is available."""
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__.split(".")) == 3  # Major.Minor.Patch

