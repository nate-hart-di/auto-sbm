name: "Auto-SBM Complete Refactor - Vertical Slice Architecture with Type Safety"
description: |
  Comprehensive refactor of the auto-SBM project based on systematic code reviews and 
  agentic engineering best practices. Transform monolithic structure into maintainable 
  vertical slices with Pydantic v2 type safety, security improvements, and comprehensive testing.

## Goal

Transform the auto-SBM codebase from its current state with 47 mypy errors, 56 ruff issues, and 43% test pass rate into a production-ready tool following vertical slice architecture principles with comprehensive type safety, security, and maintainability.

**End State**: A refactored auto-SBM tool with:
- Zero linting/type errors
- 90%+ test coverage 
- Pydantic v2 models throughout
- Secure configuration management
- Vertical slice architecture
- Rich UI properly integrated

## Why

**Current Issues (from code reviews)**:
- **Type Safety Crisis**: 47 mypy errors across the codebase
- **Code Quality**: 56 ruff linting issues including 29 unused imports
- **Security Vulnerability**: Hardcoded GitHub tokens in config.json
- **Architecture**: No Pydantic models, mixed concerns, monolithic files
- **Testing**: 31/55 tests failing, only 18% file coverage
- **Maintainability**: Rich UI integration created additional type conflicts

**Business Impact**:
- Current reliability issues risk production failures
- Security vulnerabilities expose sensitive data
- Poor test coverage makes changes risky
- Maintenance overhead increasing with each feature

## What

### Core Transformations

- **Security First**: Environment-based configuration with Pydantic validation
- **Type Safety**: Full Pydantic v2 model coverage for all data structures  
- **Architecture**: Vertical slice organization by business capability
- **Testing**: Comprehensive test suite with 90%+ coverage
- **Rich UI**: Properly typed Rich components with test compatibility

### Success Criteria

- [ ] Zero mypy type errors across entire codebase
- [ ] Zero ruff linting issues  
- [ ] 90%+ test coverage with 100% test pass rate
- [ ] All secrets moved to environment variables
- [ ] Pydantic v2 models for all data validation
- [ ] Vertical slice architecture implemented
- [ ] Rich UI fully compatible with testing framework
- [ ] Complete documentation with setup/maintenance guides

## All Needed Context

### Documentation & References

```yaml
# MUST READ - Include these in your context window
- file: /Users/nathanhart/PRPs-agentic-eng/.claude/commands/code-quality/review-general.md
  why: Comprehensive code quality standards and review process used to identify issues

- file: /Users/nathanhart/PRPs-agentic-eng/.claude/commands/code-quality/refactor-simple.md  
  why: Refactoring patterns for vertical slice boundaries and single responsibility

- file: /Users/nathanhart/auto-sbm/PRPs/code_reviews/cli.py review.md
  why: Detailed analysis of current issues including 47 mypy errors and Rich UI problems

- file: /Users/nathanhart/auto-sbm/PRPs/code_reviews/config.py-review.md
  why: Critical security issues with hardcoded tokens and lack of Pydantic validation

- file: /Users/nathanhart/auto-sbm/PRPs/code_reviews/processor.py-review.md
  why: SCSS processor type safety issues and architectural improvements needed

- file: /Users/nathanhart/auto-sbm/CLAUDE.md
  why: Current project setup, dependencies, and architectural context

- url: https://docs.pydantic.dev/latest/concepts/models/
  why: Pydantic v2 model patterns for comprehensive type safety

- url: https://docs.pydantic.dev/latest/concepts/validators/
  why: field_validator patterns for configuration and data validation

- url: https://pydantic-settings.helpmanual.io/
  why: Environment-based configuration with BaseSettings for security

- url: https://rich.readthedocs.io/en/latest/
  why: Rich UI integration patterns and testing approaches
```

### Current Codebase Tree

