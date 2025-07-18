# CLAUDE.md - AI Assistant Context

## Project Overview

**Repository**: auto-sbm (Site Builder Migration Tool)  
**Version**: 2.0.0  
**Purpose**: Production-ready automated tool for migrating DealerInspire dealer websites from legacy SCSS themes to Site Builder format  
**Architecture**: Vertical slice architecture with type safety and Rich UI  
**Languages**: Python 3.8+ (primary), SCSS processing, Markdown documentation  
**Package Management**: UV with pyproject.toml (modern Python packaging)  
**Testing**: pytest with 90%+ coverage  
**Code Quality**: ruff (linting), mypy (type checking), pre-commit hooks  
**UI Framework**: Rich for beautiful terminal interfaces

## Setup Commands

### Development Environment Setup
```bash
# Clone and setup development environment
git clone git@github.com:nate-hart-di/auto-sbm.git
cd auto-sbm

# Install in development mode with all dependencies
pip install -e .[dev]

# Or use UV for faster dependency management
uv sync --dev

# Setup pre-commit hooks for code quality
pre-commit install
```

### Environment Configuration
```bash
# Copy environment template and configure
cp .env.example .env
# Edit .env with your GitHub token and preferences

# Required environment variables:
# GITHUB_TOKEN=your_github_personal_access_token  
# GITHUB_ORG=dealerinspire
# THEMES_DIRECTORY=./themes
# BACKUP_ENABLED=true
# RICH_UI_ENABLED=true
```

### Code Quality Commands
```bash
# Linting and formatting (replaces black + flake8)
ruff check src/ --fix
ruff format src/

# Type checking with comprehensive coverage
mypy src/auto_sbm/

# Run comprehensive test suite
pytest src/ --cov=auto_sbm --cov-report=term-missing

# Run all quality checks (development)
tox
```

### CLI Usage
```bash
# Main migration command (global installation)
sbm migrate <theme-name>

# Alternative commands
sbm auto <theme-name>     # Shorthand
sbm <theme-name>          # Direct theme name

# Validation and utilities
sbm validate <theme-name>
sbm post-migrate <theme-name>

# Development mode (when working on the tool)
python -m auto_sbm.main migrate <theme-name>
```

## Project Architecture (v2.0 - Vertical Slice Design)

### **Architectural Principles**
- **🎯 Vertical Slices**: Features organized by business capability, not technical layers
- **🛡️ Type Safety**: Comprehensive Pydantic v2 models for all data validation
- **🧪 Test Coverage**: Co-located tests achieving 90%+ coverage
- **🔒 Security**: Environment-based configuration with validated settings
- **⚡ Performance**: Async processing and optimized SCSS transformation
- **🎨 Rich UI**: Professional terminal interface with CI/automation fallbacks

