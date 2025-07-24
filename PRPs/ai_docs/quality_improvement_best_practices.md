# Quality Improvement Best Practices for Auto-SBM

## Ruff Migration Strategies for Large Codebases

### Performance Benefits
- **Speed**: Ruff finishes in 0.5 seconds vs. Flake8's 30 seconds on pandas codebase
- **Scale**: 250k LOC dagster codebase: pylint 2.5 minutes vs ruff 0.4 seconds
- **Caching**: Rust-powered with caching system for consecutive runs

### Three-Stage Migration Approach
1. **Stage 1**: Add ruff without rules, run baseline
2. **Stage 2**: Enable core F rules + subset of E rules (no stylistic overlap with formatter)  
3. **Stage 3**: Gradually add additional rule categories

### Configuration Best Practices
```toml
[tool.ruff]
line-length = 100
target-version = "py39"
src = ["sbm", "tests"]

[tool.ruff.lint]
# Start with minimal rules, expand gradually
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings  
    "F",    # pyflakes
    "I",    # isort
]

# Add rules incrementally as codebase improves
extend-select = [
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "ANN",  # flake8-annotations
    "B",    # flake8-bugbear
]

ignore = [
    "ANN101",  # missing-type-self
    "ANN102",  # missing-type-cls
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*" = ["S101", "PLR2004", "ANN", "ARG"]
```

### Migration Commands
```bash
# Add noqa directives to all violation lines (useful for legacy migration)
ruff check /path/to/file.py --add-noqa

# Auto-fix what's possible
ruff check --fix

# Progressive rule addition
ruff check --select=F,E --fix  # Start minimal
ruff check --select=F,E,W,I --fix  # Add more rules
```

## MyPy Gradual Typing Strategies

### Start Small and Strategic
- Pick 5,000-50,000 LOC subset first
- Prioritize widely imported modules (utilities, models)
- Focus on public APIs and complex functions

### Team Adoption Strategy
```python
# Convention: Add type hints for new code
def new_function(param: str) -> str:
    """All new functions get full type annotations."""
    return param.upper()

# Convention: Add hints when modifying existing code  
def existing_function(param):  # TODO: Add types when next modified
    return param.lower()
```

### MyPy Configuration for Gradual Adoption
```toml
[tool.mypy]
python_version = "3.9"
# Start permissive, increase strictness gradually
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # Start false, enable per-module

# Per-module strictness
[[tool.mypy.overrides]]
module = "sbm.utils.*"  # Start with utility modules
disallow_untyped_defs = true
disallow_incomplete_defs = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false  # Keep tests permissive initially
```

### Automated Type Generation Tools
- **MonkeyType**: Runtime type collection and generation
- **autotyping**: Static analysis-based type inference
- **PyAnnotate**: Facebook's type annotation tool
- **mypy_clean_slate**: Add `type: ignore` to all errors, then fix incrementally

## pytest-cov Testing Strategies for Legacy Code

### Gradual Coverage Improvement
```bash
# Start with baseline measurement
pytest --cov=sbm --cov-report=term-missing

# Focus on critical business logic first
pytest --cov=sbm.core --cov-fail-under=60

# Add integration tests
pytest tests/integration/ --cov=sbm --cov-append
```

### Test Configuration for Legacy Codebases
```toml
[tool.pytest.ini_options]
testpaths = ["sbm", "tests"]
python_files = ["test_*.py"]
addopts = [
    "--cov=sbm",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-fail-under=50",  # Start low, increase gradually
    "--strict-markers",
    "--strict-config",
]

[tool.coverage.run]
source = ["sbm"]
omit = [
    "*/tests/*",
    "*/test_*",
    "*/__pycache__/*",
    "*/migrations/*",  # Often excluded
    "*/vendor/*",      # Third-party code
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if self.debug:",
    "if settings.DEBUG",
    "raise AssertionError", 
    "raise NotImplementedError",
    "if 0:",
    "if __name__ == .__main__.:",
    "class .*\\bProtocol\\):",
    "@(abc\\.)?abstractmethod"
]
```

### Testing Legacy Rich UI Components
```python
# Pattern: Use console capture instead of mocking Rich internals
from io import StringIO
from rich.console import Console

def test_rich_component():
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=80)
    
    # Override console for testing
    component.console = console
    component.display_something()
    
    # Verify output was captured
    output_text = output.getvalue()
    assert "expected content" in output_text
```

## CI/CD Integration Patterns

### Pre-commit Configuration
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests, types-PyYAML]
```

### GitHub Actions Quality Gates
```yaml
# .github/workflows/quality.yml
name: Code Quality
on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: "3.9"
      
      - name: Install dependencies
        run: |
          pip install -e .[dev]
      
      - name: Lint with ruff
        run: |
          ruff check .
          ruff format --check .
      
      - name: Type check with mypy
        run: mypy sbm/
      
      - name: Test with pytest
        run: pytest --cov=sbm --cov-fail-under=50
```

## Python Version Compatibility

### Union Syntax Migration for Python 3.9
```python
# OLD (Python 3.10+):
def function(param: str | None) -> int | str:
    pass

# NEW (Python 3.9 compatible):
from typing import Union, Optional

def function(param: Optional[str]) -> Union[int, str]:
    pass

# Or use __future__ import for newer syntax:
from __future__ import annotations

def function(param: str | None) -> int | str:  # Now works in 3.9+
    pass
```

### Pydantic v2 Configuration Patterns
```python
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class ModernConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8", 
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",  # Critical for cross-env compatibility
    )
    
    setting: str = Field(default="default", description="Description")
    
    @field_validator('setting')
    @classmethod
    def validate_setting(cls, v: str) -> str:
        if not v:
            raise ValueError("Setting cannot be empty")
        return v
```

## Common Pitfalls and Solutions

### Import Organization
```bash
# Fix import issues automatically
ruff check --select=I --fix

# Manual patterns for complex cases:
# 1. Standard library imports
# 2. Third-party imports  
# 3. Local application imports
```

### Logging Performance
```python
# BAD: f-strings in logging (evaluated even when not logged)
logger.info(f"Processing {expensive_computation()}")

# GOOD: Lazy evaluation with % formatting
logger.info("Processing %s", expensive_computation())

# GOOD: Only compute when needed
if logger.isEnabledFor(logging.INFO):
    logger.info("Processing %s", expensive_computation())
```

### Path Operation Modernization
```python
# OLD: os.path usage
import os
path = os.path.join(base, "subdir", "file.txt")
if os.path.exists(path):
    with open(path) as f:
        content = f.read()

# NEW: pathlib usage
from pathlib import Path
path = Path(base) / "subdir" / "file.txt"
if path.exists():
    content = path.read_text()
```

This document provides the essential patterns and strategies needed for successful large-scale Python codebase quality improvement based on industry best practices and real-world migration experiences.