```bash
auto-sbm/
├── sbm/
│   ├── cli.py                 # 750+ lines, Rich UI integration issues
│   ├── config.py              # Basic JSON config, security vulnerabilities  
│   ├── core/
│   │   ├── git.py            # Type annotation issues with config variables
│   │   ├── migration.py      # Core migration logic
│   │   ├── maps.py           # Theme mapping functionality
│   │   └── validation.py     # Validation utilities
│   ├── scss/
│   │   ├── processor.py      # 300+ lines, type hint issues
│   │   ├── mixin_parser.py   # SCSS mixin processing
│   │   └── validator.py      # SCSS validation
│   ├── ui/                   # Rich UI components with type issues
│   │   ├── console.py
│   │   ├── panels.py
│   │   ├── progress.py
│   │   └── prompts.py
│   ├── oem/                  # OEM-specific handlers
│   └── utils/                # Shared utilities
├── tests/                    # 31/55 tests failing
├── config.json              # SECURITY ISSUE: Contains hardcoded tokens
├── requirements.txt
└── CLAUDE.md
```

### Desired Codebase Tree (Vertical Slice Architecture)

```bash
auto-sbm/
├── src/
│   ├── auto_sbm/
│   │   ├── __init__.py
│   │   ├── main.py                    # Minimal CLI entry point
│   │   ├── config.py                  # Pydantic Settings with env validation
│   │   ├── models/                    # Shared Pydantic models
│   │   │   ├── __init__.py
│   │   │   ├── theme.py              # Theme data models
│   │   │   ├── migration.py          # Migration state models  
│   │   │   ├── scss.py               # SCSS processing models
│   │   │   └── tests/
│   │   │       └── test_models.py
│   │   │
│   │   ├── features/                  # Vertical slices by capability
│   │   │   ├── migration/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── service.py        # Migration orchestration
│   │   │   │   ├── models.py         # Migration-specific models
│   │   │   │   ├── cli.py            # Migration CLI commands
│   │   │   │   └── tests/
│   │   │   │       ├── test_service.py
│   │   │   │       └── test_cli.py
│   │   │   │
│   │   │   ├── scss_processing/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── processor.py      # Core SCSS transformation
│   │   │   │   ├── mixin_parser.py   # Mixin parsing logic
│   │   │   │   ├── validator.py      # SCSS validation
│   │   │   │   ├── models.py         # SCSS-specific models
│   │   │   │   └── tests/
│   │   │   │       ├── test_processor.py
│   │   │   │       └── test_validator.py
│   │   │   │
│   │   │   ├── git_operations/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── service.py        # Git operations
│   │   │   │   ├── models.py         # Git state models
│   │   │   │   └── tests/
│   │   │   │       └── test_service.py
│   │   │   │
│   │   │   └── oem_handling/
│   │   │       ├── __init__.py
│   │   │       ├── service.py        # OEM-specific logic
│   │   │       ├── models.py         # OEM models
│   │   │       └── tests/
│   │   │           └── test_service.py
│   │   │
│   │   ├── shared/                    # Cross-cutting concerns
│   │   │   ├── ui/                   # Rich UI components
│   │   │   │   ├── __init__.py
│   │   │   │   ├── console.py        # Console management
│   │   │   │   ├── progress.py       # Progress tracking
│   │   │   │   ├── panels.py         # Status panels
│   │   │   │   ├── models.py         # UI state models
│   │   │   │   └── tests/
│   │   │   │       └── test_ui.py
│   │   │   │
│   │   │   ├── validation/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── service.py        # Validation utilities
│   │   │   │   └── tests/
│   │   │   │       └── test_validation.py
│   │   │   │
│   │   │   └── utils/
│   │   │       ├── __init__.py  
│   │   │       ├── file_operations.py
│   │   │       └── tests/
│   │   │           └── test_utils.py
│   │   │
│   │   └── tests/
│   │       ├── conftest.py           # Shared test fixtures
│   │       └── integration/          # End-to-end tests
│   │           ├── test_full_migration.py
│   │           └── test_cli_integration.py
│   │
├── .env.example                      # Environment template
├── pyproject.toml                    # Modern Python packaging
├── README.md
└── CLAUDE.md                         # Updated documentation
```

