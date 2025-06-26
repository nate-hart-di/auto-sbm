# SBM Tool Refactoring

## Overview

The Site Builder Migration (SBM) tool has been refactored to improve modularity, maintainability, and extensibility. This document summarizes the changes made.

## Key Changes

1. **Modular Structure**: The monolithic script has been broken down into logical components:

   - `sbm/core/`: Core migration functionality
   - `sbm/scss/`: SCSS processing functionality
   - `sbm/utils/`: Shared utilities

2. **Improved Error Handling**: Added centralized logging and better error handling across the codebase.

3. **Enhanced Shell Scripts**: Updated shell scripts to use the new module structure.

4. **Unit Tests**: Added initial unit tests for SCSS validation.

5. **Package Organization**: Organized the code as a proper Python package that can be installed.

## Directory Structure

```
auto-sbm/
├── sbm/                     # Python package for migration logic
│   ├── __init__.py          # Package initialization
│   ├── cli.py               # Command-line interface
│   ├── core/                # Core migration components
│   │   ├── __init__.py
│   │   ├── git.py           # Git operations
│   │   ├── migration.py     # Main migration logic
│   │   ├── validation.py    # Validation functions
│   │   └── maps.py          # Map component handling
│   ├── scss/                # SCSS processing
│   │   ├── __init__.py
│   │   ├── parser.py        # SCSS parsing
│   │   ├── validator.py     # SCSS validation
│   │   ├── transformer.py   # Variable/mixin transformation
│   │   └── fixer.py         # SCSS fixing functions
│   └── utils/               # Shared utilities
│       ├── __init__.py
│       ├── command.py       # Command execution
│       ├── logger.py        # Centralized logging
│       ├── path.py          # Path handling functions
│       └── helpers.py       # Generic helper functions
├── bin/                     # Shell script wrappers
│   ├── sbm.sh               # Main entry point
│   ├── site_builder_migration.sh # Compatibility wrapper
│   ├── test-scss.sh         # SCSS testing utility
├── tests/                   # Test suite
│   ├── __init__.py
│   └── test_scss_validator.py
├── setup.py                 # Package setup for installation
├── requirements.txt         # Dependencies
└── README.md                # Documentation
```

## Usage

The basic usage remains the same:

```bash
./bin/sbm.sh <dealer-slug>
```

But now you can also use the Python module directly:

```bash
python -m sbm.cli <dealer-slug>
```

Or install the package and use it as a standalone command:

```bash
pip install -e .
sbm <dealer-slug>
```

## Benefits

1. **Better Organization**: Code is now organized into logical modules.
2. **Improved Maintainability**: Smaller files are easier to understand and maintain.
3. **Reusability**: Functions can be imported and reused across the codebase.
4. **Testability**: Modular components are easier to test independently.
5. **Extensibility**: New features can be added without modifying existing code.

## Next Steps

1. Complete the implementation of placeholder functions
2. Add more comprehensive tests
3. Update documentation
4. Add support for additional features

## Compatibility

All existing shell scripts should continue to work as before, as we've maintained the same command-line interface and provided compatibility wrappers.

## Contributing

When adding new features or fixing bugs, please follow the modular structure and add tests for your changes.
