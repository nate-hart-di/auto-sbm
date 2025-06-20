# Auto-SBM Development Guide

## Getting Started

### Development Environment Setup

#### Prerequisites

- **Python 3.8+**: Required for modern async/await and type hints
- **Git**: For version control and GitHub integration
- **Docker**: For DealerInspire platform integration
- **Node.js**: For Gulp and SCSS compilation

#### Clone and Setup

```bash
# Clone the repository
git clone https://github.com/nate-hart-di/auto-sbm.git
cd auto-sbm

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -e ".[dev]"
```

## Development Workflow

### Code Standards

We follow **PEP 8** with these modifications:

- **Line length**: 88 characters (Black default)
- **Type hints**: Required for all public functions
- **Docstrings**: Google style for all public APIs

#### Code Formatting

```bash
# Format code with Black
black sbm/ tests/

# Lint with flake8
flake8 sbm/ tests/

# Type checking with mypy
mypy sbm/
```

### Testing Strategy

#### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sbm --cov-report=html
```

## Extending the Codebase

### Adding New OEM Support

Create new file `sbm/oem/new_oem.py`:

```python
from typing import Dict, Any
from sbm.oem.handler import OEMHandler

class NewOEMHandler(OEMHandler):
    """Handler for New OEM dealer requirements."""

    def get_oem_specific_rules(self) -> Dict[str, Any]:
        """Return New OEM-specific processing rules."""
        return {
            "mixin_mappings": {
                "@include new-oem-mixin": "custom-css-property: value;"
            }
        }
```

## Performance Optimization

### Parallel Processing

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class ParallelSCSSProcessor:
    async def process_files_parallel(self, file_paths):
        """Process multiple SCSS files in parallel."""
        with ThreadPoolExecutor(max_workers=4) as executor:
            tasks = [
                loop.run_in_executor(executor, self._process_single_file, path)
                for path in file_paths
            ]
            return await asyncio.gather(*tasks)
```

## Contributing Guidelines

1. **Fork Repository**: Create personal fork for development
2. **Feature Branch**: Create branch for each feature/fix
3. **Pull Request**: Submit PR with clear description
4. **Code Review**: Address reviewer feedback
5. **Merge**: Squash and merge after approval

---

This development guide provides comprehensive coverage for contributing to and extending the Auto-SBM project.

## Getting Started

### Development Environment Setup

#### Prerequisites

- **Python 3.8+**: Required for modern async/await and type hints
- **Git**: For version control and GitHub integration
- **Docker**: For DealerInspire platform integration
- **Node.js**: For Gulp and SCSS compilation
- **GitHub CLI (optional)**: For enhanced PR management

#### Clone and Setup

```bash
# Clone the repository
git clone https://github.com/nate-hart-di/auto-sbm.git
cd auto-sbm

# Create virtual environment
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

#### Configuration

Create development configuration file:

```bash
# Create local config (gitignored)
cp config.example.yml config.local.yml

# Edit with your settings
vim config.local.yml
```

Example `config.local.yml`:

```yaml
development:
  platform_path: '/path/to/di-websites-platform'
  github_token: 'ghp_xxxxxxxxxxxxxxxx'
  log_level: 'DEBUG'
  skip_docker: false

testing:
  test_dealer_slug: 'test-dealer'
  mock_api_calls: true
  cleanup_test_files: true
```

### Project Structure

```
auto-sbm/
├── sbm/                    # Main package
│   ├── cli.py             # Command-line interface
│   ├── config.py          # Configuration management
│   ├── core/              # Core business logic
│   │   ├── full_workflow.py    # Complete workflow orchestration
│   │   ├── git_operations.py   # Git workflow automation
│   │   ├── migration.py        # SCSS migration engine
│   │   ├── validation.py       # Validation framework
│   │   └── diagnostics.py      # System diagnostics
│   ├── scss/              # SCSS processing
│   │   ├── processor.py        # Main SCSS processor
│   │   ├── mixin_parser.py     # Mixin conversion logic
│   │   ├── validation.py       # SCSS validation
│   │   └── transformer.py      # SCSS transformations
│   ├── oem/               # OEM-specific handlers
│   │   ├── handler.py          # Base OEM handler
│   │   ├── factory.py          # OEM handler factory
│   │   └── stellantis.py       # Stellantis-specific logic
│   └── utils/             # Utility modules
│       ├── logger.py           # Logging framework
│       ├── errors.py           # Exception classes
│       └── helpers.py          # Utility functions
├── tests/                 # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── fixtures/          # Test data and fixtures
├── docs/                  # Documentation
├── scripts/               # Development and deployment scripts
└── pyproject.toml         # Project configuration
```

## Development Workflow

### Code Standards

#### Style Guide

We follow **PEP 8** with these modifications:

- **Line length**: 88 characters (Black default)
- **Type hints**: Required for all public functions
- **Docstrings**: Google style for all public APIs
- **Import order**: isort configuration in pyproject.toml

#### Code Formatting

```bash
# Format code with Black
black sbm/ tests/

