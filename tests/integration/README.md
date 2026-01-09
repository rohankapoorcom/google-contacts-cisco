# Integration Tests

This directory contains integration tests that verify components work together correctly across the entire stack.

## Test Organization

### Working Tests ✅

#### `test_database_transactions.py` (14 tests - ALL PASSING)
Tests database operations, transactions, and data integrity:

- **Transaction Management**: Commit, rollback, and nested transactions
- **Data Integrity**: Foreign keys, cascades, unique constraints
- **Concurrency**: Concurrent operations and bulk inserts
- **Performance**: Query optimization and index effectiveness

These tests use real database operations with an in-memory SQLite database and verify:
- Transaction commits persist data
- Rollbacks undo changes properly
- Foreign key constraints are enforced
- Cascade deletes work correctly
- Unique constraints prevent duplicates
- Queries perform efficiently with proper indexes

### Skipped Tests (Pending Implementation) ⏭️

The following test files contain comprehensive test scenarios but are currently skipped pending fixes:

#### API Integration Tests
- `api/test_api_contacts.py` - Contact API endpoints
- `api/test_api_sync.py` - Sync API endpoints
- `api/test_api_search.py` - Search API endpoints
- `api/test_api_directory.py` - XML directory API endpoints

**Status**: Require FastAPI TestClient dependency injection fixes

#### Service Integration Tests
- `services/test_service_integration.py` - Service layer integration

**Status**: Require service implementation adjustments

#### OAuth Flow Tests
- `test_oauth_flow.py` - OAuth authentication flow

**Status**: Require TestClient dependency injection fixes

## Running Integration Tests

### Run All Integration Tests
```bash
uv run pytest tests/integration -v
```

### Run Only Passing Tests
```bash
uv run pytest tests/integration/test_database_transactions.py -v
```

### Run Without Coverage Requirements
```bash
uv run pytest tests/integration --no-cov -v
```

### Run Specific Test Class
```bash
uv run pytest tests/integration/test_database_transactions.py::TestDatabaseTransactionIntegration -v
```

## Test Markers

Integration tests are marked with `@pytest.mark.integration`:

```bash
# Run all integration tests
uv run pytest -m integration

# Run slow integration tests
uv run pytest -m "integration and slow"
```

## Test Structure

### Database Tests
Use `integration_db` fixture which provides:
- Fresh in-memory SQLite database for each test
- Automatic table creation/cleanup
- Transaction rollback after each test

### API Tests (When Fixed)
Will use `integration_client` fixture which provides:
- FastAPI TestClient with test database
- Mocked external dependencies (Google API)
- Full HTTP request/response testing

### Service Tests (When Fixed)
Test service layer interactions with:
- Repository pattern
- Database operations
- External service mocking

## Fixtures

### Available Fixtures

- `integration_db`: Database session for direct database testing
- `integration_test_contacts`: Pre-populated test contacts
- `integration_sync_state`: Test sync state
- `mock_credentials`: Mocked OAuth credentials
- `mock_google_api_responses`: Mocked Google API responses

See `conftest.py` for detailed fixture documentation.

## Coverage

Integration tests focus on:
- **Component Integration**: Multiple components working together
- **Data Flow**: End-to-end data transformations
- **Error Propagation**: Errors handled correctly across layers
- **Transaction Integrity**: Database consistency maintained
- **Performance**: Operations complete in reasonable time

## Future Improvements

### High Priority
1. Fix TestClient dependency injection for API tests
2. Implement service integration tests
3. Add OAuth flow integration tests

### Medium Priority
1. Add WebSocket integration tests (if applicable)
2. Add file upload/download integration tests
3. Add scheduled task integration tests

### Low Priority
1. Add load testing scenarios
2. Add chaos engineering tests
3. Add integration with external services (with test containers)

## Notes

- Integration tests use in-memory SQLite for speed
- External APIs (Google) are mocked
- Tests are isolated - no shared state between tests
- Each test gets a fresh database
- Tests should complete in <2 minutes total

## Troubleshooting

### Issue: Tests fail with "no such table"
**Solution**: Ensure test fixtures properly create database tables

### Issue: Tests timeout
**Solution**: Check for infinite loops or missing mocks

### Issue: Flaky tests
**Solution**: Avoid time-dependent assertions, use proper fixtures

### Issue: Coverage too low
**Solution**: Integration tests are excluded from coverage requirements
