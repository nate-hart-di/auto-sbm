# Auto-SBM API Reference

## Overview

This document provides comprehensive API reference for the SBM Tool V2 codebase. The API is organized into logical modules that handle different aspects of the Site Builder migration process.

## Core Modules

### `sbm.cli`

**Main Entry Point**: Command-line interface for the SBM tool.

#### Functions

##### `main()`

```python
def main() -> None
```

Primary entry point for the CLI application.

**Description**: Initializes the Click command group and handles global exception catching.

---

### `sbm.config`

**Configuration Management**: Handles system configuration and auto-detection.

#### Classes

##### `SBMConfig`

```python
class SBMConfig:
    def __init__(self, config_path: Optional[str] = None)
    def get_platform_path(self) -> Path
    def get_github_token(self) -> str
    def get_context7_config(self) -> Dict[str, Any]
    def validate_environment(self) -> bool
```

**Description**: Main configuration class that manages system settings and auto-detection.

**Methods**:

- `get_platform_path()`: Auto-detects or returns configured DI platform path
- `get_github_token()`: Retrieves GitHub token from MCP config or environment
- `get_context7_config()`: Loads Context7 API configuration
- `validate_environment()`: Validates that all required dependencies are available

#### Functions

##### `get_config()`

```python
def get_config(config_path: Optional[str] = None) -> SBMConfig
```

Factory function to create and return configured SBMConfig instance.

---

### `sbm.core.full_workflow`

**Complete Migration Orchestration**: Manages the end-to-end migration process.

#### Classes

##### `FullMigrationWorkflow`

```python
class FullMigrationWorkflow:
    def __init__(self, dealer_slug: str, options: Dict[str, Any])
    async def run_complete_migration(self) -> Dict[str, Any]
    def run_diagnostics(self) -> bool
    def setup_git_workflow(self) -> bool
    def start_docker_environment(self) -> bool
    def run_scss_migration(self) -> bool
    def validate_migration(self) -> bool
    def create_git_commit(self) -> bool
    def create_github_pr(self) -> str
    def generate_salesforce_message(self) -> str
```

**Description**: Orchestrates the complete migration workflow from start to finish.

**Key Methods**:

- `run_complete_migration()`: Executes all migration steps in sequence
- `run_diagnostics()`: Validates system environment and dependencies
- `setup_git_workflow()`: Handles branch creation and repository setup
- `start_docker_environment()`: Manages Docker container startup and monitoring
- `run_scss_migration()`: Executes SCSS transformation and file generation
- `validate_migration()`: Runs validation checks on generated files
- `create_git_commit()`: Commits changes with appropriate messaging
- `create_github_pr()`: Generates GitHub pull request with metadata
- `generate_salesforce_message()`: Creates Salesforce integration message

---

### `sbm.core.git_operations`

**Git Workflow Management**: Handles all Git-related operations.

#### Classes

##### `GitOperationsManager`

```python
class GitOperationsManager:
    def __init__(self, platform_path: Path, dealer_slug: str)
    def checkout_main_and_pull(self) -> bool
    def create_migration_branch(self) -> str
    def commit_changes(self, message: str) -> bool
    def create_pull_request(self, title: str, body: str) -> str
    def handle_merge_conflicts(self) -> bool
    def validate_repository_state(self) -> bool
```

**Description**: Manages Git operations including branching, committing, and PR creation.

**Key Methods**:

- `checkout_main_and_pull()`: Switches to main branch and pulls latest changes
- `create_migration_branch()`: Creates migration branch with standardized naming
- `commit_changes()`: Commits staged changes with validation
- `create_pull_request()`: Creates GitHub PR using API
- `handle_merge_conflicts()`: Automated resolution of common conflicts
- `validate_repository_state()`: Ensures repository is in valid state for operations

---

### `sbm.core.migration`

**SCSS Migration Engine**: Core migration logic and file transformations.

#### Classes

