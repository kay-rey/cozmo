# Cozmo Discord Bot Test Suite

This directory contains comprehensive tests for the Cozmo Discord Bot to ensure all functionality works correctly.

## Running Tests

### Run All Tests

```bash
python3 tests/run_all_tests.py
```

### Individual Test Categories

#### Code Structure Tests

```bash
python3 tests/test_code_structure.py
```

Validates:

- File existence and syntax
- Required components in each module
- Project structure integrity

#### Integration Tests

```bash
python3 tests/test_bot_final.py
```

Validates:

- Module imports with mock configuration
- Bot initialization
- API client setup
- Cog loading
- Configuration management

#### Startup Tests

```bash
python3 tests/test_bot_startup.py
```

Validates:

- Complete bot startup sequence
- Cog loading and registration
- Command registration
- Proper shutdown

#### Command Functionality Tests

```bash
python3 tests/test_bot_commands.py
```

Validates:

- Command registration in correct cogs
- Error handling mechanisms
- API error handling
- Cog functionality

#### Setup Verification

```bash
python3 tests/verify_bot_setup.py
```

Validates:

- Project structure
- Dependencies installation
- Configuration setup

## Test Files

| File                        | Purpose                                  |
| --------------------------- | ---------------------------------------- |
| `run_all_tests.py`          | Master test runner for all test suites   |
| `test_code_structure.py`    | Code structure and syntax validation     |
| `test_bot_final.py`         | Comprehensive integration tests          |
| `test_bot_startup.py`       | Bot startup sequence validation          |
| `test_bot_commands.py`      | Command functionality and error handling |
| `test_bot_integration.py`   | Legacy integration tests                 |
| `test_bot_comprehensive.py` | Legacy comprehensive tests               |
| `test_error_handling.py`    | Error handling validation                |
| `verify_bot_setup.py`       | Setup verification utility               |

## Test Features

### Mock Configuration

Tests use mock environment variables to avoid requiring real API keys:

- Mock Discord tokens with proper format validation
- Mock API keys for testing
- Mock channel IDs for configuration testing

### Virtual Environment Support

All tests are designed to work in virtual environments and handle:

- Proper path resolution from tests directory
- Module import path management
- Dependency verification

### Comprehensive Coverage

Tests cover:

- ✅ Code structure and syntax
- ✅ Module imports and dependencies
- ✅ Configuration management
- ✅ API client initialization
- ✅ Bot initialization and setup
- ✅ Cog loading and registration
- ✅ Command registration
- ✅ Error handling mechanisms
- ✅ Trivia questions format
- ✅ Startup and shutdown sequences

## Requirements

Tests require the same dependencies as the main bot:

- Python 3.8+
- discord.py
- aiohttp
- python-dotenv
- feedparser

Install with:

```bash
pip install -r requirements.txt
```

## Continuous Integration

The test suite is designed to be run in CI/CD environments and provides:

- Clear pass/fail status codes
- Detailed output for debugging
- Comprehensive validation of all bot components
- Mock configuration to avoid requiring secrets
