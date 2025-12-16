"""Test version information."""

from google_contacts_cisco._version import __version__, __version_info__


def test_version_info():
    """Test version info tuple."""
    assert isinstance(__version_info__, tuple)
    assert len(__version_info__) == 3
    assert all(isinstance(x, int) for x in __version_info__)


def test_version_string():
    """Test version string."""
    assert isinstance(__version__, str)
    expected = ".".join(map(str, __version_info__))
    assert __version__ == expected


def test_version_format():
    """Test version string follows semantic versioning format."""
    parts = __version__.split(".")
    assert len(parts) == 3, "Version must be in format X.Y.Z"
    assert all(part.isdigit() for part in parts), "All version parts must be numeric"
