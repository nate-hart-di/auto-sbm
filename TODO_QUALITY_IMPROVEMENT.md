# Auto-SBM Quality Improvement Implementation Plan

## Overview
Transform the auto-sbm codebase from functional prototype to production-grade software by systematically addressing 936 code quality issues across 4 phases.

**Current State**: 936 ruff errors, 469 type issues, ~39% test coverage  
**Target State**: <100 ruff errors, 0 MyPy errors, >80% test coverage

## Phase 1: Critical Infrastructure (8 hours)

### Task 1.1 - Environment Setup & Dependencies (2 hours)
**Priority**: CRITICAL - Must complete first

#### Subtasks:
- [ ] **Fix pyproject.toml duplicate classifier**
  - Location: `/Users/nathanhart/auto-sbm/pyproject.toml`
  - Action: Remove duplicate `"Programming Language :: Python :: 3.9"` classifier (line 23)
  - Validation: `ruff check pyproject.toml`

- [ ] **Update Python target version**
  - Location: `pyproject.toml` line 82
  - Action: Change `target-version = "py38"` to `target-version = "py39"`
  - Validation: `ruff --version && ruff check . --target-version py39`

- [ ] **Add missing development dependencies**
  - Location: `pyproject.toml` [tool.uv.dev-dependencies] section
  - Action: Add `types-requests>=2.28.0`, `types-PyYAML>=6.0`
  - Validation: `uv sync --dev` or `pip install types-requests types-PyYAML`

- [ ] **Install core quality tools**
  - Commands:
    ```bash
    pip install pydantic pydantic-settings mypy
    python -c "import pydantic, mypy, pytest; print('Environment OK')"
    ```
  - Expected: Clean imports, no errors

### Task 1.2 - Python 3.10+ Compatibility (4 hours)
**Priority**: HIGH - Prevents type checking

#### Subtasks:
- [ ] **Fix union syntax in helpers.py**
  - Location: `/Users/nathanhart/auto-sbm/sbm/utils/helpers.py` line 87
  - Action: Replace `X | Y` syntax with `Union[X, Y]`
  - Add import: `from typing import Union, Optional`
  - Validation: `python -m py_compile sbm/utils/helpers.py`

- [ ] **Audit all files for modern union syntax**
  - Command: `grep -r " | " sbm/ --include="*.py"`
  - Action: Replace all `X | Y` with `Union[X, Y]`
  - Files likely affected: `sbm/config.py`, `sbm/core/migration.py`

- [ ] **Verify Pydantic v2 compatibility**
  - Location: `/Users/nathanhart/auto-sbm/sbm/config.py`
  - Action: Ensure `field_validator` decorators work
  - Test: `python -c "from sbm.config import Config; print('OK')"`

### Task 1.3 - Import Organization (2 hours)
**Priority**: MEDIUM - Affects 71 PLC0415 violations

#### Subtasks:
- [ ] **Fix local imports in CLI**
  - Location: `/Users/nathanhart/auto-sbm/sbm/cli.py`
  - Target lines: 566, 641-644
  - Action: Move all function-level imports to module top
  - Pattern:
    ```python
    # Move from inside functions to top of file
    import subprocess
    from datetime import datetime
    ```

- [ ] **Clean unused imports**
  - Command: `ruff check sbm/ --select F401`
  - Action: Remove all unused imports flagged
  - Auto-fix: `ruff check sbm/ --select F401 --fix`

- [ ] **Validate import organization**
  - Command: `ruff check sbm/ --select PLC0415`
  - Expected: 0 violations after fixes

**Phase 1 Validation Gate:**
```bash
# All commands must pass
python -c "import pydantic, mypy, pytest; print('Environment OK')"
ruff check sbm/ --statistics | grep "Fixed"
mypy sbm/ | head -10  # Should show progress, not crash
```

## Phase 2: Core Quality & Type Safety (22 hours)

### Task 2.1 - Type Annotations Implementation (16 hours)
**Priority**: HIGH - Core infrastructure first