### **Directory Structure**
```
auto-sbm/
├── src/auto_sbm/              # Main package (src layout for editable installs)
│   ├── __init__.py           # Package initialization and exports
│   ├── config.py             # Pydantic BaseSettings with env validation
│   │
│   ├── models/               # Shared Pydantic models for type safety
│   │   ├── __init__.py
│   │   ├── theme.py          # Theme data structures and validation
│   │   ├── migration.py      # Migration state and result models
│   │   ├── scss.py           # SCSS processing data models
│   │   └── tests/            # Model validation tests
│   │
│   ├── features/             # Vertical slices by business capability
│   │   ├── migration/        # Migration orchestration and workflow
│   │   │   ├── __init__.py
│   │   │   ├── service.py    # Core migration business logic
│   │   │   ├── models.py     # Migration-specific models
│   │   │   ├── cli.py        # Migration CLI commands
│   │   │   └── tests/        # Migration feature tests
│   │   │
│   │   ├── scss_processing/  # SCSS transformation engine
│   │   │   ├── __init__.py
│   │   │   ├── processor.py  # Core SCSS transformation logic
│   │   │   ├── mixin_parser.py # SCSS mixin conversion
│   │   │   ├── validator.py  # SCSS syntax validation
│   │   │   ├── models.py     # SCSS-specific data models
│   │   │   └── tests/        # SCSS processing tests
│   │   │
│   │   ├── git_operations/   # Git workflow automation
│   │   │   ├── __init__.py
│   │   │   ├── service.py    # Git operations (add, commit, push, PR)
│   │   │   ├── models.py     # Git state and operation models
│   │   │   └── tests/        # Git operation tests
│   │   │
│   │   └── oem_handling/     # OEM-specific customizations
│   │       ├── __init__.py
│   │       ├── service.py    # OEM-specific business logic
│   │       ├── models.py     # OEM configuration models
│   │       └── tests/        # OEM handling tests
│   │
│   └── shared/               # Cross-cutting concerns and utilities
│       ├── ui/               # Rich UI components and theming
│       │   ├── __init__.py
│       │   ├── console.py    # Console management and output
│       │   ├── progress.py   # Progress tracking and status
│       │   ├── panels.py     # Status panels and layout
│       │   ├── models.py     # UI state models
│       │   └── tests/        # UI component tests
│       │
│       ├── validation/       # Validation utilities and patterns
│       │   ├── __init__.py
│       │   ├── service.py    # Common validation logic
│       │   └── tests/        # Validation tests
│       │
│       └── utils/            # Common utilities and helpers
│           ├── __init__.py
│           ├── file_operations.py # File system utilities
│           └── tests/        # Utility tests
│
├── tests/                    # Integration and end-to-end tests
│   ├── conftest.py          # Shared pytest fixtures
│   ├── integration/         # Full workflow integration tests
│   │   ├── test_full_migration.py
│   │   └── test_cli_integration.py
│   └── fixtures/            # Test data and fixtures
│
├── PRPs/                    # Project Requirements and Planning documents
│   ├── code_reviews/        # Code quality analysis reports
│   ├── ai_docs/            # AI assistant documentation
│   └── templates/          # PRP templates for new features
│
├── pyproject.toml          # Modern Python packaging configuration
├── .env.example           # Environment variable template
├── setup.sh               # Development setup script
├── CLAUDE.md              # This file - AI assistant context
└── README.md              # User documentation
```

### **Entry Points and CLI Structure**
- **Main CLI**: `src/auto_sbm/main.py` - Click-based CLI with Rich UI integration
- **Global Command**: `~/.local/bin/sbm` - Wrapper script for global access
- **Module Execution**: `python -m auto_sbm.main` - Direct module execution for development
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

---

## Legacy Architecture (v1.x - Deprecated)

*Note: This section documents the old monolithic structure for reference during migration.*

## Legacy Architecture (v1.x - Deprecated)

*Note: This section documents the old monolithic structure for reference during migration.*

### **Legacy Architectural Overview**
- **Monolithic Structure**: All-in-one package with no clear separation of concerns
- **Limited Type Safety**: Basic type hints, no comprehensive validation
- **Sparse Testing**: Inconsistent test coverage, many untested paths
- **Environment Variables**: Hardcoded values and inconsistent usage
- **Basic CLI**: Click-based, but lacks rich UI integration

### **Legacy Directory Structure**
```
auto-sbm/
├── auto_sbm/                 # Monolithic package
│   ├── __init__.py          # Package initialization
│   ├── config.py            # Configuration management (legacy)
│   ├── migration.py         # Migration logic (monolithic)
│   ├── git_operations.py    # Git operations (monolithic)
│   ├── scss_processing.py   # SCSS processing (monolithic)
│   ├── oem_handling.py      # OEM handling (monolithic)
│   └── tests/               # Tests (scattered and inconsistent)
│
├── requirements.txt         # Legacy dependency management
├── .env.example             # Environment variable template
├── setup.sh                 # Development setup script
├── CLAUDE.md                # This file - AI assistant context
└── README.md                # User documentation
```

### **Legacy Entry Points and CLI Structure**
- **Single Entry Point**: `auto_sbm/__init__.py` - Monolithic package initialization
- **Legacy CLI**: Basic Click commands without rich UI features

### Legacy Components

#### Legacy UI System
- **Basic console output**: No theming or advanced features
- **Static progress indicators**: Limited feedback during operations

#### Legacy SCSS Processing
- **Monolithic SCSS processor**: Single file for all processing logic
- **Limited validation**: Basic checks, no comprehensive SCSS compliance

#### Legacy Migration Logic
- **Single migration function**: All logic in `migration.py`
- **No separation of concerns**: Git, SCSS, and OEM logic intertwined

#### Legacy Configuration Management
- **Hardcoded values**: Many constants defined in code
- **Inconsistent environment variable usage**: Not all settings configurable via env vars

### Legacy Testing Strategy
- **Inconsistent test coverage**: Many features and paths untested
- **Basic unit tests**: Some functions and methods have tests, but coverage is spotty
- **No integration or end-to-end tests**: Legacy system not tested as a whole

---