##### `MigrationEngine`

```python
class MigrationEngine:
    def __init__(self, platform_path: Path, dealer_slug: str)
    def migrate_dealer_theme(self) -> Dict[str, Any]
    def process_scss_files(self) -> List[str]
    def transform_file_mappings(self) -> Dict[str, str]
    def apply_mixin_conversions(self, content: str) -> str
    def generate_output_files(self) -> bool
```

**Description**: Handles the core SCSS migration and transformation logic.

**Key Methods**:

- `migrate_dealer_theme()`: Main migration orchestration method
- `process_scss_files()`: Processes individual SCSS files
- `transform_file_mappings()`: Maps legacy files to Site Builder equivalents
- `apply_mixin_conversions()`: Converts SCSS mixins to modern CSS
- `generate_output_files()`: Creates final output files

---

### `sbm.core.validation`

**Validation Framework**: Multi-tier validation system.

#### Classes

##### `ValidationEngine`

```python
class ValidationEngine:
    def __init__(self, platform_path: Path, dealer_slug: str)
    def validate_system_environment(self) -> ValidationResult
    def validate_scss_syntax(self, file_path: Path) -> ValidationResult
    def validate_file_integrity(self, file_path: Path) -> ValidationResult
    def validate_migration_output(self) -> ValidationResult
    def run_complete_validation(self) -> List[ValidationResult]
```

##### `ValidationResult`

```python
class ValidationResult:
    def __init__(self, status: str, message: str, details: Dict[str, Any])
    def is_success(self) -> bool
    def is_warning(self) -> bool
    def is_error(self) -> bool
    def get_error_message(self) -> str
```

**Description**: Comprehensive validation system for all migration aspects.

**ValidationEngine Methods**:

- `validate_system_environment()`: Checks system dependencies and permissions
- `validate_scss_syntax()`: Validates SCSS file syntax and structure
- `validate_file_integrity()`: Ensures file integrity and proper formatting
- `validate_migration_output()`: Validates final migration results
- `run_complete_validation()`: Executes all validation checks

---

### `sbm.scss.processor`

**SCSS Processing Engine**: Advanced SCSS transformation and conversion.

#### Classes

##### `SCSSProcessor`

```python
class SCSSProcessor:
    def __init__(self, input_path: Path, output_path: Path)
    def process_file(self, file_path: Path) -> str
    def parse_scss_content(self, content: str) -> SCSSNode
    def transform_mixins(self, content: str) -> str
    def convert_variables(self, content: str) -> str
    def standardize_breakpoints(self, content: str) -> str
    def resolve_imports(self, content: str) -> str
```

**Description**: Handles advanced SCSS processing and transformation.

**Key Methods**:

- `process_file()`: Main file processing entry point
- `parse_scss_content()`: Parses SCSS into abstract syntax tree
- `transform_mixins()`: Converts SCSS mixins to modern CSS
- `convert_variables()`: Transforms variables to CSS custom properties
- `standardize_breakpoints()`: Standardizes media query breakpoints
- `resolve_imports()`: Resolves and processes SCSS imports

---

### `sbm.scss.mixin_parser`

**Mixin Conversion System**: Specialized mixin transformation logic.

#### Classes

##### `MixinParser`

```python
class MixinParser:
    def __init__(self)
    def parse_mixin_call(self, mixin_call: str) -> MixinCall
    def convert_flexbox_mixin(self, args: List[str]) -> str
    def convert_transition_mixin(self, args: List[str]) -> str
    def convert_border_radius_mixin(self, args: List[str]) -> str
    def get_supported_mixins(self) -> List[str]
```

##### `MixinCall`

```python
class MixinCall:
    def __init__(self, name: str, args: List[str], source_line: int)
    def to_css(self) -> str
    def validate_args(self) -> bool
```

**Description**: Specialized parser for SCSS mixin conversion.

**MixinParser Methods**:

- `parse_mixin_call()`: Parses SCSS mixin call syntax
- `convert_flexbox_mixin()`: Converts flexbox mixin to modern CSS
- `convert_transition_mixin()`: Handles CSS transition conversions
- `convert_border_radius_mixin()`: Converts border radius mixins
- `get_supported_mixins()`: Returns list of supported mixin conversions

---

### `sbm.oem.handler`

**OEM-Specific Processing**: Handles manufacturer-specific requirements.

#### Classes

##### `OEMHandler`

```python
class OEMHandler:
    def __init__(self, dealer_slug: str)
    def detect_oem_type(self) -> str
    def get_oem_specific_rules(self) -> Dict[str, Any]
    def apply_oem_transformations(self, content: str) -> str
    def get_pr_template(self) -> str
    def get_reviewer_assignments(self) -> List[str]
```

##### `StellantisHandler(OEMHandler)`

```python
class StellantisHandler(OEMHandler):
    def detect_brand(self) -> str
    def apply_fca_specific_rules(self, content: str) -> str
    def get_stellantis_pr_template(self) -> str
```

**Description**: Handles OEM-specific processing requirements.

**OEMHandler Methods**:

- `detect_oem_type()`: Automatically detects OEM type from dealer slug
- `get_oem_specific_rules()`: Returns OEM-specific processing rules
- `apply_oem_transformations()`: Applies OEM-specific transformations
- `get_pr_template()`: Returns appropriate PR template for OEM
- `get_reviewer_assignments()`: Gets appropriate code reviewers

---

### `sbm.utils.logger`

**Logging Framework**: Comprehensive logging and output management.

#### Functions

##### `get_logger()`

```python
def get_logger(name: str, level: str = "INFO") -> Logger
```

Factory function to create configured logger instances.

##### `setup_logging()`

```python
def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    verbose: bool = False
) -> None
```

Configures the global logging system.

#### Classes

##### `RichProgressLogger`

```python
class RichProgressLogger:
    def __init__(self, total_steps: int)
    def start_step(self, step_name: str) -> None
    def complete_step(self, success: bool = True) -> None
    def log_error(self, message: str) -> None
    def log_warning(self, message: str) -> None
    def finalize(self) -> None
```

**Description**: Rich terminal progress logging with visual feedback.

---

## Error Handling

### Exception Classes

#### `SBMError`

```python
class SBMError(Exception):
    def __init__(self, message: str, error_code: str = None, details: Dict = None)
    def get_error_code(self) -> str
    def get_details(self) -> Dict[str, Any]
    def format_for_display(self) -> str
```

#### `ValidationError(SBMError)`

```python
class ValidationError(SBMError):
    def __init__(self, validation_results: List[ValidationResult])
    def get_failed_validations(self) -> List[ValidationResult]
```

#### `GitOperationError(SBMError)`

```python
class GitOperationError(SBMError):
    def __init__(self, operation: str, git_error: str)
    def get_operation(self) -> str
    def get_git_error(self) -> str
```

#### `DockerError(SBMError)`

```python
class DockerError(SBMError):
    def __init__(self, container_name: str, docker_error: str)
    def get_container_name(self) -> str
    def get_docker_error(self) -> str
```

---

## Configuration Classes

### `WorkflowOptions`

```python
class WorkflowOptions:
    def __init__(
        self,
        force: bool = False,
        dry_run: bool = False,
        skip_docker: bool = False,
        verbose: bool = False
    )
    def to_dict(self) -> Dict[str, Any]
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowOptions'
```

### `MigrationSettings`

```python
class MigrationSettings:
    def __init__(
        self,
        input_path: Path,
        output_path: Path,
        dealer_slug: str,
        oem_type: Optional[str] = None
    )
    def validate(self) -> bool
    def get_output_files(self) -> List[Path]
```

---

## Utility Functions

### File Operations

#### `safe_file_write()`