#### Subtask 2.1.1 - Utilities & Helpers (4 hours)
- [ ] **sbm/utils/helpers.py - Infrastructure functions**
  - Target: 76 ANN201 (missing return types)
  - Pattern:
    ```python
    def get_branch_name(theme_name: str) -> str:
        """Generate standardized branch name for theme."""
    ```
  - Priority functions: `get_branch_name`, `validate_theme_name`, `sanitize_path`
  - Validation: `mypy sbm/utils/helpers.py`

#### Subtask 2.1.2 - Core Migration Logic (6 hours)
- [ ] **sbm/core/migration.py - Main business logic**
  - Target: 305 ANN001 (missing parameter types)
  - Critical functions: `migrate_dealer_theme`, `process_scss_files`
  - Pattern:
    ```python
    def migrate_dealer_theme(theme_name: str, config: Config) -> MigrationResult:
        """Execute complete theme migration workflow."""
    ```
  - Validation: `mypy sbm/core/migration.py`

#### Subtask 2.1.3 - SCSS Processing (4 hours)
- [ ] **sbm/scss/processor.py - Transformation engine**
  - Target: 88 ANN202 (missing private function types)
  - Focus: `SCSSProcessor` class methods
  - Pattern:
    ```python
    def _process_mixins(self, content: str) -> tuple[str, list[str]]:
        """Process SCSS mixins and return transformed content."""
    ```
  - Validation: `mypy sbm/scss/processor.py`

#### Subtask 2.1.4 - Configuration & Models (2 hours)
- [ ] **sbm/config.py - Settings and validation**
  - Implement Pydantic v2 models
  - Target: Complete type safety for configuration
  - Pattern:
    ```python
    from pydantic import BaseModel, Field, field_validator

    class MigrationSettings(BaseModel):
        cleanup_snapshots: bool = Field(default=True)
        create_backups: bool = Field(default=True)
        max_concurrent_files: int = Field(default=10, ge=1, le=50)
    ```
  - Validation: `mypy sbm/config.py --strict`

### Task 2.2 - Print Statement Migration (4 hours)
**Priority**: HIGH - Affects debugging and production logs

#### Subtasks:
- [ ] **Replace CLI print statements**
  - Location: `/Users/nathanhart/auto-sbm/sbm/cli.py`
  - Target: ~40 print statements
  - Pattern:
    ```python
    # OLD: print(f"Processing {theme_name}")
    # NEW: logger.info("Processing %s", theme_name)
    ```
  - Preserve: Print statements in interactive prompts

- [ ] **Replace core logic prints**
  - Locations: `sbm/core/migration.py`, `sbm/scss/processor.py`
  - Target: ~60 print statements
  - Focus: Error messages, progress updates
  - Validation: `ruff check sbm/ --select T201`

- [ ] **Configure Rich logging integration**
  - Location: `/Users/nathanhart/auto-sbm/sbm/utils/logger.py`
  - Action: Ensure logger works with Rich UI
  - Test: Print statements only in setup scripts and tests

### Task 2.3 - Code Formatting & Style (2 hours)
**Priority**: MEDIUM - Improves readability

#### Subtasks:
- [ ] **Auto-fix whitespace issues**
  - Command: `ruff check . --fix --select W`
  - Expected: Fix ~61 whitespace violations automatically

- [ ] **Fix line length violations**
  - Target: 104 E501 violations
  - Command: `ruff check . --select E501`
  - Pattern: Break lines at logical points (commas, operators)
  - Max length: 100 characters

- [ ] **Format code consistently**
  - Command: `ruff format .`
  - Review: Ensure no functional changes

**Phase 2 Validation Gate:**
```bash
# Progress targets
ruff check sbm/ --statistics  # Should show <400 errors
mypy sbm/ | wc -l            # Should show <100 errors
pytest tests/ --cov=sbm     # Should show >50% coverage
```

## Phase 3: Test Coverage Implementation (28 hours)

### Task 3.1 - Core Logic Testing (12 hours)
**Priority**: CRITICAL - Business logic must be tested

#### Subtask 3.1.1 - Migration Workflow Tests (4 hours)
- [ ] **Create tests/test_core/test_migration_workflow.py**
  - Location: `/Users/nathanhart/auto-sbm/tests/test_core/test_migration_workflow.py`
  - Coverage: End-to-end migration process
  - Pattern:
    ```python
    def test_migrate_dealer_theme_success(mock_theme, mock_config):
        """Test successful theme migration workflow."""
        result = migrate_dealer_theme("test-theme", mock_config)
        assert result.success is True
        assert result.files_created > 0
    ```
  - Validation: `pytest tests/test_core/test_migration_workflow.py -v`

