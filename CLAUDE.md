# CLAUDE.md - AI Assistant Context

## Project Overview

**Repository**: auto-sbm (Site Builder Migration Tool)  
**Version**: 2.0.0  
**Purpose**: Automated tool for migrating DealerInspire dealer websites from legacy SCSS themes to Site Builder format with Rich UI enhancements  
**Languages**: Python (primary), SCSS processing, Markdown documentation  
**Runtime**: Python 3.8+  
**Test Framework**: pytest  
**Code Quality**: ruff (linting), mypy (type checking)

## Setup Commands

### Environment Setup
```bash
# Install dependencies and activate virtual environment
source .venv/bin/activate
pip install -r requirements.txt

# Or use the global setup script
bash setup.sh
```

### Linting and Type Checking
```bash
# Run linting with ruff (replaces black + flake8)
source .venv/bin/activate && ruff check .
source .venv/bin/activate && ruff check --fix .

# Run type checking with mypy
source .venv/bin/activate && mypy sbm/

# Run tests
source .venv/bin/activate && python -m pytest tests/ -v
```

### CLI Usage
```bash
# Main migration command (after setup.sh)
sbm auto <theme-name>

# Or using module directly
source .venv/bin/activate && python -m sbm auto <theme-name>
```

## Project Architecture

### Entry Points
- **Main CLI**: `sbm/cli.py::cli` - Click-based CLI with Rich UI enhancements
- **Module Entry**: `sbm/__main__.py` - Allows `python -m sbm` execution
- **Global Command**: Created by `setup.sh` - `sbm` command available globally

### Core Components

#### Rich UI System (`sbm/ui/`)
- **`sbm/ui/console.py`** - SBMConsole with theming and CI/CD detection
- **`sbm/ui/progress.py`** - MigrationProgress for step-by-step tracking
- **`sbm/ui/panels.py`** - StatusPanels for migration status, errors, completion
- **`sbm/ui/prompts.py`** - InteractivePrompts for confirmations and reviews

#### SCSS Processing (`sbm/scss/`)
- **`sbm/scss/processor.py`** - SCSSProcessor for SBM pattern transformation
- **`sbm/scss/mixin_parser.py`** - CommonThemeMixinParser (50+ mixin support)
- **`sbm/scss/validator.py`** - SCSS validation and compliance checking

#### Core Migration (`sbm/core/`)
- **`sbm/core/migration.py`** - migrate_dealer_theme with Rich progress integration
- **`sbm/core/git.py`** - Git operations (branching, commits, PR creation)
- **`sbm/core/maps.py`** - Map component migration
- **`sbm/core/validation.py`** - Post-migration validation

#### OEM Handling (`sbm/oem/`)
- **`sbm/oem/stellantis.py`** - Stellantis-specific processing
- **`sbm/oem/factory.py`** - OEM handler factory
- **`sbm/oem/base.py`** - Base OEM handler

#### Configuration & Utilities (`sbm/utils/`, `sbm/config.py`)
- **`sbm/config.py`** - Config class with Rich UI settings
- **`sbm/utils/logger.py`** - Rich-enhanced logging with CI fallback
- **`sbm/utils/path.py`** - Path utilities for theme directories
- **`sbm/utils/command.py`** - Command execution utilities

### Rich UI Features

#### Visual Enhancements
- **Progress Tracking**: Multi-step progress bars for 6-step migration
- **Status Panels**: Professional panels for migration status, Git operations
- **Error Displays**: Structured error panels with syntax highlighting
- **Interactive Prompts**: Enhanced confirmations with context panels
- **Theming**: Default and high-contrast themes for accessibility

#### Migration Workflow Integration
1. **Git Operations** - Branch setup with progress tracking
2. **Docker Startup** - Container monitoring with status displays
3. **File Creation** - Site Builder file creation with progress
4. **SCSS Migration** - Style transformation with detailed progress
5. **Predetermined Styles** - OEM-specific style addition
6. **Map Components** - Component migration with tracking

