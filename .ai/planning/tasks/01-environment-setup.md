# Task 1.1: Environment Setup

## Overview

Set up the development environment and project structure for the Google Contacts Cisco IP Phone Integration application.

## Priority

**P0 (Critical)** - Required for MVP

## Dependencies

None - This is the initial setup task

## Objectives

1. Verify Python 3.10+ is installed (devcontainer provides this)
2. Install and configure `uv` package manager
3. Install core dependencies using `uv`
4. Configure development tools
5. Create project structure with all necessary directories and files
6. Define version number in dedicated file

## Technical Context

### Technology Stack
- **Language**: Python 3.10+
- **Package Manager**: uv (modern, fast Python package manager)
- **Web Framework**: FastAPI
- **Database**: SQLite with SQLAlchemy ORM
- **XML Library**: lxml
- **HTTP Client**: aiohttp (async)
- **Testing**: pytest
- **Code Quality**: black (formatter), mypy (type checker), ruff (linter)

### Development Environment
- **Container**: Devcontainer (Python 3.13)
- No virtual environment needed - devcontainer provides isolated environment

### Project Structure
```
google_contacts_cisco/
├── __init__.py
├── main.py                 # Application entry point
├── config.py               # Configuration management
├── models/                 # Data models
│   ├── __init__.py
│   ├── contact.py
│   ├── phone_number.py
│   └── sync_state.py
├── services/               # Business logic
│   ├── __init__.py
│   ├── google_client.py    # Google API client
│   ├── contact_service.py
│   ├── sync_service.py
│   ├── xml_formatter.py
│   └── search_service.py
├── repositories/           # Data access
│   ├── __init__.py
│   ├── contact_repository.py
│   └── sync_repository.py
├── api/                    # API endpoints
│   ├── __init__.py
│   ├── routes.py
│   └── schemas.py          # Request/response schemas
├── auth/                   # Authentication
│   ├── __init__.py
│   └── oauth.py
├── templates/              # Frontend templates
│   ├── base.html
│   ├── index.html
│   ├── oauth_setup.html
│   └── contacts.html
├── static/                 # Static files (CSS, JS)
│   ├── css/
│   └── js/
└── utils/                  # Utilities
    ├── __init__.py
    ├── phone_normalizer.py
    └── logger.py
```

## Acceptance Criteria

- [ ] Python 3.10+ is verified and available in devcontainer
- [ ] `uv` package manager is installed and configured
- [ ] All directories in project structure are created
- [ ] All `__init__.py` files are created
- [ ] Version file is created with proper format
- [ ] Core dependencies are installed using `uv` (see requirements below)
- [ ] Development tools (black, mypy, pytest) are configured
- [ ] Devcontainer is updated to use `uv`
- [ ] A simple "hello world" FastAPI app runs successfully
- [ ] Tests can be run with pytest

## Implementation Steps

### 1. Verify Python Installation

The devcontainer provides Python 3.13 by default. Verify:

```bash
python --version  # Should be 3.13 or higher
```

### 2. Install uv Package Manager

Install `uv` - a fast Python package manager written in Rust:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or if already in devcontainer, you can install via pip (one-time bootstrap):

```bash
pip install uv
```

Verify installation:

```bash
uv --version
```

### 3. Update Devcontainer to Use uv

Update `.devcontainer/devcontainer.json` to use `uv` instead of `pip`:

```json
{
  "name": "Python Development",
  "image": "mcr.microsoft.com/devcontainers/python:3.13",
  "features": {},
  "postCreateCommand": "pip install uv && uv pip install --upgrade pip && uv pip install -e '.[dev]'",
  "customizations": {
    "vscode": {
      "settings": {
        "python.defaultInterpreterPath": "/usr/local/bin/python",
        "python.linting.enabled": true,
        "python.linting.pylintEnabled": false,
        "python.linting.mypyEnabled": true,
        "python.formatting.provider": "black",
        "python.testing.pytestEnabled": true,
        "python.testing.unittestEnabled": false,
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
          "source.organizeImports": true
        },
        "[python]": {
          "editor.defaultFormatter": "ms-python.black-formatter",
          "editor.formatOnSave": true
        }
      },
      "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "ms-python.black-formatter",
        "ms-python.mypy-type-checker",
        "ms-python.pytest"
      ]
    }
  },
  "remoteUser": "vscode"
}
```

### 4. Create Version File