#### Subtask 3.1.2 - SCSS Processor Tests (4 hours)
- [ ] **Create tests/test_core/test_scss_processor.py**
  - Location: `/Users/nathanhart/auto-sbm/tests/test_core/test_scss_processor.py`
  - Coverage: SCSS transformation logic
  - Focus: Mixin parsing, variable handling
  - Pattern:
    ```python
    def test_process_scss_mixins():
        """Test SCSS mixin transformation."""
        processor = SCSSProcessor()
        result = processor.process_mixins(scss_content)
        assert "@mixin" not in result
        assert "custom-property" in result
    ```

#### Subtask 3.1.3 - Git Operations Tests (4 hours)
- [ ] **Create tests/test_core/test_git_operations.py**
  - Location: `/Users/nathanhart/auto-sbm/tests/test_core/test_git_operations.py`
  - Coverage: Branch creation, commits, PR creation
  - Use: Git fixtures and temporary repos
  - Validation: `pytest tests/test_core/test_git_operations.py -v`

### Task 3.2 - UI Component Testing (8 hours)
**Priority**: MEDIUM - Fix existing Rich UI test issues

#### Subtasks:
- [ ] **Fix MockStat object issues**
  - Location: `/Users/nathanhart/auto-sbm/tests/test_ui/`
  - Problem: Rich UI tests failing with mock objects
  - Solution: Use pytest fixtures for Rich console capture
  - Pattern:
    ```python
    @pytest.fixture
    def rich_console():
        """Provide Rich console for testing output."""
        from rich.console import Console
        from io import StringIO
        
        string_io = StringIO()
        return Console(file=string_io, force_terminal=True)
    ```

- [ ] **Enhance progress tracking tests**
  - Location: `/Users/nathanhart/auto-sbm/tests/test_ui/test_progress.py`
  - Focus: Progress bar updates, step completion
  - Use: Console capture without mocking internals

- [ ] **Test status panel components**
  - Location: `/Users/nathanhart/auto-sbm/tests/test_ui/test_panels.py`
  - Coverage: Migration status, error displays
  - Pattern: Test rendered output content

### Task 3.3 - Integration Testing (8 hours)
**Priority**: HIGH - Validates complete workflows

#### Subtasks:
- [ ] **Create tests/integration/test_full_workflow.py**
  - Location: `/Users/nathanhart/auto-sbm/tests/integration/test_full_workflow.py`
  - Coverage: Complete CLI to file output workflow
  - Use: Temporary theme directories
  - Validation: Actual file creation and Git operations

- [ ] **Create tests/integration/test_cli_integration.py**
  - Location: `/Users/nathanhart/auto-sbm/tests/integration/test_cli_integration.py`
  - Coverage: CLI commands with real environment
  - Test: `sbm migrate`, `sbm validate` commands

- [ ] **Error recovery scenario tests**
  - Coverage: Failed migrations, rollback procedures
  - Pattern: Inject failures and test recovery

**Phase 3 Validation Gate:**
```bash
pytest tests/ --cov=sbm --cov-report=term-missing --cov-fail-under=80
# Must achieve >80% coverage
ruff check sbm/ --statistics  # Should show <100 errors
mypy sbm/                     # Should pass with zero errors
```

## Phase 4: Documentation & Production Polish (14 hours)

### Task 4.1 - Documentation Alignment (4 hours)
**Priority**: MEDIUM - Prevents developer confusion

#### Subtasks:
- [ ] **Update CLAUDE.md architecture claims**
  - Location: `/Users/nathanhart/auto-sbm/CLAUDE.md`
  - Issues: Claims vertical slice architecture (not implemented)
  - Action: Align with actual horizontal structure
  - Fix: Coverage statistics, dependency claims

- [ ] **Correct project structure documentation**
  - Action: Document actual file organization
  - Remove: References to unimplemented features
  - Add: Accurate setup and usage instructions

