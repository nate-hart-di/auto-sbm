name: "Auto-SBM Code Quality Improvement Initiative"
description: |

## Purpose

Systematic transformation of auto-sbm from functional prototype to production-grade software through comprehensive code quality improvements, type safety implementation, and test coverage expansion.

## Core Principles

1. **Incremental Progress**: Fix issues in risk-prioritized phases to maintain feature stability
2. **Validation Loops**: Executable quality gates at each step with automated verification
3. **Modern Standards**: Adopt 2024/2025 Python best practices with industry-standard tooling
4. **Maintainability**: Establish sustainable development practices for long-term success

---

## Goal

Transform the auto-sbm codebase to achieve production-grade quality standards:
- **936 ruff linting errors** reduced to <100
- **469 type annotation issues** resolved with comprehensive MyPy compliance
- **Test coverage** increased from ~39% to 80%+
- **Documentation alignment** with actual codebase structure
- **Developer experience** improved with modern tooling and CI/CD integration

## Why

- **Technical Debt Crisis**: 936 quality issues create maintenance burden and deployment risk
- **Type Safety Gap**: Missing type annotations prevent reliable IDE support and early bug detection
- **Testing Inadequacy**: 39% coverage insufficient for production confidence
- **Documentation Drift**: Misleading docs confuse new developers and slow onboarding
- **Competitive Advantage**: Production-grade tool establishes auto-sbm as enterprise-ready solution

## What

A systematic 4-phase quality improvement program using modern Python toolchain:
1. **Critical Infrastructure** (Week 1): Environment setup, compatibility fixes
2. **Core Quality** (Weeks 2-3): Type annotations, linting compliance, logging improvements
3. **Test Coverage** (Weeks 4-5): Comprehensive testing strategy with 80%+ coverage
4. **Production Polish** (Week 6): Documentation alignment, performance optimization, security audit

### Success Criteria

- [ ] Ruff errors: 936 → <100 (89% reduction)
- [ ] MyPy compliance: 0% → 90%+ type coverage
- [ ] Test coverage: 39% → 80%+ with meaningful tests
- [ ] Developer onboarding: Multi-day → 1-day productivity
- [ ] CI/CD reliability: Intermittent → 100% pass rate
- [ ] Documentation accuracy: Outdated → Current and correct

## All Needed Context

### Documentation & References

```yaml
# MUST READ - Include these in your context window
- url: https://docs.astral.sh/ruff/tutorial/
  why: Official Ruff migration guide for large codebases, configuration best practices

- url: https://docs.astral.sh/ruff/linter/
  why: Comprehensive rule reference and per-file configuration patterns

- url: https://mypy.readthedocs.io/en/stable/existing_code.html
  why: Official MyPy gradual typing strategy for legacy codebases

- url: https://realpython.com/ruff-python/
  why: Modern Python linting best practices and migration strategies

- docfile: PRPs/ai_docs/quality_improvement_best_practices.md
  why: Industry research on Ruff/MyPy migration for large codebases, proven strategies

- file: tests/test_ui/test_progress.py
  why: Example of proper Rich UI testing patterns, console capture approach

- file: tests/test_config_migration.py
  why: Comprehensive Pydantic v2 testing patterns, environment variable handling

- file: sbm/config.py
  why: Current Pydantic v2 implementation, field validation patterns to follow
  critical: Uses model_config instead of class Config, field_validator not @validator

- file: pyproject.toml
  why: Current tool configuration, shows what needs updating for quality tools
  gotcha: Target version mismatch (py38 vs py39), duplicate classifiers need fixing
```

### Current Codebase Structure

```bash
auto-sbm/
├── sbm/                    # Main package (31 Python files)
│   ├── cli.py             # 1,313 lines - main CLI interface
│   ├── config.py          # Pydantic v2 configuration system
│   ├── core/              # Business logic (5 files)
│   ├── oem/               # OEM-specific handlers (5 files)  
│   ├── scss/              # SCSS processing engine (5 files)
│   ├── ui/                # Rich UI components (7 files)
│   └── utils/             # Shared utilities (5 files)
├── tests/                 # 12 test files (~39% coverage)
│   ├── test_*.py          # 9 main test files
│   └── test_ui/           # 3 UI-specific tests
├── PRPs/                  # Project documentation
└── pyproject.toml         # Tool configuration (needs updates)
```

### Known Gotchas & Library Quirks

