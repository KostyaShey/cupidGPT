# CupidGPT Test Suite

This directory contains comprehensive tests for the CupidGPT appointment creation process.

## Test Structure

### `conftest.py`
Contains pytest fixtures and configuration:
- `temp_db`: Temporary database for testing
- `db_manager`: DatabaseManager instance with test database
- `mock_llm_client`: Mocked LLM client for testing without API calls
- `appointment_manager`: AppointmentManager with mocked dependencies
- `test_user`: Single test user fixture
- `test_paired_users`: Two paired users for testing sharing functionality
- `future_datetime` / `past_datetime`: Datetime fixtures for testing

### `test_appointment_creation.py`
Unit tests for appointment creation:
- **TestCreateAppointmentFromText**: Tests for natural language appointment creation
  - Successful creation
  - Past date validation
  - LLM extraction failures
  - Minimal details handling
  - Invalid user handling
  - Exception handling

- **TestCreateAppointmentManual**: Tests for manual appointment creation
  - Successful creation with all fields
  - Past date validation
  - Empty title validation
  - Special characters handling
  - Invalid user handling

- **TestAppointmentRetrieval**: Tests for retrieving appointments
  - Empty list handling
  - Multiple appointments
  - Retrieval by ID
  - Invalid ID handling

- **TestAppointmentSharing**: Tests for paired user functionality
  - Shared appointments between paired users
  - Privacy between unpaired users

- **TestAppointmentEdgeCases**: Edge cases and boundary conditions
  - Appointments at current time
  - Very long titles and descriptions
  - Unicode characters
  - Multiple appointments at same time

### `test_appointment_integration.py`
Integration tests for complete workflows:
- **TestAppointmentCreationIntegration**: End-to-end workflows
  - Complete flow from text to database
  - Paired user appointment sharing
  - Multiple appointments ordering
  - Update workflow
  - Deletion workflow
  - Conflict detection
  - Date-specific retrieval

- **TestAppointmentPermissions**: Authorization tests
  - Update permission checks
  - Delete permission checks
  - Paired user update permissions

### `test_llm_client.py`
Tests for LLM client functionality:
- **TestLLMAppointmentExtraction**: Appointment detail extraction
  - Simple appointments
  - Appointments with location
  - Relative date expressions
  - Extraction failures
  - Duration handling
  - Invalid date format handling
  - API exception handling

- **TestLLMIntentDetermination**: Intent classification
  - Appointment intent
  - Checklist intent
  - Unknown intent

- **TestDateTimeParsing**: Date/time parsing
  - Relative datetime
  - Absolute datetime
  - Parsing failures

## Running Tests

### Run all tests:
```bash
pytest tests/
```

### Run specific test file:
```bash
pytest tests/test_appointment_creation.py
```

### Run specific test class:
```bash
pytest tests/test_appointment_creation.py::TestCreateAppointmentFromText
```

### Run specific test:
```bash
pytest tests/test_appointment_creation.py::TestCreateAppointmentFromText::test_successful_appointment_creation
```

### Run with coverage:
```bash
pytest tests/ --cov=src --cov-report=html
```

### Run with verbose output:
```bash
pytest tests/ -v
```

### Run only integration tests:
```bash
pytest tests/test_appointment_integration.py -v
```

## Test Coverage

The test suite covers:
- ✅ Appointment creation from natural language text
- ✅ Manual appointment creation
- ✅ Appointment retrieval and listing
- ✅ Appointment updates and deletions
- ✅ Paired user sharing functionality
- ✅ Permission and authorization checks
- ✅ Date/time validation (past dates, future dates)
- ✅ Edge cases (unicode, special characters, long text)
- ✅ LLM integration (mocked)
- ✅ Database operations
- ✅ Error handling and validation
- ✅ Conflict detection
- ✅ Date-specific queries

## Key Testing Patterns

### Mocking LLM Calls
The tests use `unittest.mock.AsyncMock` to mock LLM API calls, avoiding actual API requests:

```python
mock_llm_client.extract_appointment_details = AsyncMock(return_value={
    'success': True,
    'title': 'Test Appointment',
    'appointment_datetime': future_date.isoformat(),
    # ... other fields
})
```

### Temporary Database
Each test uses a temporary SQLite database that is automatically cleaned up:

```python
@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)
```

### Async Testing
All async functions are tested using `pytest-asyncio`:

```python
@pytest.mark.asyncio
async def test_example(appointment_manager, test_user):
    result = await appointment_manager.create_appointment_from_text(...)
    assert result['success'] is True
```

## Dependencies

Required packages (from `requirements-dev.txt`):
- `pytest==7.4.0`
- `pytest-asyncio==0.21.1`
- `pytest-cov==4.1.0`

## Notes

- Tests are isolated and don't affect production data
- Each test uses a fresh temporary database
- LLM calls are mocked to avoid API costs and ensure deterministic results
- Tests cover both success and failure scenarios
- Integration tests verify complete workflows
- Permission tests ensure proper authorization
