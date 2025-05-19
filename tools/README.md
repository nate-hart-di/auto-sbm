# SBM Tool Utilities

This directory contains utility scripts for the Site Builder Migration (SBM) tool.

## Style Parsing Utilities

- `test-enhanced-parser.py`: Test script for the enhanced style parser
- `test-improved-parser.py`: Test script for the improved multi-selector style parser
- `test-parser-with-sample.py`: Test script for running the parser on sample files
- `test-cookie-styles.py`: Test script for extracting cookie disclaimer styles

## SCSS Utilities

- `fix-scss-braces.py`: Utility to fix unbalanced braces in SCSS files
- `fix-scss-files.py`: Utility to fix common issues in SCSS files
- `reset-scss-files.py`: Utility to reset SCSS files to their original state

## Usage

These tools are primarily for development and debugging purposes. They are not meant to be used directly in the migration process.

For testing the integrated parser functionality, please use the test script in the `tests` directory:

```
python tests/test_improved_parser_integration.py <slug-or-file> [--legacy] [--verbose]
```

## Note

The improved style parser functionality has been integrated into the main SBM tool in the `sbm/scss/enhanced_parser.py` module. These standalone utility scripts are kept for reference and legacy purposes.