### Known Gotchas & Library Quirks

```python
# CRITICAL: Rich UI requires special testing patterns
# Rich objects don't stringify content directly - use .renderable or render()
# TaskID from Rich Progress is not compatible with integer operations

# CRITICAL: Pydantic v2 syntax changes from v1
# Use ConfigDict not class Config
# Use field_validator not @validator  
# Use model_dump() not dict()
# Use Annotated types for complex validation

# CRITICAL: Environment variables in tests
# Use monkeypatch.setenv() for environment variable testing
# Set ALLOW_MODEL_REQUESTS=False to prevent real API calls in tests

# CRITICAL: SCSS processing complexity
# SCSS variable conversion requires context awareness (mixins vs CSS properties)
# Temporary file handling needs proper cleanup with pathlib
# Cross-platform path handling essential for Windows compatibility

# CRITICAL: Git operations  
# Configuration variables can be float | list[Any] | str | None
# Need proper type guards before operations like .append()
# Git hooks and repository state must be validated before operations

# CRITICAL: Click CLI with Rich
# Rich console integration with Click requires careful stdout handling
# Progress bars need proper task management with typed IDs
# CI/CD environments need fallback to plain text output
```

## Implementation Blueprint

### Data Models and Structure

```python
# Core Pydantic models for type safety across the application

# src/auto_sbm/models/theme.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from pathlib import Path
from enum import Enum

class ThemeType(str, Enum):
    LEGACY = "legacy"
    SITE_BUILDER = "site_builder"

class ThemeStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class Theme(BaseModel):
    """Core theme data model with validation"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    name: str = Field(..., min_length=1, max_length=100)
    type: ThemeType
    source_path: Path
    destination_path: Optional[Path] = None
    status: ThemeStatus = ThemeStatus.PENDING
    scss_files: List[Path] = Field(default_factory=list)
    oem_specific: Dict[str, Any] = Field(default_factory=dict)

# src/auto_sbm/models/migration.py  
class MigrationConfig(BaseModel):
    """Migration configuration with validation"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    theme: Theme
    backup_enabled: bool = True
    validation_enabled: bool = True
    rich_ui_enabled: bool = True
    max_concurrent_files: int = Field(default=10, ge=1, le=50)

class MigrationResult(BaseModel):
    """Migration operation result"""
    success: bool
    theme_name: str
    files_processed: int = 0
    files_failed: int = 0
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

# src/auto_sbm/models/scss.py
class ScssVariable(BaseModel):
    """SCSS variable with context information"""
    name: str
    value: str
    context: str  # 'mixin', 'map', 'property', 'global'
    line_number: int
    
class ScssProcessingResult(BaseModel):
    """Result of SCSS file processing"""
    success: bool
    original_content: str
    processed_content: str
    variables_converted: List[ScssVariable] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
```

### Task List (in order of completion)