```python
# CRITICAL: Python 3.9 compatibility required
# Current issue: Uses Python 3.10+ union syntax in sbm/utils/helpers.py:87
# Fix: Replace 'X | Y' with 'Union[X, Y]' from typing

# CRITICAL: Pydantic v2 patterns must be followed consistently
# ✅ CORRECT: model_config = SettingsConfigDict(...)
# ❌ WRONG: class Config: ...
# ✅ CORRECT: @field_validator('field_name')
# ❌ WRONG: @validator('field_name')

# CRITICAL: Rich UI testing requires console capture approach
# ✅ CORRECT: Console(file=StringIO(), force_terminal=False)
# ❌ WRONG: Mocking Rich internal objects directly

# CRITICAL: Import organization must follow existing patterns
# Current issue: 71 PLC0415 violations (local imports in functions)
# Pattern: Move all imports to top-level, organize: stdlib, third-party, local

# CRITICAL: Logging performance patterns
# ✅ CORRECT: logger.info("Message %s", variable)  # Lazy evaluation
# ❌ WRONG: logger.info(f"Message {variable}")     # Always evaluated

# CRITICAL: Path operations modernization
# Target: Replace os.path with pathlib.Path (172 PTH violations)
# Pattern: Path(base) / "sub" / "file.txt" instead of os.path.join()
```

## Implementation Blueprint

### Data Models and Structure

Establish type-safe configuration and validation throughout the codebase:

```python
# Pattern: Comprehensive type annotations for all public functions
from typing import Union, Optional, List, Dict, Any
from pathlib import Path

def migrate_styles(theme_name: str, force_reset: bool = False) -> bool:
    """Migrate SCSS styles with full type safety."""
    pass

# Pattern: Pydantic v2 models for complex data structures  
from pydantic import BaseModel, Field, field_validator

class MigrationResult(BaseModel):
    """Results from migration operation."""
    success: bool
    theme_name: str
    files_processed: int
    errors: List[str] = Field(default_factory=list)
    elapsed_seconds: float
    
    @field_validator('theme_name')
    @classmethod
    def validate_theme_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Theme name cannot be empty")
        return v.strip()

# Pattern: Rich UI testing with console capture
from io import StringIO
from rich.console import Console

def test_progress_display():
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=80)
    progress = MigrationProgress()
    progress.progress.console = console  # Override for testing
    
    with progress.progress_context():
        progress.add_migration_task("test-theme")
    
    captured = output.getvalue()
    assert "test-theme" in captured
```

### Task Implementation Plan