Create `google_contacts_cisco/_version.py` (similar to [tesiratomqtt versioning](https://github.com/rohankapoorcom/tesiratomqtt/blob/main/src/_version.py)):

```python
"""Version information for google-contacts-cisco."""

__version_info__ = (0, 1, 0)
__version__ = ".".join(map(str, __version_info__))
```

### 5. Create Project Directory Structure

Create all directories listed in the project structure above:

```bash
mkdir -p google_contacts_cisco/{models,services,repositories,api,auth,templates,static/{css,js},utils}
```

### 6. Create __init__.py Files

Create empty `__init__.py` files in each Python package directory.

Update the main `google_contacts_cisco/__init__.py` to expose version:

```python
"""Google Contacts Cisco IP Phone Integration."""

from ._version import __version__, __version_info__

__all__ = ["__version__", "__version_info__"]
```

### 7. Update pyproject.toml

Update `pyproject.toml` to use dynamic versioning:

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "google-contacts-cisco"
dynamic = ["version"]
description = "Google Contacts integration for Cisco IP Phones"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.12.0",
    "google-api-python-client>=2.100.0",
    "google-auth>=2.25.0",
    "google-auth-oauthlib>=1.1.0",
    "lxml>=5.0.0",
    "aiohttp>=3.9.0",
    "python-dotenv>=1.0.0",
    "phonenumbers>=8.13.0",
]

[project.optional-dependencies]
dev = [
    "black>=23.11.0",
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.0",
    "pytest-mock>=3.12.0",
    "mypy>=1.7.0",
    "ruff>=0.1.6",
    "httpx>=0.25.0",
    "types-requests>=2.31.0",
]

[tool.setuptools.dynamic]
version = {attr = "google_contacts_cisco._version.__version__"}

[tool.black]
line-length = 88
target-version = ['py310', 'py311', 'py312', 'py313']
include = '\.pyi?$'
extend-exclude = '''
/(
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | venv
  | _build
  | buck-out
  | build
  | dist
)/
'''

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--strict-config",
    "--verbose",
]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
]

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
disallow_incomplete_defs = false
check_untyped_defs = true
disallow_untyped_decorators = false
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true
show_error_codes = true

[[tool.mypy.overrides]]
module = [
    "tests.*",
]
disallow_untyped_defs = false

[tool.coverage.run]
source = ["google_contacts_cisco"]
omit = [
    "*/tests/*",
    "*/test_*.py",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@abstractmethod",
]
```

### 8. Remove requirements.txt files

Since we're using `pyproject.toml` with `uv`, we don't need separate `requirements.txt` and `requirements-dev.txt` files. Delete them:

```bash
rm requirements.txt requirements-dev.txt
```

### 9. Install Dependencies Using uv

Install all dependencies including dev dependencies:

```bash
uv pip install -e '.[dev]'
```

This installs the package in editable mode with all development dependencies.

### 10. Create Simple FastAPI App

Create `google_contacts_cisco/main.py`:

```python
"""Main application entry point."""
from fastapi import FastAPI
from ._version import __version__

app = FastAPI(
    title="Google Contacts Cisco Directory",
    description="Web application for syncing Google Contacts to Cisco IP Phones",
    version=__version__
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Google Contacts Cisco Directory API"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
```

### 11. Test FastAPI App

```bash
uvicorn google_contacts_cisco.main:app --reload
```

Visit `http://localhost:8000` and `http://localhost:8000/docs` to verify.

You should see the version number in the API docs.

### 12. Create Basic Test

Create `tests/test_main.py`:

```python
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
```

Create `tests/test_version.py`:

```python
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
```

### 13. Run Tests

```bash
pytest
```

## Verification

After completing this task:
1. The project structure should match the specified layout
2. `uv` should be installed and working: `uv --version`
3. All dependencies should be installed via `uv`
4. Version file should exist and be importable
5. The FastAPI app should run without errors and display correct version
6. Tests should pass successfully (including version tests)
7. Code formatting with `black .` should work
8. Type checking with `mypy .` should work (may have warnings initially)
9. Devcontainer should be configured to use `uv`

### Quick Verification Commands

```bash
# Check uv installation
uv --version

# Check version
python -c "from google_contacts_cisco._version import __version__; print(__version__)"

# Run tests
pytest

# Format code
black .

# Type check
mypy google_contacts_cisco

# Run application
uvicorn google_contacts_cisco.main:app --reload
```

## Notes

- **No virtual environment needed**: The devcontainer provides an isolated environment
- **Use uv for all package operations**: Faster and more reliable than pip
- **Version file pattern**: Following the [tesiratomqtt approach](https://github.com/rohankapoorcom/tesiratomqtt/blob/main/src/_version.py) for clean version management
- **Dynamic versioning**: pyproject.toml reads version from `_version.py` automatically
- Ensure all file paths use forward slashes (/) for cross-platform compatibility
- The devcontainer automatically rebuilds and installs dependencies on startup

## Related Documentation

- FastAPI: https://fastapi.tiangolo.com/
- uv Package Manager: https://github.com/astral-sh/uv
- SQLAlchemy: https://docs.sqlalchemy.org/
- Google People API: https://developers.google.com/people
- Version file example: https://github.com/rohankapoorcom/tesiratomqtt/blob/main/src/_version.py

## Estimated Time

2-3 hours

