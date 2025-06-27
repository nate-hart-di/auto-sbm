# Directory Structure Overview

The SBM tool has been reorganized to improve modularity and maintainability. Here's the current structure:

## Main Directories

- `/` (Root): Main project files and compatibility wrappers
- `/sbm/`: Core Python package with modular functionality
- `/bin/`: Shell scripts for running the tool
- `/tools/`: Utility scripts for development and testing
- `/tests/`: Test scripts and output
- `/documentation/`: Detailed documentation files
- `/logs/`: Log files (these are generated during runtime)

## Working with the Codebase

### Python Module Structure

The heart of the SBM tool is in the `/sbm/` directory, organized as a proper Python package:

```
sbm/
├── __init__.py
├── cli.py                # Command-line interface
├── core/                 # Core migration components
│   ├── __init__.py
│   ├── git.py            # Git operations
│   ├── migration.py      # Main migration logic
│   ├── validation.py     # Validation functions
│   └── maps.py           # Map component handling
├── scss/                 # SCSS processing
│   ├── __init__.py
│   ├── parser.py         # SCSS parsing
│   ├── enhanced_parser.py # Enhanced parser with multi-selector support
│   ├── validator.py      # SCSS validation
│   ├── transformer.py    # Variable/mixin transformation
│   └── legacy/           # Legacy implementations for reference
└── utils/                # Shared utilities
    ├── __init__.py
    ├── command.py        # Command execution
    ├── logger.py         # Centralized logging
    ├── path.py           # Path handling functions
    └── helpers.py        # Generic helper functions
```

### Shell Scripts

The shell scripts have been standardized and placed in the `/bin/` directory:

```
bin/
├── sbm.sh                # Main entry point
├── site_builder_migration.sh # Compatibility wrapper
├── create-pr.sh          # PR creation script
├── post-migration.sh     # Post-migration tasks
├── start-dealer.sh       # Dealer site initialization
└── test-scss-syntax.sh   # SCSS testing utility
```

### Utility Tools

Development and testing utilities are in the `/tools/` directory:

```
tools/
├── test-enhanced-parser.py  # Test the enhanced parser
├── test-improved-parser.py  # Test the improved parser
├── fix-scss-braces.py       # Fix SCSS brace issues
└── ...                      # Other utilities
```

### Documentation

Detailed documentation is kept in the `/documentation/` directory:

```
documentation/
├── ENHANCED-STYLE-EXTRACTION.md
├── FEATURES-TO-ADD.md
├── IMPROVED-STYLE-PARSER.md
└── TESTING-OEM-SUPPORT.md
```

## Key Changes

1. **Integrated Improved Style Parser**: The improved style parser has been integrated into `sbm/scss/enhanced_parser.py`
2. **Consistent Directory Structure**: Related files are kept together in logical directories
3. **Better Separation of Concerns**: Core functionality, utilities, and scripts are separated
4. **Reference Implementations**: Legacy implementations are kept for reference in appropriate subdirectories
