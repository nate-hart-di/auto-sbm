# SBM Tests

This directory contains test scripts and output for the Site Builder Migration (SBM) tool.

## Test Scripts

- `test_improved_parser_integration.py`: Tests the integrated improved style parser
- `test_scss_validator.py`: Tests the SCSS validator functionality

## Output Directory

The `output/` directory is used to store test results and output files. This directory is not tracked in Git.

## Running Tests

To run the improved parser integration test:

```bash
python tests/test_improved_parser_integration.py <slug-or-file> [--legacy] [--verbose]
```

## Test Development

When adding new tests:

1. Create test files in this directory
2. Use appropriate naming conventions
3. Ensure tests can run independently
4. Document usage in this README