# Sort imports with isort
isort sbm/ tests/

# Lint with flake8
flake8 sbm/ tests/

# Type checking with mypy
mypy sbm/
```

#### Pre-commit Hooks

Pre-commit hooks automatically run on commit:

- Black code formatting
- isort import sorting
- flake8 linting
- mypy type checking
- pytest test execution

### Testing Strategy

#### Test Organization

- **Unit Tests**: Test individual functions and classes in isolation
- **Integration Tests**: Test component interactions and workflows
- **End-to-End Tests**: Test complete migration workflows with mock data
- **Performance Tests**: Validate performance benchmarks

#### Running Tests

```bash
# Run all tests
pytest

# Run specific test category
pytest tests/unit/
pytest tests/integration/

# Run with coverage
pytest --cov=sbm --cov-report=html

# Run performance benchmarks
pytest tests/performance/ --benchmark-only
```

#### Test Data Management

Test data is organized in `tests/fixtures/`:

```
tests/fixtures/
├── dealer_themes/         # Sample dealer SCSS themes
│   ├── stellantis/       # Stellantis dealer samples
│   ├── generic/          # Generic dealer samples
│   └── edge_cases/       # Edge case test data
├── expected_outputs/      # Expected migration results
├── mock_responses/        # Mock API responses
└── config/               # Test configuration files
```

#### Writing Tests

Example unit test:

```python
import pytest
from pathlib import Path
from sbm.scss.processor import SCSSProcessor

class TestSCSSProcessor:
    def test_mixin_conversion(self):
        """Test basic mixin conversion functionality."""
        processor = SCSSProcessor(
            input_path=Path("test/input"),
            output_path=Path("test/output")
        )

        input_scss = "@include flexbox(row, center, center);"
        expected_css = "display: flex; flex-direction: row; justify-content: center; align-items: center;"

        result = processor.transform_mixins(input_scss)
        assert result.strip() == expected_css

    @pytest.mark.integration
    def test_full_file_processing(self, tmp_path):
        """Test complete file processing workflow."""
        # Setup test files
        input_file = tmp_path / "test.scss"
        input_file.write_text("@include flexbox(); .test { color: red; }")

        processor = SCSSProcessor(tmp_path, tmp_path)
        result = processor.process_file(input_file)

        assert "display: flex" in result
        assert ".test { color: red; }" in result
```

### Debugging

#### Debug Configuration

Enable debug mode for detailed logging:

```bash
export SBM_LOG_LEVEL=DEBUG
export SBM_DEBUG_MODE=true

# Run with debug output
sbm auto test-dealer --verbose
```

#### IDE Setup

**VS Code Configuration** (`.vscode/settings.json`):

```json
{
  "files.associations": {
    "*.scss": "scss"
  },
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.pylintEnabled": false,
  "python.sortImports.provider": "isort",
  "python.testing.pytestArgs": ["tests/"],
  "python.testing.pytestEnabled": true
}
```

**PyCharm Configuration**:

- Set Python interpreter to `./venv/bin/python`
- Enable pytest as test runner
- Configure Black as external tool
- Set up run configurations for common tasks

#### Common Debug Scenarios

**SCSS Processing Issues**:

```python
# Add to scss/processor.py for debugging
import logging
logger = logging.getLogger(__name__)

def transform_mixins(self, content: str) -> str:
    logger.debug(f"Input content: {content}")
    result = self._apply_mixin_transformations(content)
    logger.debug(f"Transformed content: {result}")
    return result
```

**Git Operation Debugging**:

```bash
# Enable Git debug output
export GIT_TRACE=1
export GIT_CURL_VERBOSE=1

# Run migration with Git debugging
sbm auto test-dealer --verbose
```

## Extending the Codebase

### Adding New OEM Support

#### 1. Create OEM Handler

Create new file `sbm/oem/new_oem.py`:

```python
from typing import Dict, Any, List
from sbm.oem.handler import OEMHandler