### Task 4.2 - Performance Optimization (6 hours)
**Priority**: MEDIUM - Reduces technical debt

#### Subtasks:
- [ ] **Migrate to pathlib usage**
  - Target: 172 PTH violations
  - Pattern:
    ```python
    # OLD: os.path.join(base, filename)
    # NEW: Path(base) / filename
    ```
  - Files: All modules using os.path operations
  - Validation: `ruff check . --select PTH`

- [ ] **Fix logging performance issues**
  - Target: 33 G004 violations
  - Pattern:
    ```python
    # OLD: logger.info(f"Processing {name}")
    # NEW: logger.info("Processing %s", name)
    ```
  - Benefits: Lazy evaluation, better performance

- [ ] **Optimize error handling patterns**
  - Focus: Reduce exception overhead
  - Pattern: Use specific exceptions over generic ones

### Task 4.3 - Security Audit (4 hours)
**Priority**: HIGH - Production security requirements

#### Subtasks:
- [ ] **Review subprocess security issues**
  - Target: 4 S602 violations
  - Pattern: Validate all subprocess calls use shell=False
  - Action: Add input sanitization where needed

- [ ] **Audit hardcoded credentials**
  - Target: 2 S105 violations
  - Action: Move all secrets to environment variables
  - Pattern: Use configuration classes for sensitive data

- [ ] **Validate input sanitization**
  - Focus: Theme names, file paths, user inputs
  - Pattern: Add validation before filesystem operations

**Phase 4 Validation Gate:**
```bash
# Final quality check
ruff check . --statistics                    # Must be <100 errors
mypy sbm/                                    # Must pass with 0 errors
pytest tests/ --cov=sbm --cov-fail-under=80 # Must achieve >80% coverage
bandit -r sbm/                               # Security audit
```

## Validation Loops

### Level 1: Environment & Syntax (Run before any changes)
```bash
python -c "import pydantic, mypy, pytest; print('Environment OK')"
ruff check sbm/ --fix
mypy sbm/
```
**Expected**: Clean environment, no import errors

### Level 2: Incremental Quality Gates (After each task)
```bash
ruff check sbm/ --statistics
mypy sbm/ --report .mypy_cache/
pytest tests/ --cov=sbm --cov-report=term-missing
```
**Success Criteria**:
- Phase 1: Environment setup works, critical imports resolved
- Phase 2: Ruff errors <500, MyPy errors <100, Coverage >50%
- Phase 3: Ruff errors <100, MyPy clean, Coverage >80%

### Level 3: Functional Validation (Integration test)
```bash
cd ~/di-websites-platform
sbm migrate test-theme --skip-post-migration
```
**Expected**: Migration completes without errors, clear logs, proper file generation

### Level 4: Quality Metrics (Comprehensive assessment)
```bash
pytest tests/ -v --cov=sbm --cov-report=html
ruff check . --statistics > quality_metrics.txt
mypy sbm/ --html-report .mypy_cache/html
```
**Review**: Coverage gaps, remaining issues, type safety completeness

## Success Metrics

| Metric | Current | Target | Phase 1 | Phase 2 | Phase 3 |
|--------|---------|--------|---------|---------|---------|
| Ruff Errors | 936 | <100 | <800 | <400 | <100 |
| Type Coverage | ~0% | >90% | >20% | >60% | >90% |
| Test Coverage | ~39% | >80% | >45% | >65% | >80% |
| MyPy Errors | 469+ | 0 | <300 | <100 | 0 |

## Risk Mitigation

- **Breaking Changes**: Small incremental changes with validation
- **Test Failures**: Comprehensive regression testing at each phase
- **Performance Impact**: Benchmark migration times before/after
- **Quality Over Quantity**: Focus coverage on critical business logic

## Final Definition of Done

- [ ] All ruff errors < 100
- [ ] MyPy passes with zero errors
- [ ] Test coverage > 80%
- [ ] All CI/CD checks pass
- [ ] Documentation aligned with reality
- [ ] Security audit completed
- [ ] Performance benchmarks maintained
- [ ] Feature parity maintained throughout process

---

**Next Steps**: Execute Phase 1 tasks in order, validating each completion before proceeding to the next phase.