```yaml
Task 1: Project Structure & Configuration
CREATE pyproject.toml:
  - MIGRATE from setup.py to modern packaging
  - ADD development dependencies (ruff, mypy, pytest)
  - CONFIGURE tool sections for linting and type checking

CREATE src/auto_sbm/config.py:
  - IMPLEMENT Pydantic BaseSettings for environment-based configuration
  - REMOVE hardcoded secrets from config.json
  - ADD validation for all configuration values
  - PATTERN: Use pydantic-settings for secure configuration

MODIFY .gitignore:
  - ADD .env to ignored files
  - ADD mypy and ruff cache directories

CREATE .env.example:
  - PROVIDE template for environment variables
  - DOCUMENT all required configuration options

Task 2: Core Models Implementation  
CREATE src/auto_sbm/models/ structure:
  - IMPLEMENT theme.py with Theme and ThemeType models
  - IMPLEMENT migration.py with MigrationConfig and MigrationResult
  - IMPLEMENT scss.py with ScssVariable and processing models
  - ADD comprehensive field validation and type safety

CREATE model tests:
  - IMPLEMENT test_models.py for each model module
  - TEST validation scenarios and edge cases
  - ENSURE 100% model test coverage

Task 3: Migration Feature Slice
CREATE src/auto_sbm/features/migration/:
  - MOVE migration logic from current sbm/core/migration.py
  - IMPLEMENT service.py with proper Pydantic model usage
  - CREATE models.py for migration-specific data structures
  - IMPLEMENT cli.py for migration-related commands
  - ADD comprehensive tests with mocked dependencies

Task 4: SCSS Processing Feature Slice  
CREATE src/auto_sbm/features/scss_processing/:
  - REFACTOR current sbm/scss/processor.py (fix 300+ line file)
  - MOVE mixin_parser.py and validator.py with type improvements
  - IMPLEMENT proper Pydantic models for SCSS data structures
  - FIX type annotation issues identified in code review
  - ADD comprehensive test coverage for edge cases

Task 5: Git Operations Feature Slice
CREATE src/auto_sbm/features/git_operations/:
  - REFACTOR sbm/core/git.py fixing type annotation issues
  - ADD proper type guards for configuration variables
  - IMPLEMENT service.py with proper error handling
  - CREATE models.py for git operation state
  - FIX issues with float | list[Any] | str | None configuration

Task 6: Rich UI Shared Component
CREATE src/auto_sbm/shared/ui/:
  - REFACTOR current sbm/ui/ components with proper typing
  - FIX Rich UI test compatibility issues
  - IMPLEMENT proper TaskID handling in progress.py
  - CREATE ui-specific Pydantic models for state management
  - ADD CI/CD fallback for non-interactive environments

Task 7: OEM Handling Feature Slice
CREATE src/auto_sbm/features/oem_handling/:
  - MOVE current sbm/oem/ logic to new structure
  - IMPLEMENT proper Pydantic models for OEM data
  - ADD service layer with type safety
  - CREATE comprehensive tests for OEM-specific logic

Task 8: CLI Refactor and Integration
CREATE src/auto_sbm/main.py:
  - IMPLEMENT minimal CLI entry point using Click
  - INTEGRATE all feature slices through service layers
  - FIX function redefinition issues (test_compilation)
  - REMOVE code duplication and dead code
  - ENSURE Rich UI integration works with Click

Task 9: Testing Infrastructure  
CREATE comprehensive test suite:
  - IMPLEMENT conftest.py with shared fixtures
  - CREATE integration tests for end-to-end workflows
  - FIX 31 failing tests from Rich UI integration
  - ACHIEVE 90%+ test coverage across all modules
  - ADD performance benchmarks for large theme migrations

Task 10: Security and Validation
IMPLEMENT security improvements:
  - REMOVE all hardcoded secrets from configuration
  - ADD environment variable validation
  - IMPLEMENT secure file handling patterns
  - ADD input validation for all user-provided data
  - CREATE security-focused integration tests
```

### Pseudocode for Core Components