class NewOEMHandler(OEMHandler):
    """Handler for New OEM dealer requirements."""

    def detect_brand(self) -> str:
        """Detect specific brand within New OEM."""
        # Implementation for brand detection
        pass

    def get_oem_specific_rules(self) -> Dict[str, Any]:
        """Return New OEM-specific processing rules."""
        return {
            "mixin_mappings": {
                "@include new-oem-mixin": "custom-css-property: value;"
            },
            "variable_mappings": {
                "$new-oem-color": "var(--new-oem-primary)"
            },
            "file_mappings": {
                "custom.scss": "sb-custom.scss"
            }
        }

    def apply_oem_transformations(self, content: str) -> str:
        """Apply New OEM-specific transformations."""
        # Custom transformation logic
        return content

    def get_pr_template(self) -> str:
        """Return New OEM PR template."""
        return """
        # New OEM Site Builder Migration

        ## Changes
        - Migrated legacy SCSS to Site Builder format
        - Applied New OEM-specific transformations

        ## Validation
        - [ ] SCSS compiles without errors
        - [ ] New OEM brand guidelines followed
        - [ ] Responsive design maintained
        """

    def get_reviewer_assignments(self) -> List[str]:
        """Return appropriate reviewers for New OEM."""
        return ["new-oem-team", "carsdotcom/fe-dev"]
```

#### 2. Register in Factory

Update `sbm/oem/factory.py`:

```python
from sbm.oem.new_oem import NewOEMHandler

class OEMHandlerFactory:
    _handlers = {
        "stellantis": StellantisHandler,
        "new_oem": NewOEMHandler,  # Add new handler
        "generic": OEMHandler
    }

    def detect_oem_type(self, dealer_slug: str) -> str:
        """Enhanced OEM detection logic."""
        if any(brand in dealer_slug.lower() for brand in ["new", "oem", "specific"]):
            return "new_oem"
        # ... existing detection logic
```

#### 3. Add Tests

Create `tests/unit/oem/test_new_oem.py`:

```python
import pytest
from sbm.oem.new_oem import NewOEMHandler

class TestNewOEMHandler:
    def test_brand_detection(self):
        handler = NewOEMHandler("new-oem-dealer")
        brand = handler.detect_brand()
        assert brand in ["brand1", "brand2", "brand3"]

    def test_oem_transformations(self):
        handler = NewOEMHandler("new-oem-dealer")
        input_scss = "@include new-oem-mixin();"
        result = handler.apply_oem_transformations(input_scss)
        assert "custom-css-property: value;" in result
```

### Adding New SCSS Transformations

#### 1. Extend Mixin Parser

Update `sbm/scss/mixin_parser.py`:

```python
class MixinParser:
    def __init__(self):
        self._mixin_handlers = {
            "flexbox": self._convert_flexbox,
            "transition": self._convert_transition,
            "new_mixin": self._convert_new_mixin,  # Add new handler
        }

    def _convert_new_mixin(self, args: List[str]) -> str:
        """Convert new custom mixin to CSS."""
        if not args:
            return "new-css-property: default-value;"

        # Parse arguments and generate CSS
        value = args[0] if args else "default"
        return f"new-css-property: {value}; additional-property: auto;"
```

#### 2. Add Validation Rules

Update `sbm/scss/validation.py`:

```python
class SCSSValidator:
    def validate_mixin_usage(self, content: str) -> List[ValidationResult]:
        """Validate mixin usage in SCSS content."""
        results = []

        # Check for new mixin pattern
        if "@include new_mixin" in content:
            if not self._validate_new_mixin_args(content):
                results.append(ValidationResult(
                    status="error",
                    message="Invalid arguments for new_mixin",
                    details={"line": self._find_line_number(content, "new_mixin")}
                ))

        return results
```

### Adding New CLI Commands

#### 1. Create Command Module

Create `sbm/commands/new_command.py`:

```python
import click
from sbm.core.new_feature import NewFeatureEngine