```yaml
Phase 1 - Critical Infrastructure (8 hours):
  Task 1.1 - Environment & Dependencies:
    MODIFY pyproject.toml:
      - FIND: 'classifiers = [' section
      - REMOVE: duplicate "Programming Language :: Python :: 3.9" entry (line 23)
      - FIND: target-version = "py38"
      - REPLACE: target-version = "py39"
      - ADD to [project.optional-dependencies.dev]: "types-requests>=2.28.0", "types-PyYAML>=6.0.0"
    
    VERIFY installation:
      - RUN: pip install -e .[dev]
      - TEST: python -c "import pydantic, mypy, pytest, ruff; print('All tools available')"

  Task 1.2 - Python Compatibility Fix:
    MODIFY sbm/utils/helpers.py:
      - FIND: line 87 with "X | Y" syntax  
      - ADD at top: from typing import Union, Optional
      - REPLACE: all "X | Y" with "Union[X, Y]"
      - PRESERVE: existing function signatures and behavior
    
    VERIFY compatibility:
      - RUN: python -c "from sbm.utils.helpers import get_branch_name; print('Import OK')"

  Task 1.3 - Import Organization Cleanup:
    TARGET: Fix 71 PLC0415 local import violations
    MODIFY sbm/cli.py:
      - FIND: functions with local imports (search for "import" inside functions)
      - MOVE: all imports to top-level (after existing imports)
      - REMOVE: unused imports like datetime, timezone
      - PRESERVE: existing functionality
    
    PATTERN for other files:
      - SCAN: ruff check --select=PLC0415 to find violations
      - MOVE: local imports to module level
      - GROUP: stdlib, third-party, local imports with blank lines

Phase 2 - Type Safety & Core Quality (22 hours):
  Task 2.1 - Type Annotations Implementation (16 hours):
    PRIORITY STRATEGY:
      1. Start with utils/ (infrastructure used everywhere)
      2. Then core/ (business logic)
      3. Then scss/ (processing engine)
      4. Finally ui/ (presentation layer)
    
    MODIFY sbm/utils/helpers.py:
      - ADD type annotations to all functions
      - PATTERN: def get_branch_name(theme_name: str) -> str:
      - USE: Union, Optional from typing for Python 3.9 compatibility
      - VERIFY: mypy sbm/utils/helpers.py passes
    
    MODIFY sbm/utils/logger.py:
      - ADD: type annotations following existing patterns
      - PATTERN: def setup_logger(name: Optional[str] = None) -> logging.Logger:
    
    CONTINUE with each module systematically:
      - ALWAYS run mypy after each file
      - FIX any type errors before proceeding
      - DOCUMENT any type: ignore with explanation

  Task 2.2 - Print Statement Migration (4 hours):
    TARGET: Replace 121 T201 print statement violations
    STRATEGY: Keep prints in setup.sh, tests/, remove from production code
    
    MODIFY sbm/cli.py:
      - FIND: print() statements (search for "print(")
      - REPLACE with: logger.info(), logger.debug(), click.echo() as appropriate
      - PATTERN: print(f"Message {var}") → logger.info("Message %s", var)
      - PRESERVE: click.echo() for user-facing CLI output
    
    SCAN and fix other modules:
      - RUN: ruff check --select=T201 to find all violations
      - REPLACE: production prints with appropriate logging
      - KEEP: prints in tests/ and setup scripts

  Task 2.3 - Line Length & Formatting (2 hours):
    TARGET: Fix 104 E501 line length violations
    MODIFY files with violations:
      - RUN: ruff check --select=E501 --fix (auto-fixes simple cases)
      - MANUAL: break complex expressions and long strings
      - PATTERN: Use parentheses for multi-line expressions
      - PRESERVE: readability over strict line limits

Phase 3 - Test Coverage Expansion (28 hours):
  Task 3.1 - Core Business Logic Testing (12 hours):
    CREATE tests/test_core/:
      - test_migration_workflow.py (end-to-end migration testing)
      - test_scss_processor.py (SCSS transformation logic)
      - test_git_operations.py (Git workflow validation)
    
    PATTERN for migration tests:
      ```python
      def test_full_migration_workflow():
          """Test complete theme migration from start to finish."""
          with temp_theme_environment("test-theme") as theme_dir:
              result = migrate_dealer_theme("test-theme", skip_just=True)
              assert result is True
              
              # Verify output files exist
              assert (theme_dir / "sb-inside.scss").exists()
              assert (theme_dir / "sb-vdp.scss").exists()
      ```
    
    COVERAGE TARGET: Core migration functions (sbm/core/migration.py)

  Task 3.2 - UI Component Testing Enhancement (8 hours):
    ENHANCE tests/test_ui/:
      - FIX existing Rich UI test failures
      - PATTERN: Use console capture, not object mocking
      - ADD tests for panels, prompts, console components
    
    PATTERN for Rich testing:
      ```python
      def test_migration_progress_display():
          output = StringIO()
          console = Console(file=output, force_terminal=False, width=80)
          
          progress = MigrationProgress()
          progress.progress.console = console
          
          with progress.progress_context():
              progress.add_migration_task("test-theme")
              progress.complete_step("test-step")
          
          captured = output.getvalue()
          assert "test-theme" in captured
          assert "100%" in captured
      ```

  Task 3.3 - Integration & Error Scenario Testing (8 hours):
    CREATE tests/integration/:
      - test_cli_commands.py (CLI integration testing)
      - test_error_recovery.py (Error handling scenarios)
      - test_theme_variations.py (Different theme types)
    
    PATTERN for CLI testing:
      ```python
      def test_auto_command_integration():
          """Test full auto command workflow."""
          from click.testing import CliRunner
          from sbm.cli import cli
          
          runner = CliRunner()
          with runner.isolated_filesystem():
              result = runner.invoke(cli, ['auto', 'test-theme', '--skip-post-migration'])
              assert result.exit_code == 0
              assert "Migration completed" in result.output
      ```

Phase 4 - Documentation & Production Polish (14 hours):
  Task 4.1 - Documentation Alignment (4 hours):
    MODIFY CLAUDE.md:
      - UPDATE architecture description to match actual sbm/ structure
      - REMOVE references to non-existent src/auto_sbm/ layout
      - CORRECT test coverage claims (39% not 90%+)
      - ALIGN tool versions and configuration with reality
    
    UPDATE README.md:
      - VERIFY installation instructions work
      - UPDATE feature claims to match implementation
      - ADD quality metrics and CI status badges

  Task 4.2 - Pathlib Migration (6 hours):
    TARGET: Fix 172 PTH violations (os.path → pathlib)
    MODIFY sbm/utils/path.py:
      - REPLACE: os.path.join() with Path() / operations
      - REPLACE: os.path.exists() with Path.exists()
      - PATTERN: Path(base) / "sub" / "file.txt"
      - PRESERVE: all existing path resolution logic
    
    CONTINUE with other modules systematically:
      - RUN: ruff check --select=PTH to find violations
      - MODERNIZE: file operations to use pathlib
      - TEST: ensure no path resolution breaks

  Task 4.3 - Security & Performance Audit (4 hours):
    AUDIT subprocess usage:
      - REVIEW: 4 S602 violations for shell injection risks
      - VERIFY: all subprocess calls use list arguments, not shell=True
      - FIX: any hardcoded credential issues (2 S105 violations)
    
    OPTIMIZE logging performance:
      - FIX: 33 G004 violations (f-strings in logging)
      - PATTERN: logger.info("Message %s", var) not logger.info(f"Message {var}")
```

