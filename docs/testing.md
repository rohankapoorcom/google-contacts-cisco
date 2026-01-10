# Testing Guide

This document outlines testing standards, best practices, and guidelines for the google-contacts-cisco project.

## Table of Contents

- [Overview](#overview)
- [CI/CD Pipeline](#cicd-pipeline)
- [Running Tests](#running-tests)
- [Test Organization](#test-organization)
- [Writing Tests](#writing-tests)
- [Test Fixtures](#test-fixtures)
- [Mocking](#mocking)
- [Coverage](#coverage)
- [Best Practices](#best-practices)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

## Overview

### Testing Philosophy

Our testing approach emphasizes:

1. **Quality over Quantity**: 80% coverage with thorough tests > 100% coverage with superficial tests
2. **Fast Execution**: Unit tests should run in milliseconds, full suite in seconds
3. **Isolation**: Tests should be independent and not affect each other
4. **Clarity**: Test names should clearly describe what is being tested
5. **Maintainability**: Tests should be easy to understand and modify

### Test Types

- **Unit Tests**: Test individual functions/classes in isolation
- **Integration Tests**: Test component interactions (e.g., service + repository + database)
- **End-to-End Tests**: Test complete user flows through the application

### Coverage Goals

- **Overall**: 80% minimum
- **Critical Modules**: 95% minimum
  - `services/`: Business logic
  - `repositories/`: Data access
  - `models/`: Database models
  - `auth/`: Authentication
- **High Priority**: 85% minimum
  - `api/`: API endpoints
  - `schemas/`: Data validation

## CI/CD Pipeline

### Overview

The project uses GitHub Actions for continuous integration and continuous deployment. All tests, linting, and quality checks run automatically on every pull request and push to main.

### Workflow Triggers

The CI pipeline runs on:

1. **Pull Requests** to `main` branch
   - All quality checks must pass before merging
   - Provides fast feedback on code changes

2. **Pushes** to `main` branch
   - Validates merged code
   - Ensures main branch always passes tests

3. **Daily Schedule** (6 AM UTC)
   - Catches dependency issues
   - Detects breaking changes in external services

4. **Manual Dispatch**
   - On-demand workflow runs
   - Useful for testing workflow changes

### CI Jobs

#### 1. Lint Job

Runs code quality checks:
- **Ruff**: Fast Python linter for code quality
- **Black**: Code formatting verification
- **Mypy**: Static type checking

```bash
# Replicate locally:
uv run ruff check .
uv run black --check .
uv run mypy google_contacts_cisco
```

**Fail Conditions**:
- Any linting violations
- Code formatting issues
- Type checking errors

#### 2. Test Job

Runs comprehensive test suite across Python versions:

**Matrix**: Python 3.10, 3.11, 3.12, 3.13

**Test Execution**:
- Full pytest suite with coverage
- Coverage threshold: 80% minimum
- XML and HTML coverage reports generated

**Optimizations**:
- Dependency caching via uv
- Pytest cache for faster reruns
- Parallel matrix execution

**Artifacts**:
- Coverage XML report (30 days retention)
- Coverage HTML report (30 days retention)

```bash
# Replicate locally (matches CI):
uv run pytest \
  --cov=google_contacts_cisco \
  --cov-report=xml \
  --cov-report=term-missing \
  --cov-report=html \
  --cov-fail-under=80 \
  -v
```

**Fail Conditions**:
- Any test failures
- Coverage below 80%
- Test errors or crashes

#### 3. Frontend Checks Job

Validates frontend code quality:
- Installs Node.js dependencies
- Runs frontend linting (if configured)
- Runs frontend tests (if configured)
- Builds production bundle

```bash
# Replicate locally:
cd frontend
npm ci
npm run lint     # If configured
npm test         # If configured
npm run build
```

**Fail Conditions**:
- Linting errors
- Test failures
- Build errors

#### 4. Summary Job

Provides consolidated results:
- Aggregates all job results
- Creates summary in GitHub Actions UI
- Sets overall workflow status

### Quality Gates

**All PRs must pass**:
- ✅ Ruff linting (zero violations)
- ✅ Black formatting (properly formatted)
- ✅ Mypy type checking (zero errors)
- ✅ All tests passing on Python 3.10-3.13
- ✅ Coverage ≥ 80%
- ✅ Frontend build successful

### Viewing CI Results

#### In Pull Requests:
1. Navigate to your PR
2. Scroll to "Checks" section
3. View detailed logs for any failures
4. Re-run failed jobs if needed

#### In GitHub Actions Tab:
1. Go to repository → Actions
2. Select "CI - Tests and Linting" workflow
3. View run history and logs
4. Download coverage artifacts

### Downloading Coverage Reports

Coverage reports are uploaded as artifacts (Python 3.12 only):

1. Go to Actions → Select workflow run
2. Scroll to "Artifacts" section
3. Download:
   - `coverage-xml`: Machine-readable format
   - `coverage-html`: Interactive HTML report

### Local Testing to Match CI

To ensure your changes will pass CI before pushing:

```bash
# Full CI simulation
./scripts/test.sh                    # Run tests with coverage
uv run ruff check .                  # Lint
uv run black --check .               # Format check
uv run mypy google_contacts_cisco    # Type check

# Or use the dev script that runs all checks
./scripts/dev.sh --check-all
```

### Debugging CI Failures

#### Linting Failures

```bash
# Check what failed
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run black .
```

#### Type Checking Failures

```bash
# Run mypy locally
uv run mypy google_contacts_cisco

# Show error context
uv run mypy --show-error-context google_contacts_cisco

# Ignore specific errors (use sparingly)
# Add inline: # type: ignore[error-code]
```

#### Test Failures

```bash
# Run failing test with verbose output
./scripts/test.sh -vv -k test_name

# Run with debugging
./scripts/test.sh -s -k test_name

# Check specific Python version
uv run --python 3.10 pytest
```

#### Coverage Failures

```bash
# Generate detailed coverage report
./scripts/coverage-report.sh

# Identify missing coverage
python scripts/verify-coverage.py

# View HTML report
open htmlcov/index.html
```

### CI Configuration Files

- **Workflow**: `.github/workflows/ci.yml`
- **Python Config**: `pyproject.toml` (pytest, ruff, black, mypy)
- **Dependencies**: `pyproject.toml` (dependency-groups.dev)
- **Test Scripts**: `scripts/test.sh`, `scripts/coverage-report.sh`

### Best Practices for CI

1. **Run tests locally before pushing**
   ```bash
   ./scripts/test.sh && uv run ruff check . && uv run black --check .
   ```

2. **Fix linting issues immediately**
   - Don't disable linting rules without good reason
   - Use `ruff --fix` for auto-fixable issues

3. **Maintain coverage above 80%**
   - Add tests for new code
   - Verify coverage locally: `./scripts/coverage-report.sh`

4. **Keep CI green**
   - Don't merge failing PRs
   - Fix broken CI immediately
   - Daily runs catch dependency issues early

5. **Review CI logs on failures**
   - Read full error messages
   - Check all job logs, not just failed ones
   - Look for patterns in test failures

### Scheduled Runs

Daily automated runs (6 AM UTC):
- Detect dependency issues
- Catch breaking changes in Google APIs
- Verify tests remain stable
- No notifications unless failed

**If scheduled run fails**:
1. Check GitHub Actions → CI workflow
2. Review failure logs
3. Determine if issue is:
   - Dependency version conflict
   - External API change
   - Test flakiness
4. Create issue and fix promptly

## Running Tests

### Basic Commands

```bash
# Run all tests with coverage
./scripts/test.sh

# Run tests without coverage (faster)
./scripts/test.sh --no-cov

# Run tests in verbose mode
./scripts/test.sh --verbose

# Run fast tests only (skip slow tests)
./scripts/test.sh --fast

# Run specific test file
./scripts/test.sh tests/unit/services/test_sync_service.py

# Run specific test function
./scripts/test.sh -k test_sync_contacts

# Run tests with specific markers
./scripts/test.sh -m unit
./scripts/test.sh -m "unit and not slow"
```

### Coverage Reports

```bash
# Generate comprehensive coverage reports
./scripts/coverage-report.sh

# Verify coverage and identify gaps
python scripts/verify-coverage.py

# Check only critical modules
python scripts/verify-coverage.py --critical-only

# Fail if below threshold
python scripts/verify-coverage.py --fail-under 80
```

### Using pytest directly

```bash
# Run with uv
uv run pytest

# With coverage
uv run pytest --cov=google_contacts_cisco

# Specific markers
uv run pytest -m unit
uv run pytest -m "not slow"

# With output capture disabled (see print statements)
uv run pytest -s
```

## Test Organization

### Directory Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_main.py             # Application entry point tests
├── test_version.py          # Version tests
└── unit/                    # Unit tests
    ├── api/                 # API endpoint tests
    │   ├── test_routes.py
    │   ├── test_google.py
    │   └── test_directory_routes.py
    ├── services/            # Service layer tests
    │   ├── test_sync_service.py
    │   ├── test_google_client.py
    │   └── test_xml_formatter.py
    ├── repositories/        # Data access tests
    │   ├── test_contact_repository.py
    │   └── test_sync_repository.py
    ├── auth/                # Authentication tests
    │   └── test_oauth.py
    └── utils/               # Utility tests
        └── test_phone_utils.py
```

### Test File Naming

- **Test files**: `test_*.py` or `*_test.py`
- **Test classes**: `Test*` (e.g., `TestContactService`)
- **Test functions**: `test_*` (e.g., `test_create_contact`)

### Test Markers

```python
@pytest.mark.unit          # Unit test
@pytest.mark.integration   # Integration test
@pytest.mark.e2e           # End-to-end test
@pytest.mark.slow          # Slow running test (>1 second)
```

## Writing Tests

### Test Structure: Arrange-Act-Assert (AAA)

```python
def test_create_contact(db_session):
    # Arrange: Set up test data and dependencies
    contact_data = {
        "resource_name": "people/12345",
        "display_name": "John Doe",
    }
    
    # Act: Execute the code being tested
    contact = Contact(**contact_data)
    db_session.add(contact)
    db_session.commit()
    
    # Assert: Verify the results
    assert contact.id is not None
    assert contact.display_name == "John Doe"
    assert contact.deleted is False
```

### Test Naming Conventions

Test names should clearly describe:
1. What is being tested
2. Under what conditions
3. What the expected behavior is

```python
# Good test names
def test_sync_service_creates_new_contacts():
    """Should create contacts that don't exist in database."""
    pass

def test_sync_service_handles_deleted_contacts():
    """Should mark contacts as deleted when removed from Google."""
    pass

def test_search_by_phone_normalizes_input():
    """Should find contacts regardless of phone number format."""
    pass

# Bad test names
def test_sync():  # Too vague
    pass

def test_1():  # Meaningless
    pass
```

### Descriptive Docstrings

Every test should have a docstring explaining its purpose:

```python
def test_contact_with_multiple_phone_numbers(db_session):
    """Test contact with multiple phone numbers.
    
    Verifies that:
    - Contact can have multiple phone numbers
    - Phone numbers maintain correct relationship
    - Primary phone number can be identified
    """
    # Test implementation...
```

## Test Fixtures

### Using Shared Fixtures

Fixtures are defined in `tests/conftest.py` and automatically available to all tests:

```python
def test_example(db_session, sample_contact):
    """Example using shared fixtures."""
    # db_session: Database session
    # sample_contact: Pre-created contact
    
    assert sample_contact.id is not None
    contact = db_session.query(Contact).first()
    assert contact == sample_contact
```

### Available Fixtures

#### Database Fixtures

- `test_engine`: SQLite in-memory database engine
- `db_session`: Database session with automatic rollback
- `sample_contact`: Basic contact
- `sample_contact_with_phones`: Contact with phone numbers
- `sample_contacts_batch`: List of 5 contacts
- `sample_sync_state`: Sync state object

#### API Fixtures

- `test_client`: FastAPI TestClient for API testing

#### Mock Fixtures

- `mock_google_credentials`: Mock OAuth credentials
- `mock_google_people_service`: Mock Google People API service
- `sample_google_contact_response`: Sample API response data

#### Utility Fixtures

- `temp_test_dir`: Temporary directory for test files
- `temp_token_file`: Temporary token file path

### Creating Custom Fixtures

```python
@pytest.fixture
def custom_contact(db_session):
    """Create a custom contact for specific test needs."""
    contact = Contact(
        resource_name="people/custom",
        display_name="Custom Contact",
        organization="Test Org",
    )
    db_session.add(contact)
    db_session.commit()
    return contact

def test_with_custom_fixture(custom_contact):
    """Test using custom fixture."""
    assert custom_contact.organization == "Test Org"
```

### Fixture Scopes

- `function` (default): New instance per test function
- `class`: Shared within test class
- `module`: Shared within test module
- `session`: Shared across all tests

```python
@pytest.fixture(scope="session")
def expensive_resource():
    """Create once for entire test session."""
    resource = create_expensive_resource()
    yield resource
    resource.cleanup()
```

## Mocking

### When to Mock

Mock external dependencies:
- ✅ Google API calls
- ✅ File system operations (when appropriate)
- ✅ Network requests
- ✅ Time-dependent operations
- ❌ Internal business logic (test it directly)
- ❌ Database operations (use test database)

### Using unittest.mock

```python
from unittest.mock import Mock, patch, MagicMock

def test_google_api_call():
    """Test Google API integration with mocking."""
    with patch('google_contacts_cisco.services.google_client.build') as mock_build:
        # Set up mock
        mock_service = Mock()
        mock_service.people().connections().list().execute.return_value = {
            "connections": [],
            "nextPageToken": None,
        }
        mock_build.return_value = mock_service
        
        # Test code that uses Google API
        client = GoogleClient()
        contacts = client.fetch_contacts()
        
        # Verify
        assert contacts == []
        mock_service.people().connections().list.assert_called_once()
```

### Using pytest-mock

```python
def test_with_pytest_mock(mocker):
    """Test using pytest-mock plugin."""
    # Mock a function
    mock_fetch = mocker.patch(
        'google_contacts_cisco.services.google_client.GoogleClient.fetch_contacts'
    )
    mock_fetch.return_value = []
    
    # Test code...
    result = some_function_that_calls_fetch_contacts()
    
    # Verify
    assert result is not None
    mock_fetch.assert_called_once()
```

### Mocking Tips

1. **Mock at the boundary**: Mock external services, not internal code
2. **Use spec**: Add `spec=True` to ensure mock has correct interface
3. **Return realistic data**: Mock return values should match real API responses
4. **Verify calls**: Assert that mocks were called correctly
5. **Clean up**: Use context managers or fixtures to ensure mocks are cleaned up

## Coverage

### Viewing Coverage Reports

```bash
# Terminal report
uv run pytest --cov=google_contacts_cisco --cov-report=term-missing

# HTML report (interactive)
./scripts/coverage-report.sh
open htmlcov/index.html

# Verify coverage and get recommendations
python scripts/verify-coverage.py
```

### Understanding Coverage Metrics

- **Statement Coverage**: Percentage of code lines executed
- **Branch Coverage**: Percentage of decision branches taken
- **Missing Lines**: Lines not executed during tests

### Improving Coverage

1. **Identify gaps**: Use `python scripts/verify-coverage.py`
2. **View HTML report**: See exactly which lines aren't covered
3. **Focus on critical paths**: Prioritize business logic and error handling
4. **Test edge cases**: Empty inputs, invalid data, boundary conditions
5. **Test error paths**: Exceptions, validation failures, API errors

### Coverage Exclusions

Some code is intentionally excluded from coverage:

```python
def __repr__(self):  # Excluded: Debug-only method
    return f"<Contact {self.display_name}>"

if __name__ == "__main__":  # Excluded: Entry point
    main()

if TYPE_CHECKING:  # Excluded: Type checking only
    from typing import Optional
```

Add `# pragma: no cover` to exclude specific lines:

```python
except Exception as e:  # pragma: no cover
    # This should never happen, defensive programming
    logger.critical(f"Unexpected error: {e}")
    raise
```

## Best Practices

### Do's ✅

1. **Write descriptive test names**
   ```python
   def test_contact_repository_creates_contact_with_phone_numbers():
       """Test that repository correctly creates contacts with phone numbers."""
   ```

2. **Test one concept per test**
   ```python
   def test_contact_creation():
       """Test basic contact creation."""
       # Test only creation, not updating or deletion
   ```

3. **Use fixtures for common setup**
   ```python
   def test_with_fixture(sample_contact):
       """Reuse fixtures instead of duplicating setup code."""
   ```

4. **Test edge cases**
   ```python
   def test_search_with_empty_string():
   def test_search_with_special_characters():
   def test_search_with_very_long_input():
   ```

5. **Test error conditions**
   ```python
   def test_sync_service_handles_api_error():
       """Should handle API errors gracefully."""
       with pytest.raises(SyncError):
           service.sync()
   ```

6. **Make tests independent**
   ```python
   # Each test should work regardless of other tests
   def test_a():
       contact = create_contact()  # Own setup
       
   def test_b():
       contact = create_contact()  # Own setup
   ```

### Don'ts ❌

1. **Don't test implementation details**
   ```python
   # Bad: Testing internal variable names
   def test_internal_variable():
       service = SyncService()
       assert service._internal_cache is not None  # Fragile!
   
   # Good: Test behavior
   def test_caching_behavior():
       service = SyncService()
       result1 = service.get_data()
       result2 = service.get_data()
       assert result1 == result2  # Same result cached
   ```

2. **Don't write tests that depend on order**
   ```python
   # Bad: Tests depend on execution order
   shared_state = {}
   
   def test_a():
       shared_state['value'] = 1
   
   def test_b():
       assert shared_state['value'] == 1  # Breaks if run alone!
   ```

3. **Don't make tests too complex**
   ```python
   # Bad: Complex test logic
   def test_complex():
       for i in range(10):
           if i % 2 == 0:
               result = function_a(i)
           else:
               result = function_b(i)
           # Hard to understand what's being tested!
   
   # Good: Simple, focused tests
   def test_even_numbers():
       result = function_a(2)
       assert result == expected
   ```

4. **Don't test third-party libraries**
   ```python
   # Bad: Testing SQLAlchemy
   def test_sqlalchemy_commit():
       session.commit()  # Trust SQLAlchemy works
   
   # Good: Test your code
   def test_repository_saves_contact():
       repo.save(contact)
       assert repo.get(contact.id) == contact
   ```

5. **Don't use real external services**
   ```python
   # Bad: Real API call
   def test_google_api():
       service = GoogleClient()
       contacts = service.fetch_contacts()  # Real API call!
   
   # Good: Mock external service
   def test_google_api(mock_google_people_service):
       service = GoogleClient(mock_google_people_service)
       contacts = service.fetch_contacts()
   ```

## Common Patterns

### Testing API Endpoints

```python
def test_health_endpoint(test_client):
    """Test health check endpoint."""
    response = test_client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
```

### Testing Database Operations

```python
def test_contact_creation(db_session):
    """Test creating a contact in database."""
    contact = Contact(
        resource_name="people/123",
        display_name="Test User"
    )
    db_session.add(contact)
    db_session.commit()
    
    # Verify it was saved
    saved = db_session.query(Contact).filter_by(
        resource_name="people/123"
    ).first()
    assert saved is not None
    assert saved.display_name == "Test User"
```

### Testing Exceptions

```python
def test_invalid_input_raises_exception():
    """Test that invalid input raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        validate_phone_number("invalid")
    
    assert "invalid phone number" in str(exc_info.value).lower()
```

### Testing Async Functions

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await async_fetch_data()
    assert result is not None
```

### Parametrized Tests

```python
@pytest.mark.parametrize("input,expected", [
    ("+1-555-0100", "+15550100"),
    ("555-0100", "+15550100"),
    ("(555) 010-0", "+15550100"),
])
def test_phone_normalization(input, expected):
    """Test phone number normalization with various formats."""
    result = normalize_phone_number(input)
    assert result == expected
```

## Troubleshooting

### Tests Fail Intermittently

**Problem**: Tests pass sometimes but fail other times.

**Solutions**:
- Remove time-dependent logic (use fixed times in tests)
- Ensure test isolation (clean up after each test)
- Check for race conditions in async code
- Verify database cleanup between tests

### Tests Are Slow

**Problem**: Test suite takes too long to run.

**Solutions**:
- Use in-memory database (SQLite `:memory:`)
- Mock external API calls
- Mark slow tests with `@pytest.mark.slow`
- Run fast tests during development: `./scripts/test.sh --fast`
- Use appropriate fixture scopes

### Coverage Is Low

**Problem**: Coverage percentage below 80%.

**Solutions**:
1. Run: `python scripts/verify-coverage.py`
2. Open HTML report: `open htmlcov/index.html`
3. Identify uncovered lines (marked in red)
4. Add tests for:
   - Error paths and exception handling
   - Edge cases and boundary conditions
   - Validation logic
   - Different code branches

### Import Errors

**Problem**: `ModuleNotFoundError` or `ImportError` in tests.

**Solutions**:
- Ensure you're in project root
- Run with `uv run pytest`
- Check that `__init__.py` files exist
- Verify PYTHONPATH includes project root

### Database Errors

**Problem**: Database locked, constraint violations, etc.

**Solutions**:
- Use `db_session` fixture (auto-rollback)
- Don't share database state between tests
- Use fresh database for each test
- Check for proper cleanup in fixtures

### Mock Not Working

**Problem**: Mocks not being used or assertions failing.

**Solutions**:
- Patch at the right location (where imported, not where defined)
- Use `spec=True` to ensure correct interface
- Verify mock is called: `mock.assert_called()`
- Check mock is set up before code runs

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Python unittest.mock Guide](https://docs.python.org/3/library/unittest.mock.html)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy Testing Guide](https://docs.sqlalchemy.org/en/14/orm/session_transaction.html#session-testing)

## Contributing

When adding new features:

1. ✅ Write tests alongside implementation (TDD)
2. ✅ Ensure tests cover critical paths
3. ✅ Run full test suite before committing
4. ✅ Verify coverage meets thresholds
5. ✅ Update this documentation if needed

Remember: **Tests are documentation**. Write tests that clearly demonstrate how your code should be used and what it should do.
