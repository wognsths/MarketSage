# Test Data Directory

This directory contains test files for the Parser tests.

## For real API tests

To run the real parser API tests that use the UPSTAGE API, you need to place a valid test document here:

- `test_document.pdf` - A sample PDF document for testing the parser API

These files are ignored by git and should be added manually to your local test environment.

## Automatically created test files

The test suite will automatically create several test files in this directory during test execution, including:
- `sample.txt`
- `sample.html`

These will be cleaned up automatically after the tests run. 