## Testing Structure

### Test Organization
```
tests/
├── test_ui/                 # Rich UI component tests
│   ├── test_console.py     # Console and theming tests
│   ├── test_progress.py    # Progress tracking tests
│   └── test_panels.py      # Status panel tests
├── test_core/              # Core functionality tests
├── test_scss/              # SCSS processing tests
└── test_integration/       # End-to-end integration tests
```

### Test Commands
```bash
# Run all tests
source .venv/bin/activate && python -m pytest tests/ -v

# Run specific test modules
source .venv/bin/activate && python -m pytest tests/test_ui/ -v
source .venv/bin/activate && python -m pytest tests/test_core/ -v

# Run with coverage
source .venv/bin/activate && python -m pytest tests/ --cov=sbm --cov-report=html
```

## Rich UI Implementation Details

### Console Management
- **SBMConsole**: Centralized console with theming
- **CI Detection**: Automatic fallback to plain text in CI/CD
- **Themes**: Default and high-contrast for accessibility
- **Global Instance**: `get_console()` provides singleton

### Progress Tracking
- **MigrationProgress**: 6-step migration tracking
- **Step Tasks**: Individual progress bars for each step
- **Context Manager**: `progress_context()` for proper cleanup
- **Real-time Updates**: Live progress updates during operations

### Status Displays
- **Migration Panels**: Theme status with configuration info
- **Git Panels**: Branch status and file change summaries
- **Error Panels**: Structured error display with recovery options
- **Completion Panels**: Summary with elapsed time and statistics

## Code Quality Standards

### Linting Configuration
- **Tool**: `ruff` (replaces black + flake8)
- **Config**: Follows Python best practices
- **Auto-fix**: `ruff check --fix .` for automatic fixes

### Type Checking
- **Tool**: `mypy`
- **Coverage**: All functions should have type hints
- **Config**: Strict type checking enabled

### Code Patterns
- **Error Handling**: Custom SBMError with proper logging
- **Logging**: Rich-enhanced logger with CI fallback
- **Configuration**: Type-safe Config class
- **CLI**: Click framework with Rich integration

## Dependencies

### Core Runtime Dependencies
- `click>=8.0.0` - CLI framework
- `rich>=13.0.0` - Terminal UI enhancements
- `gitpython>=3.1.0` - Git operations
- `jinja2>=3.0.0` - Template processing
- `pyyaml>=6.0` - Configuration parsing
- `psutil>=5.9.0` - System monitoring
- `requests>=2.28.0` - HTTP requests

### Development Dependencies
- `pytest>=7.0.0` - Testing framework
- `pytest-cov>=4.0.0` - Test coverage
- `ruff>=0.1.0` - Linting and formatting
- `mypy>=1.0.0` - Static type checking
- `pre-commit>=2.17.0` - Git hooks

## Migration Workflow

### 6-Step Process
1. **Git Operations** - Branch creation and setup
2. **Docker Startup** - Environment preparation
3. **File Creation** - Site Builder file generation
4. **SCSS Migration** - Style transformation and mixin conversion
5. **Predetermined Styles** - OEM-specific additions
6. **Map Components** - Component migration

### Rich UI Integration
- Each step shows real-time progress
- Status panels display current operation
- Error handling with structured displays
- Interactive prompts for manual review
- Completion summary with statistics

## Important Notes

### CI/CD Compatibility
- Rich UI automatically detects CI environments
- Falls back to plain text output when needed
- All functionality preserved in CI mode

### Error Handling
- Structured error displays with recovery options
- Logging preserved alongside Rich output
- Graceful degradation on Rich import failures

### Performance
- Rich UI adds minimal overhead
- Progress tracking is lightweight
- No impact on core migration logic

### Accessibility
- High-contrast theme available
- Icon usage with text alternatives
- Screen reader compatible fallbacks