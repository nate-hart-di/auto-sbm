# SBM Tool Reorganization Plan

## Current Issues

1. Monolithic main script (`site_builder_migration.py`) is over 2000 lines
2. Duplicate functionality across utility scripts
3. Lack of modularity making maintenance difficult
4. No centralized error handling or logging strategy
5. SCSS validation and fixing spread across multiple tools

## Proposed Directory Structure

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
│   ├── start-dealer.sh      # Dealer starter
│   ├── post-migration.sh    # Post-migration operations
│   ├── create-pr.sh         # PR creation
│   └── test-scss.sh         # SCSS testing utility
├── tests/                   # Test suite
├── setup.py                 # Package setup for installation
├── requirements.txt         # Dependencies
└── README.md                # Updated documentation
```

## Migration Steps

1. Create the directory structure
2. Extract functionality from the monolithic script into appropriate modules:

   - Move Git operations to `sbm/core/git.py`
   - Extract SCSS processing to `sbm/scss/` modules
   - Move map migrations to `sbm/core/maps.py`
   - Create a unified command execution utility in `utils/command.py`
   - Build a centralized logging system in `utils/logger.py`

3. Create a CLI interface in `sbm/cli.py` that handles command-line arguments and orchestrates the migration process

4. Update shell scripts to use the new module structure

5. Add proper error handling and logging throughout the codebase

6. Add comprehensive tests

## Benefits

1. **Maintainability**: Smaller files are easier to understand and maintain
2. **Reusability**: Functions can be imported and reused across the codebase
3. **Testability**: Modular components are easier to test independently
4. **Extensibility**: New features can be added without modifying existing code
5. **Stability**: Better error handling and logging improves reliability

## Implementation Plan

### Phase 1: Initial Restructuring

- Create the directory structure
- Implement core utils modules
- Create package initialization files

### Phase 2: Core Functionality Migration

- Migrate Git operations to git.py
- Extract SCSS processing to scss modules
- Move map migrations to maps.py
- Create a unified CLI interface

### Phase 3: Shell Script Updates

- Update shell scripts to use the new module structure
- Ensure backward compatibility

### Phase 4: Testing and Documentation

- Create comprehensive tests
- Update documentation
- Add usage examples

### Phase 5: Finalization

- Address any remaining issues
- Performance optimizations
- Final testing