### Integration Points

```yaml
CI/CD Pipeline Enhancement:
  pre-commit hooks:
    - add: .pre-commit-config.yaml with ruff, mypy, pytest
    - verify: pre-commit install && pre-commit run --all-files
  
  GitHub Actions:
    - create: .github/workflows/quality.yml
    - checks: [linting, type-checking, tests, coverage]
    - gates: All checks must pass for merge

pyproject.toml Updates:
  tool.ruff.lint:
    - extend-select: Gradually add rule categories as codebase improves
    - per-file-ignores: Configure test-specific rule exceptions
  
  tool.mypy:
    - strict: true (gradually enable)
    - per-module overrides: Start permissive, increase strictness
  
  tool.pytest.ini_options:
    - cov-fail-under: Start at 50%, increase to 80%
    - markers: Add custom markers for test categories

Development Environment:
  requirements update:
    - add: development tool dependencies
    - pin: versions for reproducible builds
    - separate: dev/test/prod dependency groups
```

## Validation Loop

### Level 1: Environment & Syntax Validation

```bash
# CRITICAL: Run these FIRST before any code changes
# Environment verification
python -c "import pydantic, mypy, pytest, ruff; print('✅ All tools available')"

# Baseline measurement  
ruff check sbm/ --statistics > baseline_errors.txt
mypy sbm/ --report .mypy_cache/baseline/
pytest tests/ --cov=sbm --cov-report=html --cov-report=term

# Expected: Clean tool installation, baseline metrics recorded
```

### Level 2: Incremental Quality Gates

```bash
# After each task completion - run and verify improvement:

# Phase 1 Gates:
ruff check sbm/ --statistics  # Should show error reduction
python -c "from sbm.utils.helpers import get_branch_name; print('✅ Import fixed')"
mypy sbm/utils/ --report .mypy_cache/phase1/  # Should pass on utils

# Phase 2 Gates:  
ruff check sbm/ --statistics  # Target: <500 errors
mypy sbm/ --report .mypy_cache/phase2/  # Target: <100 errors
pytest tests/ --cov=sbm --cov-report=term  # Target: >50% coverage

# Phase 3 Gates:
ruff check sbm/  # Target: <100 errors, should pass
mypy sbm/  # Target: 0 errors, full compliance
pytest tests/ --cov=sbm --cov-fail-under=80  # Target: 80%+ coverage

# Success Criteria Per Phase:
# Phase 1: Environment clean, compatibility fixed, imports organized
# Phase 2: <500 ruff errors, >50% type coverage, no print statements  
# Phase 3: <100 ruff errors, MyPy clean, 80%+ test coverage
```

### Level 3: Functional Integration Testing

```bash
# Integration test - actual migration workflow
cd ~/di-websites-platform  # Real DI environment
sbm migrate test-theme --skip-post-migration --verbose

# Expected outcomes:
# - Migration completes without errors
# - Logs are clean and informative (no print statements)
# - Generated files have proper SCSS syntax
# - No type-related runtime errors
# - Performance comparable to previous version

# CLI integration testing
python -m pytest tests/integration/ -v --tb=short

# Expected: All integration tests pass, error scenarios handled gracefully
```

### Level 4: Production Readiness Validation

```bash
# Comprehensive quality assessment
pytest tests/ -v --cov=sbm --cov-report=html --cov-report=term-missing
ruff check . --statistics
mypy sbm/ --html-report .mypy_cache/html --cobertura-xml-report coverage.xml

# Performance benchmarking
time sbm migrate sample-theme --skip-post-migration
# Should complete in similar time to baseline

# Security validation
bandit -r sbm/ -f json -o security_report.json
safety check --json --output safety_report.json

# Documentation verification
python -c "
import sbm
print('Package imports successfully')
print(f'Version: {sbm.__version__}')
"

# CI/CD pipeline test
pre-commit run --all-files
# Expected: All hooks pass without issues
```