```python
# Core Configuration with Security
# src/auto_sbm/config.py
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from pathlib import Path
from typing import Optional

class AutoSBMSettings(BaseSettings):
    """Secure configuration management with environment variables"""
    
    # GitHub integration (NO HARDCODED TOKENS)
    github_token: str = Field(..., description="GitHub personal access token")
    github_org: str = Field(default="dealrinspire", description="GitHub organization")
    
    # File system paths  
    themes_directory: Path = Field(default=Path("themes"), description="Themes directory")
    backup_directory: Path = Field(default=Path("backups"), description="Backup directory")
    
    # Processing configuration
    max_concurrent_files: int = Field(default=10, ge=1, le=50)
    rich_ui_enabled: bool = Field(default=True, description="Enable Rich UI")
    backup_enabled: bool = Field(default=True, description="Enable backups")
    
    # Validation
    @field_validator('themes_directory', 'backup_directory')
    def validate_directories_exist(cls, v):
        """Ensure directories exist or can be created"""
        if not v.exists():
            v.mkdir(parents=True, exist_ok=True)
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Migration Service with Proper Type Safety
# src/auto_sbm/features/migration/service.py
from auto_sbm.models.migration import MigrationConfig, MigrationResult
from auto_sbm.models.theme import Theme
from auto_sbm.shared.ui.progress import ProgressTracker
from typing import AsyncGenerator

class MigrationService:
    """Core migration orchestration with type safety"""
    
    def __init__(self, config: AutoSBMSettings, ui_tracker: ProgressTracker):
        self.config = config
        self.ui_tracker = ui_tracker
    
    async def migrate_theme(self, migration_config: MigrationConfig) -> MigrationResult:
        """Migrate a theme with comprehensive validation and progress tracking"""
        
        # Validate input using Pydantic models
        if not migration_config.theme.source_path.exists():
            return MigrationResult(
                success=False,
                theme_name=migration_config.theme.name,
                errors=["Source path does not exist"]
            )
        
        # Initialize progress tracking
        task_id = await self.ui_tracker.start_migration(migration_config.theme.name)
        
        try:
            # Process SCSS files with proper error handling
            scss_results = await self._process_scss_files(
                migration_config.theme.scss_files,
                task_id
            )
            
            # Validate results using Pydantic models
            migration_result = MigrationResult(
                success=all(result.success for result in scss_results),
                theme_name=migration_config.theme.name,
                files_processed=len(scss_results),
                files_failed=sum(1 for r in scss_results if not r.success)
            )
            
            await self.ui_tracker.complete_migration(task_id, migration_result.success)
            return migration_result
            
        except Exception as e:
            await self.ui_tracker.fail_migration(task_id, str(e))
            return MigrationResult(
                success=False,
                theme_name=migration_config.theme.name,
                errors=[str(e)]
            )

# SCSS Processing with Fixed Type Issues  
# src/auto_sbm/features/scss_processing/processor.py
from auto_sbm.models.scss import ScssVariable, ScssProcessingResult
from typing import List, Tuple, Union
import re

class ScssProcessor:
    """SCSS processing with proper type safety and validation"""
    
    def process_file(self, content: str) -> ScssProcessingResult:
        """Process SCSS content with comprehensive error handling"""
        
        try:
            # Extract variables with proper typing
            variables = self._extract_variables(content)
            
            # Convert variables intelligently
            processed_content = self._convert_variables(content, variables)
            
            # Validate syntax
            is_valid, error_message = self._validate_scss_syntax(processed_content)
            
            return ScssProcessingResult(
                success=is_valid,
                original_content=content,
                processed_content=processed_content,
                variables_converted=variables,
                errors=[error_message] if error_message else []
            )
            
        except Exception as e:
            return ScssProcessingResult(
                success=False,
                original_content=content,
                processed_content=content,
                errors=[f"Processing failed: {str(e)}"]
            )
    
    def _validate_scss_syntax(self, content: str) -> Tuple[bool, Optional[str]]:
        """Validate SCSS syntax with proper return type annotation"""
        # Implementation with proper error handling
        pass

# Rich UI with Proper Type Safety
# src/auto_sbm/shared/ui/progress.py  
from rich.progress import Progress, TaskID
from auto_sbm.models.migration import MigrationResult
from typing import Optional

class ProgressTracker:
    """Rich UI progress tracking with proper type safety"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.progress: Optional[Progress] = None
        if enabled:
            self.progress = Progress()
    
    async def start_migration(self, theme_name: str) -> Optional[TaskID]:
        """Start migration tracking with proper TaskID typing"""
        if not self.enabled or not self.progress:
            return None
            
        task_id = self.progress.add_task(
            f"Migrating {theme_name}",
            total=100
        )
        return task_id
    
    async def update_progress(self, task_id: Optional[TaskID], progress: int) -> None:
        """Update progress with type-safe TaskID handling"""
        if not self.enabled or not self.progress or task_id is None:
            return
            
        self.progress.update(task_id, completed=progress)
```

### Integration Points

