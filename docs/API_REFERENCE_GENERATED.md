# SBM Tool v2 - Generated API Reference

_Generated from indexed knowledge using crawl4ai-rag system_

## Table of Contents

1. [Core Classes](#core-classes)
2. [CLI Commands](#cli-commands)
3. [Configuration System](#configuration-system)
4. [Migration Workflow](#migration-workflow)
5. [SCSS Processing](#scss-processing)
6. [OEM Detection](#oem-detection)
7. [User Review System](#user-review-system)
8. [Git Operations](#git-operations)
9. [Utilities](#utilities)
10. [Testing Framework](#testing-framework)

## Core Classes

### Configuration (`config.py`)

#### `SBMConfig`

Main configuration class managing project settings and paths.

**Properties:**

- `di_platform_dir: str` - Path to DealerInspire platform directory
- `dealer_slug: str` - Dealer identifier slug
- `theme_path: str` - Path to dealer theme directory

**Methods:**

- `get_theme_path(dealer_slug: str) -> str` - Returns absolute path to theme directory
- `validate_configuration() -> bool` - Validates configuration settings
- `auto_detect_platform() -> bool` - Auto-detects ~/di-websites-platform

**Example:**

```python
config = SBMConfig()
theme_path = config.get_theme_path("example-dealer")
```

### Migration Workflow (`core/full_workflow.py`)

#### `FullMigrationWorkflow`

Orchestrates the complete 8-step migration process.

**Constructor:**

```python
FullMigrationWorkflow(config: SBMConfig, dealer_slug: str)
```

**Core Methods:**

- `run_full_migration() -> bool` - Executes complete migration workflow
- `step_1_diagnostics() -> bool` - System diagnostics
- `step_2_git_setup() -> bool` - Git branch setup
- `step_3_docker_startup() -> bool` - Docker container startup
- `step_4_theme_migration() -> bool` - Automated theme processing
- `step_5_user_review() -> bool` - **NEW** Interactive user review session
- `step_6_file_saving() -> bool` - File saving and gulp compilation
- `step_7_validation() -> bool` - Output validation
- `step_8_pull_request() -> bool` - PR creation with confirmation

**8-Step Workflow Process:**

1. System Diagnostics
2. Git Setup
3. Docker Startup
4. Theme Migration (Automated)
5. **User Review Session** (NEW in v2.9.0)
6. File Saving & Gulp
7. Validation
8. Pull Request (with confirmation)

### User Review System (`core/user_review.py`) - NEW v2.9.0

#### `UserReviewManager`

Interactive review session with comprehensive change tracking.

**Constructor:**

```python
UserReviewManager(config: SBMConfig, generated_files: List[str])
```

**Core Methods:**

- `start_review_session() -> ReviewResult` - Begin interactive review
- `capture_file_states() -> Dict[str, FileState]` - Capture file MD5/size/lines
- `detect_manual_changes() -> List[FileChange]` - Detect manual modifications
- `generate_review_report() -> ReviewReport` - Generate change analysis report

**Interactive Commands:**

- `done` - Complete review session
- `help` - Show available commands
- `status` - Display current file states

**FileState Properties:**

- `md5_hash: str` - File content hash
- `file_size: int` - Size in bytes
- `line_count: int` - Number of lines
- `modified_time: datetime` - Last modification timestamp

### SCSS Processing (`scss/processor.py`)

#### `SCSSProcessor`

Processes legacy SCSS files and generates Site Builder compatible output.

**Core Methods:**

- `process_legacy_files(theme_path: str) -> ProcessingResult` - Main processing entry point
- `extract_inside_styles(inside_scss: str) -> str` - Extract inside page styles
- `extract_vdp_styles(vdp_scss: str) -> str` - Extract VDP styles
- `extract_vrp_styles(vrp_scss: str) -> str` - Extract VRP styles
- `convert_hex_colors(scss_content: str) -> str` - Convert hex colors to CSS variables
- `apply_production_headers(file_type: str) -> str` - Add production file headers

**Enhanced Color Conversion:**

```python
# Example color mapping (v2.5.0 enhancement)
color_map = {
    '#008001': 'var(--green-008001, #008001)',
    '#32CD32': 'var(--lime-green, #32CD32)',
    '#e20000': 'var(--red-e20000, #e20000)',
    '#093382': 'var(--blue-093382, #093382)',
    '#1a5490': 'var(--blue-1a5490, #1a5490)'
}
```

**Output Files:**

- `sb-inside.scss` - Inside page styles
- `sb-vdp.scss` - Vehicle Detail Page styles
- `sb-vrp.scss` - Vehicle Results Page styles

### OEM Detection (`oem/base.py`, `oem/stellantis.py`)

#### `OEMHandlerFactory`

Factory class for creating brand-specific handlers.

**Methods:**

- `get_handler(dealer_slug: str) -> OEMHandler` - Get appropriate handler for dealer
- `detect_brand(dealer_slug: str) -> str` - Detect dealer brand/OEM

**Fixed Implementation:**

```python
# Correct usage (was previously hallucinated)
handler = OEMHandlerFactory(config).get_handler(dealer_slug)
```

#### `StellantisHandler`

Specialized handler for Stellantis/FCA dealers.

**Methods:**

- `generate_map_components() -> str` - Generate map components with directions box
- `apply_stellantis_templates(files: Dict[str, str]) -> Dict[str, str]` - Apply brand templates
- `get_production_headers() -> Dict[str, str]` - Get Stellantis-specific headers

### Git Operations (`core/git_operations.py`)

#### `GitOperations`

Enhanced git operations with user review tracking.

**Constructor:**

```python
GitOperations(config: SBMConfig)
```

**Core Methods:**

- `create_feature_branch(dealer_slug: str) -> bool` - Create migration branch
- `commit_changes(message: str, files: List[str]) -> bool` - Commit with proper paths
- `create_enhanced_pr(dealer_slug: str, review_result: ReviewResult) -> bool` - **NEW** Enhanced PR creation
- `push_branch() -> bool` - Push branch to remote

**Enhanced PR Features (v2.9.0):**

- Automated vs manual work separation
- User review tracking integration
- Development insights for automation improvement
- GitHub action confirmation prompts

## CLI Commands

### Basic Commands (Default Interface)

#### `sbm auto [dealer-name]`

Execute full automated migration workflow.

**Options:**

- `--force` - Skip validation checks
- `--skip-docker` - Skip Docker startup
- `--dry-run` - Preview operations without execution

**Example:**

```bash
sbm auto example-dealer
```

#### `sbm doctor`

Run comprehensive system diagnostics.

**Checks:**

- DealerInspire platform setup
- Docker availability
- GitHub CLI configuration
- Path validation

#### `sbm validate [dealer]`

Validate dealer slug and configuration.

**Validation:**

- Dealer slug format
- Theme directory existence
- Git repository status

### Advanced Commands (Hidden by default)

Use `sbm --advanced` to see all commands.

#### `sbm setup [dealer]`

Setup environment for specific dealer.

#### `sbm migrate [dealer]`

Run migration process only.

#### `sbm config-info`

Display current configuration.

#### `sbm create-pr [dealer]`

Create pull request only.

### Command Options

**Global Options:**

- `--help, -h` - Show help information
- `--advanced` - Show all commands including hidden ones
- `--verbose` - Enable verbose logging
- `--config-file` - Specify custom config file

## Configuration System

### Auto-Detection

- Automatically detects `~/di-websites-platform`
- Reads `~/.cursor/mcp.json` for platform configuration
- Validates paths and permissions

### Configuration Properties

```python
{
    "di_platform_dir": "/path/to/di-websites-platform",
    "dealer_themes_dir": "/path/to/dealer-themes",
    "docker_compose_file": "docker-compose.yml",
    "github_repo": "di-websites-platform"
}
```

### Environment Support

- Development vs Production environments
- Custom path overrides
- Debug mode settings

## Migration Workflow API

### Workflow Steps

#### Step 1: System Diagnostics

```python
diagnostics = SystemDiagnostics(config)
result = diagnostics.run_all_checks()
```

#### Step 2: Git Setup

```python
git_ops = GitOperations(config)
branch_created = git_ops.create_feature_branch(dealer_slug)
```

#### Step 3: Docker Startup

```python
docker_manager = DockerManager(config)
containers_ready = docker_manager.start_platform()
```

#### Step 4: Theme Migration

```python
scss_processor = SCSSProcessor(config)
migration_result = scss_processor.process_legacy_files(theme_path)
```

#### Step 5: User Review (NEW)

```python
review_manager = UserReviewManager(config, generated_files)
review_result = review_manager.start_review_session()
```

#### Step 6: File Saving & Gulp

```python
file_manager = FileManager(config)
gulp_result = file_manager.save_and_compile(processed_files)
```

#### Step 7: Validation

```python
validator = MigrationValidator(config)
validation_result = validator.validate_output(output_files)
```

#### Step 8: Pull Request

```python
git_ops = GitOperations(config)
pr_created = git_ops.create_enhanced_pr(dealer_slug, review_result)
```

## SCSS Processing API

### Color Conversion API

```python
processor = SCSSProcessor()

# Convert individual colors
converted = processor.convert_hex_color("#008001")
# Returns: "var(--green-008001, #008001)"

# Process entire SCSS content
scss_content = ".button { background: #008001; }"
converted_scss = processor.convert_hex_colors(scss_content)
# Returns: ".button { background: var(--green-008001, #008001); }"
```

### Production Headers API

```python
# Get headers for specific file types
inside_header = processor.get_production_header("inside")
vdp_header = processor.get_production_header("vdp")
vrp_header = processor.get_production_header("vrp")
```

### Processing Results

```python
class ProcessingResult:
    success: bool
    files_generated: List[str]
    warnings: List[str]
    errors: List[str]
    statistics: ProcessingStats
```

## OEM Detection API

### Brand Detection

```python
factory = OEMHandlerFactory(config)
brand = factory.detect_brand("example-stellantis-dealer")
# Returns: "stellantis" or "generic"

handler = factory.get_handler("example-dealer")
# Returns: StellantisHandler or GenericHandler
```

### Stellantis Features

```python
stellantis_handler = StellantisHandler(config)

# Generate map components
map_html = stellantis_handler.generate_map_components()

# Apply brand-specific templates
branded_files = stellantis_handler.apply_stellantis_templates(scss_files)
```

## User Review System API (NEW v2.9.0)

### Review Session API

```python
review_manager = UserReviewManager(config, generated_files)

# Start interactive session
review_result = review_manager.start_review_session()

# Check for manual changes
changes = review_manager.detect_manual_changes()

# Generate report
report = review_manager.generate_review_report()
```

### Review Result Structure

```python
class ReviewResult:
    automated_files: List[str]
    manually_modified_files: List[str]
    file_changes: Dict[str, FileChange]
    review_duration: int
    user_feedback: str
```

### File Change Tracking

```python
class FileChange:
    file_path: str
    size_before: int
    size_after: int
    lines_before: int
    lines_after: int
    md5_before: str
    md5_after: str
    modification_type: str  # "automated", "manual", "mixed"
```

## Git Operations API

### Enhanced PR Creation (NEW v2.9.0)

```python
git_ops = GitOperations(config)

# Create enhanced PR with user review data
pr_result = git_ops.create_enhanced_pr(
    dealer_slug="example-dealer",
    review_result=review_result
)
```

### PR Structure

Enhanced PRs include:

- **Automated Migration** section listing tool-generated changes
- **Manual Refinements** section with size differences
- **Development Notes** explaining automation effectiveness
- Clear tracking for improving future automation

## Testing Framework API

### Production Validation

```python
# Test against production patterns
validator = ProductionValidator()
result = validator.validate_against_real_prs(output_files)

# Comprehensive test suite
test_suite = ComprehensiveTestSuite()
test_results = test_suite.run_all_tests()
```

### Real-World Test Cases

The tool includes validation against 10+ real production cases:

- `case_11699_spitzermotorsofmansfieldcdjr`
- `case_12755_example_maserati_2`
- `case_12760_example_maserati_1`
- And more...

### Test Categories

- **Real Pattern Tests** - Validates against actual PR patterns
- **File Structure Tests** - Ensures correct file creation
- **Content Validation** - Verifies map components and headers
- **Production Readiness** - 100% success rate validation

## Error Handling

### Exception Classes

```python
class SBMError(Exception):
    """Base exception for SBM operations"""
    pass

class ConfigurationError(SBMError):
    """Configuration-related errors"""
    pass

class MigrationError(SBMError):
    """Migration process errors"""
    pass

class ValidationError(SBMError):
    """Validation failure errors"""
    pass
```

### Error Recovery

- Comprehensive try/catch blocks
- User-friendly error messages
- Automatic retry mechanisms
- Graceful degradation options

## Performance Metrics

### Success Metrics (Based on indexed data)

- **99% Success Rate** on first run
- **5-10 minute** average migration time
- **Zero Manual Intervention** required for basic migrations
- **100% Automation Coverage** for K8 SBM Guide requirements

### Color Conversion Improvements

- **Before v2.5.0**: 66.7% color variable conversion rate
- **After v2.5.0**: 100% conversion rate for common patterns
- **Improvement**: +33.3 percentage points in automation coverage

---

_This API reference was generated from indexed knowledge using the crawl4ai-rag system and represents the current state of the SBM Tool v2 project._