@click.command()
@click.argument('dealer_slug')
@click.option('--option1', help='Custom option for new command')
@click.option('--dry-run', is_flag=True, help='Preview changes only')
def new_command(dealer_slug: str, option1: str, dry_run: bool):
    """New custom command for special operations."""
    try:
        engine = NewFeatureEngine(dealer_slug, option1)

        if dry_run:
            result = engine.preview_changes()
            click.echo(f"Would perform: {result}")
        else:
            result = engine.execute()
            click.echo(f"Completed: {result}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.ClickException(str(e))
```

#### 2. Register Command

Update `sbm/cli.py`:

```python
from sbm.commands.new_command import new_command

@cli.group()
def main():
    """SBM Tool V2 - Site Builder Migration Tool"""
    pass

# Add new command to CLI
main.add_command(new_command)
```

## Performance Optimization

### Profiling

#### CPU Profiling

```python
import cProfile
import pstats
from sbm.core.migration import MigrationEngine

def profile_migration():
    """Profile migration performance."""
    profiler = cProfile.Profile()

    # Start profiling
    profiler.enable()

    # Run migration
    engine = MigrationEngine("test-dealer")
    engine.migrate_dealer_theme()

    # Stop profiling
    profiler.disable()

    # Analyze results
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions

if __name__ == "__main__":
    profile_migration()
```

#### Memory Profiling

```python
from memory_profiler import profile

@profile
def memory_intensive_operation():
    """Profile memory usage of SCSS processing."""
    processor = SCSSProcessor(large_input_path, output_path)
    result = processor.process_large_theme()
    return result
```

### Optimization Strategies

#### Parallel Processing

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List

class ParallelSCSSProcessor:
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers

    async def process_files_parallel(self, file_paths: List[Path]) -> List[str]:
        """Process multiple SCSS files in parallel."""
        loop = asyncio.get_event_loop()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            tasks = [
                loop.run_in_executor(executor, self._process_single_file, path)
                for path in file_paths
            ]

            results = await asyncio.gather(*tasks)
            return results
```

#### Caching

```python
from functools import lru_cache
import hashlib

class CachedSCSSProcessor:
    def __init__(self):
        self._cache_dir = Path(".sbm_cache")
        self._cache_dir.mkdir(exist_ok=True)

    @lru_cache(maxsize=128)
    def _get_cached_transformation(self, content_hash: str) -> str:
        """Get cached transformation result."""
        cache_file = self._cache_dir / f"{content_hash}.css"
        if cache_file.exists():
            return cache_file.read_text()
        return None

    def process_with_cache(self, content: str) -> str:
        """Process SCSS with caching."""
        content_hash = hashlib.md5(content.encode()).hexdigest()

        # Check cache first
        cached_result = self._get_cached_transformation(content_hash)
        if cached_result:
            return cached_result

        # Process and cache result
        result = self._process_scss(content)
        cache_file = self._cache_dir / f"{content_hash}.css"
        cache_file.write_text(result)

        return result
```

## Release Process

### Version Management

We use **Semantic Versioning** (SemVer):

- **MAJOR**: Breaking changes to CLI or public API
- **MINOR**: New features, backward-compatible changes
- **PATCH**: Bug fixes, security updates

#### Release Checklist

1. **Update Version**:

   ```bash
   # Update version in pyproject.toml
   # Update version in sbm/__init__.py
   # Update CHANGELOG.md
   ```

2. **Run Full Test Suite**:

   ```bash
   pytest tests/ --cov=sbm --cov-min=80
   pytest tests/integration/
   pytest tests/performance/
   ```

3. **Update Documentation**:

   ```bash
   # Regenerate API docs
   sphinx-apidoc -o docs/api sbm/
   
   # Update README if needed
   # Update CHANGELOG.md
   ```

4. **Create Release Branch**:

   ```bash
   git checkout -b release/v2.6.0
   git commit -am "Prepare release v2.6.0"
   git push origin release/v2.6.0
   ```

5. **Create GitHub Release**:

   ```bash
   gh release create v2.6.0 \
     --title "Release v2.6.0" \
     --notes-file CHANGELOG.md \
     --target main
   ```

6. **Publish to PyPI**:
   ```bash
   python -m build
   python -m twine upload dist/*
   ```

### Automated CI/CD

#### GitHub Actions Workflow

`.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10', 3.11]

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v3
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Run tests
        run: |
          pytest tests/ --cov=sbm --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  release:
    if: github.ref == 'refs/heads/main'
    needs: test
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Build and publish
        run: |
          python -m build
          python -m twine upload dist/*
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
```

## Contributing Guidelines

### Code Review Process

1. **Fork Repository**: Create personal fork for development
2. **Feature Branch**: Create branch for each feature/fix
3. **Pull Request**: Submit PR with clear description
4. **Code Review**: Address reviewer feedback
5. **Merge**: Squash and merge after approval

### PR Template

```markdown
## Description

Brief description of changes made.

## Type of Change

- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing

- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist

- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Code is commented and documented
- [ ] No new warnings introduced
- [ ] Tests added for changes
```

### Community Standards

- **Be respectful**: Follow code of conduct
- **Be helpful**: Assist other contributors
- **Be clear**: Write clear commit messages and PR descriptions
- **Be thorough**: Include tests and documentation
- **Be patient**: Allow time for reviews and feedback

---

This development guide provides comprehensive coverage for contributing to and extending the Auto-SBM project. For questions or clarifications, please open an issue or discussion on the GitHub repository.
