# Testing Guide

This document outlines testing standards, best practices, and guidelines for the google-contacts-cisco project.

## Table of Contents

- [Overview](#overview)
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