```yaml
CONFIGURATION:
  - migrate from: config.json (with hardcoded secrets)
  - migrate to: .env + Pydantic BaseSettings
  - pattern: Use environment variables for all sensitive data

PACKAGING:
  - migrate from: setup.py + requirements.txt
  - migrate to: pyproject.toml with modern packaging
  - tools: ruff, mypy, pytest configuration in pyproject.toml

CLI_INTEGRATION:
  - migrate from: monolithic sbm/cli.py (750+ lines)  
  - migrate to: feature-based CLI with Click and Rich
  - pattern: Thin CLI layer calling service methods

RICH_UI:
  - fix: TaskID type compatibility issues
  - fix: Test assertion problems with Rich objects
  - pattern: Proper Rich object testing with .renderable access

TESTING:
  - migrate from: root-level tests/ with 43% pass rate
  - migrate to: co-located tests/ with comprehensive coverage
  - target: 90%+ coverage with 100% pass rate
```

## Validation Loop

### Level 1: Syntax & Style (Fix Current Issues)

```bash
# Fix critical type issues first
source .venv/bin/activate && mypy src/auto_sbm/ --install-types --non-interactive

# Fix linting issues  
source .venv/bin/activate && ruff check src/auto_sbm/ --fix

# Format code consistently
source .venv/bin/activate && ruff format src/auto_sbm/

# Expected: Zero errors. Current state: 47 mypy + 56 ruff issues to resolve
```

### Level 2: Security Validation

```bash
# Remove hardcoded secrets
grep -r "gho_" src/ && echo "❌ Found hardcoded tokens" || echo "✅ No hardcoded secrets"

# Validate environment configuration
source .venv/bin/activate && python -c "
from auto_sbm.config import AutoSBMSettings
settings = AutoSBMSettings()
print('✅ Configuration validation passed')
"

# Test security with missing environment variables
GITHUB_TOKEN= source .venv/bin/activate && python -c "
from auto_sbm.config import AutoSBMSettings
try:
    settings = AutoSBMSettings()
    print('❌ Should have failed without GITHUB_TOKEN')
except Exception as e:
    print('✅ Properly validates required environment variables')
"
```

### Level 3: Feature Testing

```python
# Test each feature slice independently
def test_migration_service():
    """Test migration service with proper mocking"""
    from auto_sbm.features.migration.service import MigrationService
    from auto_sbm.models.migration import MigrationConfig
    
    # Test with valid configuration
    config = MigrationConfig(...)
    result = await migration_service.migrate_theme(config)
    assert result.success is True

def test_scss_processor():
    """Test SCSS processing with edge cases"""
    from auto_sbm.features.scss_processing.processor import ScssProcessor
    
    processor = ScssProcessor()
    result = processor.process_file("$primary-color: #007bff;")
    assert result.success is True
    assert len(result.variables_converted) == 1

def test_rich_ui_integration():
    """Test Rich UI components properly"""
    from auto_sbm.shared.ui.progress import ProgressTracker
    
    tracker = ProgressTracker(enabled=True)
    task_id = await tracker.start_migration("test-theme")
    assert task_id is not None
    
    # Test fallback for CI environments
    tracker_ci = ProgressTracker(enabled=False)
    task_id_ci = await tracker_ci.start_migration("test-theme")
    assert task_id_ci is None
```

```bash
# Run tests with coverage tracking
source .venv/bin/activate && pytest src/ --cov=auto_sbm --cov-report=term-missing

# Target: 90%+ coverage, 100% pass rate
# Current: 31/55 tests failing, 18% file coverage
```

### Level 4: Integration Testing

```bash
# Test complete migration workflow
source .venv/bin/activate && python -c "
import asyncio
from auto_sbm.main import migrate_theme_command
from auto_sbm.config import AutoSBMSettings

async def test_integration():
    settings = AutoSBMSettings()
    result = await migrate_theme_command('test-theme')
    assert result.success is True
    print('✅ Integration test passed')

asyncio.run(test_integration())
"

# Test CLI integration
source .venv/bin/activate && python -m auto_sbm migrate test-theme --dry-run

# Test Rich UI in various environments
TERM=dumb python -m auto_sbm migrate test-theme --dry-run  # CI environment test
```

