# Site Builder Migration (SBM) Python Package

This directory contains the Python modules for the Site Builder Migration (SBM) tool.

## Module Structure

- `cli.py`: Command-line interface handling
- `core/`: Core migration functionality
  - `git.py`: Git operations
  - `migration.py`: Main migration logic
  - `maps.py`: Map component handling
  - `validation.py`: Validation functions
- `scss/`: SCSS processing functionality
  - `parser.py`: Basic SCSS parsing functions
  - `enhanced_parser.py`: Enhanced style parser with multi-selector support
  - `transformer.py`: Variable/mixin transformation
  - `validator.py`: SCSS validation
  - `legacy/`: Legacy parser implementations for reference
- `oem/`: OEM-specific handlers
  - Support for different manufacturer customizations
- `utils/`: Shared utilities
  - `command.py`: Command execution
  - `logger.py`: Centralized logging
  - `path.py`: Path handling functions
  - `helpers.py`: Generic helper functions

## Usage

The package is designed to be used either through the CLI or imported programmatically:

```python
# Import via the CLI module
from sbm.cli import main

# Or import specific functionality
from sbm.scss.enhanced_parser import analyze_style_scss
from sbm.core.migration import migrate_styles
```

## Development

When adding new functionality:

1. Follow the modular structure
2. Add appropriate tests in the `tests/` directory
3. Keep functionality organized by purpose
4. Use the shared utilities for common tasks
