# MarketSage Test Suite

This directory contains unit tests for all MarketSage services.

## Running Tests

To run all tests:

```bash
python -m unittest discover -s test
```

To run a specific test file:

```bash
python -m unittest test.test_parser
python -m unittest test.test_kis
python -m unittest test.test_websearch
```

## Test Structure

- `test_parser.py` - Tests for the UPSTAGE document parser service
- `test_kis.py` - Tests for the Korea Investment & Securities API service
- `test_websearch.py` - Tests for the web search service
- `utils.py` - Utility functions for test data and credential management
- `output/` - Directory for test logs (automatically created, excluded from git)

## Test Environment Setup

The tests include both mock tests and real service tests. For real service tests, you need API credentials set in the `.env` file.

Required environment variables:

```dotenv
# KIS (Korea Investment & Securities) API Credentials
KIS_APP_KEY=your_kis_app_key_here
KIS_APP_SECRET=your_kis_app_secret_here

# Websearch API Credentials
SEARCH_API_KEY=your_search_api_key_here
SEARCH_ENGINE_ID=your_search_engine_id_here

# UPSTAGE Parser API Credentials
UPSTAGE_API_KEY=your_upstage_api_key_here
UPSTAGE_API_ENDPOINT=your_upstage_api_endpoint_here
```

The values set in the `.env` file are loaded through settings modules in the `app/core/settings/` directory. The tests get credential values from these settings modules.

## Test Data

The `test_data/` directory contains files used during testing. Some files are generated during test execution, while others need to be provided manually for real API testing.

For real UPSTAGE API tests, you need to add a `test_document.pdf` file in the `test_data/` directory. This file is not automatically created and must be provided manually before running the tests.

## Test Logs

All test logs are stored in the `output/` directory. Each test run creates a separate log file with a timestamp in the format:

```
test_parser_YYYYMMDD-HHMMSS.log
test_kis_YYYYMMDD-HHMMSS.log
test_websearch_YYYYMMDD-HHMMSS.log
```

These logs include detailed information about each test run, API calls, and any errors encountered. The `output/` directory is excluded from version control 