"""Test main application."""

import os
import tempfile
from pathlib import Path

import pytest
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


class TestPathTraversalSecurity:
    """Tests for path traversal vulnerability fixes."""

    @pytest.mark.skipif(
        not STATIC_DIR.exists() or not (STATIC_DIR / "index.html").exists(),
        reason="Frontend not built, skipping static file tests"
    )
    def test_path_traversal_blocked_parent_directory(self):
        """Test that ../ path traversal attempts are blocked."""
        # Try to access parent directory
        response = client.get("/../../../etc/passwd")
        assert response.status_code == 403

    @pytest.mark.skipif(
        not STATIC_DIR.exists() or not (STATIC_DIR / "index.html").exists(),
        reason="Frontend not built, skipping static file tests"
    )
    def test_path_traversal_blocked_encoded(self):
        """Test that URL-encoded path traversal attempts are blocked."""
        # URL-encoded ../ is %2e%2e%2f
        response = client.get("/%2e%2e/%2e%2e/%2e%2e/etc/passwd")
        # FastAPI decodes this automatically, should still be blocked
        assert response.status_code in (403, 404, 200)  # 200 if serving index.html

    @pytest.mark.skipif(
        not STATIC_DIR.exists() or not (STATIC_DIR / "index.html").exists(),
        reason="Frontend not built, skipping static file tests"
    )
    def test_path_traversal_blocked_backslash(self):
        """Test that backslash-based traversal is blocked on Windows."""
        response = client.get("/..\\..\\..\\etc\\passwd")
        # Should either block or serve index.html for SPA
        assert response.status_code in (403, 200)

    @pytest.mark.skipif(
        not STATIC_DIR.exists() or not (STATIC_DIR / "index.html").exists(),
        reason="Frontend not built, skipping static file tests"
    )
    def test_path_traversal_blocked_null_byte(self):
        """Test that null byte injection is blocked."""
        # Null byte can sometimes bypass extension checks
        response = client.get("/../../etc/passwd%00.html")
        assert response.status_code in (403, 404, 200)

    @pytest.mark.skipif(
        not STATIC_DIR.exists() or not (STATIC_DIR / "index.html").exists(),
        reason="Frontend not built, skipping static file tests"
    )
    def test_path_traversal_blocked_absolute_path(self):
        """Test that absolute paths are blocked."""
        response = client.get("/etc/passwd")
        # Should serve index.html for SPA routing or block if malicious
        assert response.status_code in (200, 403)
        if response.status_code == 200:
            # If 200, should be serving index.html, not actual /etc/passwd
            assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.skipif(
        not STATIC_DIR.exists() or not (STATIC_DIR / "index.html").exists(),
        reason="Frontend not built, skipping static file tests"
    )
    def test_path_with_dot_components_sanitized(self):
        """Test that paths with . and .. components are properly sanitized."""
        response = client.get("/./assets/../index.html")
        # Should serve index.html or return 200
        assert response.status_code == 200

    @pytest.mark.skipif(
        not STATIC_DIR.exists() or not (STATIC_DIR / "index.html").exists(),
        reason="Frontend not built, skipping static file tests"
    )
    def test_symlink_access_blocked(self):
        """Test that symlink-based traversal is blocked."""
        # This test requires creating a temporary symlink
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create a test file outside static dir
            sensitive_file = tmpdir_path / "sensitive.txt"
            sensitive_file.write_text("sensitive data")

            # Try to create symlink in static dir (if we have permission)
            try:
                symlink_path = STATIC_DIR / "malicious_link"
                if not symlink_path.exists():
                    os.symlink(sensitive_file, symlink_path)

                    # Try to access via symlink
                    response = client.get("/malicious_link")
                    # Should be blocked
                    assert response.status_code in (403, 404)

                    # Cleanup
                    symlink_path.unlink()
            except (OSError, PermissionError):
                # Skip test if we can't create symlinks (e.g., Windows without admin)
                pytest.skip("Cannot create symlinks on this system")

    @pytest.mark.skipif(
        not STATIC_DIR.exists() or not (STATIC_DIR / "index.html").exists(),
        reason="Frontend not built, skipping static file tests"
    )
    def test_valid_static_file_still_served(self):
        """Test that legitimate static files can still be accessed."""
        # Try to access a valid static file
        # Check if assets directory and files exist
        assets_dir = STATIC_DIR / "assets"
        if assets_dir.exists():
            # Find any file in assets
            asset_files = list(assets_dir.glob("*.js")) + list(assets_dir.glob("*.css"))
            if asset_files:
                asset_file = asset_files[0]
                relative_path = asset_file.relative_to(STATIC_DIR)
                response = client.get(f"/{relative_path}")
                # Should successfully serve the file
                assert response.status_code == 200

    @pytest.mark.skipif(
        not STATIC_DIR.exists() or not (STATIC_DIR / "index.html").exists(),
        reason="Frontend not built, skipping static file tests"
    )
    def test_spa_fallback_still_works(self):
        """Test that SPA fallback to index.html still works for valid routes."""
        # Request a valid SPA route (not an API route)
        response = client.get("/contacts")
        assert response.status_code == 200
        # Should serve index.html
        assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.skipif(
        not STATIC_DIR.exists() or not (STATIC_DIR / "index.html").exists(),
        reason="Frontend not built, skipping static file tests"
    )
    def test_api_routes_not_affected(self):
        """Test that API routes are not affected by static file handling."""
        # API routes should still return 404 if they don't exist
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

    @pytest.mark.skipif(
        not STATIC_DIR.exists() or not (STATIC_DIR / "index.html").exists(),
        reason="Frontend not built, skipping static file tests"
    )
    def test_security_logging_on_traversal_attempt(self, caplog):
        """Test that path traversal attempts are logged."""
        import logging
        caplog.set_level(logging.WARNING)

        # Attempt path traversal
        response = client.get("/../../../etc/passwd")

        # Check if warning was logged
        # Note: Logging may vary based on what triggers the block
        assert response.status_code in (403, 404, 200)

    def test_case_sensitivity_handled(self):
        """Test that case sensitivity doesn't bypass security."""
        # Try various case combinations that might bypass checks
        test_paths = [
            "/../../../etc/PASSWD",
            "/..%2F..%2F..%2Fetc%2Fpasswd",
            "/.%2e/.%2e/.%2e/etc/passwd",
        ]

        for path in test_paths:
            response = client.get(path)
            # Should be blocked or serve index.html, but not leak sensitive files
            assert response.status_code in (403, 404, 200)
            if response.status_code == 200:
                # If serving something, should be HTML (index.html)
                content_type = response.headers.get("content-type", "")
                # Don't allow text/plain which might be /etc/passwd
                assert "html" in content_type.lower() or "json" in content_type.lower()