### Level 5: Performance & Production Readiness

```bash
# Memory usage testing for large themes
source .venv/bin/activate && python -c "
import tracemalloc
from auto_sbm.features.migration.service import MigrationService

tracemalloc.start()
# Test with large theme
current, peak = tracemalloc.get_traced_memory()
print(f'Memory usage: {peak / 1024 / 1024:.1f} MB peak')
tracemalloc.stop()
"

# Performance benchmarking
source .venv/bin/activate && python -c "
import time
from auto_sbm.features.scss_processing.processor import ScssProcessor

start = time.time()
processor = ScssProcessor()
# Process sample files
end = time.time()
print(f'Processing time: {end - start:.2f}s')
"

# Security audit
source .venv/bin/activate && python -c "
import os
from auto_sbm.config import AutoSBMSettings

# Verify no environment bleeding
settings = AutoSBMSettings()
assert 'gho_' not in str(settings.model_dump())
print('✅ No secret values in configuration dump')
"
```

## Final Validation Checklist

- [ ] **Type Safety**: Zero mypy errors (currently 47 errors)
- [ ] **Code Quality**: Zero ruff linting issues (currently 56 issues)  
- [ ] **Security**: All secrets moved to environment variables
- [ ] **Architecture**: Vertical slice structure implemented
- [ ] **Testing**: 90%+ coverage with 100% pass rate (currently 43% pass rate)
- [ ] **Rich UI**: Proper type compatibility and testing support
- [ ] **Performance**: Memory usage stable for large themes
- [ ] **Documentation**: Complete setup and maintenance guides
- [ ] **CLI**: Feature-complete with proper error handling
- [ ] **Integration**: End-to-end migration workflows tested

## Success Metrics & Timeline

### Phase 1 (Foundation) - Week 1
- [ ] Project structure and configuration complete
- [ ] Core Pydantic models implemented and tested
- [ ] Security vulnerabilities resolved (environment-based config)

### Phase 2 (Core Features) - Week 2  
- [ ] Migration and SCSS processing feature slices complete
- [ ] Git operations refactored with proper type safety
- [ ] Rich UI components properly typed and tested

### Phase 3 (Integration) - Week 3
- [ ] All feature slices integrated through main CLI
- [ ] Comprehensive test suite with 90%+ coverage
- [ ] Performance optimization and security validation

### Phase 4 (Validation) - Week 4
- [ ] Full integration testing with real-world themes
- [ ] Documentation and maintenance guides complete
- [ ] Production deployment validation

**Expected Outcome**: Transform auto-SBM from a maintenance-heavy tool with significant technical debt into a production-ready, type-safe, secure application following modern Python best practices.

---

## Anti-Patterns to Avoid

- ❌ **Don't migrate everything at once** - Use incremental refactoring with validation at each step
- ❌ **Don't ignore the failing tests** - Fix Rich UI test compatibility issues properly  
- ❌ **Don't hardcode any configuration** - Use environment variables for all external dependencies
- ❌ **Don't create circular imports** - Maintain clear dependency directions in vertical slices
- ❌ **Don't skip type annotations** - Every function and method must have complete type hints
- ❌ **Don't ignore security** - Validate all inputs and handle secrets properly
- ❌ **Don't create monolithic files** - Keep files under 500 lines and functions under 50 lines
- ❌ **Don't break existing CLI behavior** - Maintain backward compatibility for existing commands

## Time Efficiency Benefits

This comprehensive refactor provides:

- **10x maintainability improvement**: Type safety prevents runtime errors
- **Security hardening**: Eliminates hardcoded token vulnerabilities  
- **90%+ test reliability**: Proper test architecture prevents regression
- **Developer velocity**: Clear architecture enables faster feature development
- **Production confidence**: Comprehensive validation ensures deployment safety

**Expected ROI**: 50+ hours saved per quarter through reduced debugging, faster feature development, and improved reliability.