### Level 5: Creative Validation Gates

```bash
# MCP-enhanced validation using existing auto-sbm capabilities
# Real dealer theme migration test
sbm auto bmw-north-america --skip-post-migration --verbose
# Expected: Complex real-world theme migrates successfully

# Multi-theme batch testing  
for theme in volvo-cars bmw-mini stellantis-ram; do
    echo "Testing $theme..."  
    sbm migrate $theme --skip-post-migration || echo "❌ Failed: $theme"
done

# Load generation for performance validation
python -c "
import concurrent.futures
from sbm.scss.processor import SCSSProcessor

themes = ['test1', 'test2', 'test3', 'test4', 'test5']
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(SCSSProcessor, theme) for theme in themes]
    results = [f.result() for f in concurrent.futures.as_completed(futures)]
print(f'✅ Concurrent processing successful: {len(results)} themes')
"

# Memory usage validation
python -c "
import psutil
import os
from sbm.core.migration import migrate_dealer_theme

process = psutil.Process(os.getpid())
initial_memory = process.memory_info().rss / 1024 / 1024

migrate_dealer_theme('test-theme', skip_just=True)

final_memory = process.memory_info().rss / 1024 / 1024
memory_growth = final_memory - initial_memory

print(f'Memory usage: {initial_memory:.1f}MB → {final_memory:.1f}MB')
print(f'Growth: {memory_growth:.1f}MB')
assert memory_growth < 100, f'Excessive memory growth: {memory_growth:.1f}MB'
print('✅ Memory usage within acceptable limits')
"
```

## Final Validation Checklist

- [ ] **Environment**: All tools install and import successfully
- [ ] **Syntax & Style**: `ruff check .` passes with <100 errors
- [ ] **Type Safety**: `mypy sbm/` passes with 0 errors  
- [ ] **Testing**: `pytest tests/ --cov=sbm --cov-fail-under=80` passes
- [ ] **Integration**: Real theme migration works end-to-end
- [ ] **Performance**: Migration times comparable to baseline (<10% regression)
- [ ] **Documentation**: CLAUDE.md accurately reflects implementation
- [ ] **CI/CD**: All GitHub Actions workflows pass
- [ ] **Security**: No S602 or S105 violations, credentials properly handled
- [ ] **Compatibility**: Works on Python 3.9+ across platforms
- [ ] **Developer Experience**: New contributor can be productive in 1 day
- [ ] **Production Ready**: Confident deployment to production environments

---

## Anti-Patterns to Avoid

- ❌ **Breaking Changes**: Don't modify core migration logic behavior
- ❌ **Coverage Gaming**: Don't write meaningless tests just for percentage
- ❌ **Type Annotation Shortcuts**: Don't use `Any` everywhere instead of proper types
- ❌ **Batch Rule Changes**: Don't enable all ruff rules at once - gradual adoption
- ❌ **Mocking Rich Internals**: Use console capture, not mock.patch on Rich objects
- ❌ **Print Statement Debugging**: Use logger.debug(), not print() for debugging
- ❌ **Hardcoded Test Values**: Use fixtures and parameterized tests
- ❌ **Ignoring CI Failures**: All quality gates must pass before merge
- ❌ **Premature Optimization**: Fix correctness first, then performance
- ❌ **Documentation Debt**: Keep docs updated as changes are made

## Success Metrics

### Quantitative Targets
| Metric | Baseline | Phase 1 | Phase 2 | Phase 3 | Target |
|--------|----------|---------|---------|---------|---------|
| Ruff Errors | 936 | <800 | <400 | <100 | <100 |
| MyPy Errors | 469+ | <300 | <100 | 0 | 0 |
| Test Coverage | ~39% | >45% | >65% | >80% | >80% |
| Type Coverage | ~0% | >20% | >60% | >90% | >90% |

### Qualitative Outcomes
- **Developer Onboarding**: From multi-day to 1-day productivity
- **Deployment Confidence**: From risky to reliable
- **Maintenance Burden**: 50% reduction in debugging time
- **IDE Experience**: Full autocomplete and error detection
- **Team Velocity**: Faster development with fewer bugs

**Confidence Level for One-Pass Implementation Success: 9/10**

The comprehensive context, proven patterns, executable validation gates, and industry-standard tooling provide extremely high confidence for successful implementation. The incremental approach with validation loops minimizes risk while the detailed technical guidance and real-world examples ensure implementability.