```python
def safe_file_write(file_path: Path, content: str, backup: bool = True) -> bool
```

Safely writes content to file with optional backup creation.

#### `ensure_directory()`

```python
def ensure_directory(directory_path: Path, create_parents: bool = True) -> bool
```

Ensures directory exists, creating it if necessary.

#### `cleanup_temporary_files()`

```python
def cleanup_temporary_files(temp_dir: Path) -> None
```

Cleans up temporary files and directories.

### Docker Operations

#### `get_container_status()`

```python
def get_container_status(container_name: str) -> str
```

Returns the current status of a Docker container.

#### `monitor_container_logs()`

```python
def monitor_container_logs(
    container_name: str,
    timeout: int = 45,
    pattern: Optional[str] = None
) -> bool
```

Monitors container logs for specific patterns or errors.

### Git Utilities

#### `get_current_branch()`

```python
def get_current_branch(repo_path: Path) -> str
```

Returns the name of the current Git branch.

#### `is_repository_clean()`

```python
def is_repository_clean(repo_path: Path) -> bool
```

Checks if the repository has uncommitted changes.

#### `get_remote_url()`

```python
def get_remote_url(repo_path: Path, remote_name: str = "origin") -> str
```

Returns the URL of the specified Git remote.

---

## Constants

### File Mappings

```python
LEGACY_TO_SB_MAPPINGS = {
    "lvdp.scss": "sb-vdp.scss",
    "lvrp.scss": "sb-vrp.scss",
    "inside.scss": "sb-inside.scss"
}
```

### Default Breakpoints

```python
STANDARD_BREAKPOINTS = {
    "tablet": "768px",
    "desktop": "1024px",
    "large": "1200px"
}
```

### Supported Mixins

```python
SUPPORTED_MIXINS = [
    "flexbox",
    "transition",
    "border-radius",
    "box-shadow",
    "gradient",
    "transform"
]
```

---

## Usage Examples

### Basic Migration

```python
from sbm.core.full_workflow import FullMigrationWorkflow
from sbm.config import WorkflowOptions

# Create workflow options
options = WorkflowOptions(force=False, dry_run=False)

# Initialize workflow
workflow = FullMigrationWorkflow("dealer-slug", options.to_dict())

# Run complete migration
result = await workflow.run_complete_migration()

if result['success']:
    print(f"Migration completed successfully: {result['pr_url']}")
else:
    print(f"Migration failed: {result['error']}")
```

### Custom SCSS Processing

```python
from sbm.scss.processor import SCSSProcessor
from pathlib import Path

# Initialize processor
processor = SCSSProcessor(
    input_path=Path("input/dealer-theme"),
    output_path=Path("output/site-builder")
)

# Process specific file
result = processor.process_file(Path("input/dealer-theme/lvdp.scss"))
print(f"Processed content: {result}")
```

### Validation Only

```python
from sbm.core.validation import ValidationEngine
from pathlib import Path

# Initialize validation engine
validator = ValidationEngine(
    platform_path=Path("/path/to/di-platform"),
    dealer_slug="dealer-slug"
)

# Run complete validation
results = validator.run_complete_validation()

for result in results:
    if result.is_error():
        print(f"Error: {result.get_error_message()}")
    elif result.is_warning():
        print(f"Warning: {result.message}")
```

---

## Integration Points

### Context7 API Integration

The tool integrates with Context7 for enhanced documentation and error handling:

```python
from sbm.utils.context7 import Context7Client

client = Context7Client()
enhanced_docs = client.get_enhanced_documentation("error-code-123")
```

### MCP Integration

Model Context Protocol integration for AI assistant support:

```python
from sbm.utils.mcp import MCPClient

mcp_client = MCPClient()
config = mcp_client.get_configuration()
github_token = config.get('github_token')
```

---

This API reference provides comprehensive coverage of the SBM Tool V2 codebase. For implementation examples and detailed usage patterns, refer to the main project documentation and test files.
