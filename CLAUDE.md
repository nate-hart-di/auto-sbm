# CLAUDE.md - AI Assistant Context

## 🚨 CRITICAL FILE ORGANIZATION RULES 🚨

**BEFORE CREATING ANY NEW FILE, READ THIS:**

1. **Tests** → `tests/test_*.py` (NEVER in root or sbm/)
2. **PRP docs** → `PRPs/*.md` (NEVER in root)
3. **Source code** → `sbm/*.py` (Python modules)
4. **Scripts** → `sbm/scripts/` (Specialized scripts)
5. **Documentation** → `*.md` (root directory only)
6. **Data** → `stats/raw/` (Raw statistical data)

**Common mistakes to AVOID:**

- ❌ Creating `test_*.py` in root directory
- ❌ Creating `PRP_*.md` in root directory
- ❌ Creating any test files outside `tests/`
- ❌ Creating any PRP files outside `PRPs/`

---

## Project Overview

**Repository**: auto-sbm (Site Builder Migration Tool)  
**Version**: 2.0.0  
**Purpose**: Production-ready automated tool for migrating DealerInspire dealer websites from legacy SCSS themes to Site Builder format  
**Architecture**: Vertical slice architecture### Code Quality Standards

**🚨 FILE ORGANIZATION REMINDER 🚨**

- Tests go in `tests/` directory
- PRP documents go in `PRPs/` directory
- Source code goes in `sbm/` directory
- Documentation goes in root directory

### Linting Configurationth type safety and Rich UI

**Languages**: Python 3.8+ (primary), SCSS processing, Markdown documentation  
**Package Management**: UV with pyproject.toml (modern Python packaging)  
**Testing**: pytest with 90%+ coverage  
**Code Quality**: ruff (linting), mypy (type checking), pre-commit hooks  
**UI Framework**: Rich for beautiful terminal interfaces

## 🛠️ MANDATORY AGENT WORKFLOW

**ALL AGENTS (Claude, Gemini, Codex, etc.) MUST follow this workflow for EVERY task:**

1.  **Branch First**: Never work on `master` directly. Create a new branch `feat/*`, `fix/*`, or `docs/*` before making any changes.
2.  **Version Consistency**: If making functional changes, ensure the version in `pyproject.toml` is updated using `scripts/bump_version.py`.
3.  **Changelog**: All changes (including docs) must be reflected in `CHANGELOG.md`.
4.  **Proof of Work**: Generate a walkthrough or summary of changes on the branch before merging.
5.  **Commit Often**: Small, descriptive commits are preferred over monolithic ones.

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

### **🚨 CRITICAL FILE ORGANIZATION RULES 🚨**

**ALWAYS follow these rules when creating new files:**

1. **Tests MUST go in `tests/`**
2. **PRP documents MUST go in `PRPs/`**
3. **Source code MUST go in `sbm/`**
4. **Specialized scripts MUST go in `scripts/stats/`**
5. **Raw data MUST go in `stats/raw/`**
6. **Setup scripts MUST go in root**
7. **Documentation MUST go in root**

**Examples of CORRECT file placement:**

```
✅ tests/test_new_feature.py           # Tests go in tests/
✅ PRPs/new-feature-requirements.md   # PRPs go in PRPs/
✅ sbm/new_module.py                   # Code goes in sbm/
✅ setup-new-thing.sh                 # Scripts in root
✅ NEW_DOCS.md                         # Docs in root
```

**Examples of WRONG file placement:**

```
❌ test_new_feature.py                # Test file in root
❌ new-feature-requirements.md        # PRP in root
❌ PRP_SUMMARY.md                     # PRP-related doc in root
❌ sbm/test_something.py              # Test in source directory
```

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
├── scripts/                   # Specialized automation scripts
│   └── stats/                 # Stats aggregation and backfill
├── sbm/                       # Core package
│   ├── core/                  # Core migration logic
│   ├── utils/                 # Shared utilities (tracker, logger)
│   └── ...
├── stats/                     # Statistical data and reports
│   └── raw/                   # Raw JSON data from GitHub/Local
├── tests/                     # 🚨 ALL TESTS GO HERE 🚨
├── PRPs/                      # 🚨 ALL PRP DOCUMENTS GO HERE 🚨
├── pyproject.toml             # Modern Python packaging configuration
├── .env.example              # Environment variable template
├── setup.sh                  # Development setup script
├── CLAUDE.md                 # This file - AI assistant context
└── README.md                 # User documentation
├── tests/                    # 🚨 ALL TESTS GO HERE 🚨
│   ├── conftest.py          # Shared pytest fixtures
│   ├── integration/         # Full workflow integration tests
│   │   ├── test_full_migration.py
│   │   └── test_cli_integration.py
│   ├── test_*.py            # Unit tests (test_progress_fixes.py, etc.)
│   └── fixtures/            # Test data and fixtures
│
├── PRPs/                    # 🚨 ALL PRP DOCUMENTS GO HERE 🚨
│   ├── migration-critical-fixes.md    # PRP documents
│   ├── PRP_READINESS_SUMMARY.md       # PRP-related summaries
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

**🚨 FILE PLACEMENT ENFORCEMENT 🚨**

When creating ANY new file, ALWAYS ask yourself:

1. **Is this a test?** → `tests/test_whatever.py`
2. **Is this PRP-related?** → `PRPs/whatever.md`
3. **Is this source code?** → `sbm/whatever.py`
4. **Is this a script?** → `setup-whatever.sh` (root)
5. **Is this documentation?** → `WHATEVER.md` (root)

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

**🚨 CRITICAL: ALL TEST FILES MUST GO IN `tests/` DIRECTORY 🚨**

### Test Organization

```
tests/                       # 🚨 ALL TESTS GO HERE 🚨
├── test_ui/                 # Rich UI component tests
│   ├── test_console.py     # Console and theming tests
│   ├── test_progress.py    # Progress tracking tests
│   └── test_panels.py      # Status panel tests
├── test_core/              # Core functionality tests
├── test_scss/              # SCSS processing tests
├── test_integration/       # End-to-end integration tests
├── test_*.py               # Any other unit tests
└── fixtures/               # Test data and fixtures
```

**NEVER create test files anywhere else:**

- ❌ `test_something.py` (root directory)
- ❌ `sbm/test_something.py` (source directory)
- ❌ `src/test_something.py` (src directory)
- ✅ `tests/test_something.py` (correct location)

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

_Note: This section documents the old monolithic structure for reference during migration._

## Legacy Architecture (v1.x - Deprecated)

_Note: This section documents the old monolithic structure for reference during migration._

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

## 🌳 Branching & Git Rules

- **🚨 NO DIRECT MASTER COMMITS**: Never update `master` directly. Always create a new branch.
- **Workflow**: Create branch -> checkout -> apply changes -> commit -> push.
- **Up-to-date**: Ensure your branch is rebased or merged with latest `master` before and after work.
- **Persistence**: This branching rule IS MANDATORY and must be followed by every agent reaching this context.
