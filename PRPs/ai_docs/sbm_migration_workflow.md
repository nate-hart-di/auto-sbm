# SBM Migration Workflow Documentation

## Complete Migration Process Overview

The SBM (Site Builder Migration) tool performs a comprehensive 6-step migration process to convert dealer themes from legacy format to Site Builder format.

## Core Migration Steps

### 1. Git Operations (`sbm/core/git.py`)
- **Function**: `setup_git_branch()`
- **Purpose**: Create and switch to migration branch
- **Branch Pattern**: `{theme_name}-sbm{date}`
- **Rich Opportunities**: Branch creation status, git operation progress

### 2. Docker Environment Setup (`sbm/core/migration.py`)
- **Function**: `run_just_start()`
- **Purpose**: Start Docker containers for compilation testing
- **Interactive Elements**: AWS SSO login, password prompts
- **Rich Opportunities**: Container status, authentication flow UI

### 3. Site Builder File Creation (`sbm/core/migration.py`)
- **Function**: `create_sb_files()`
- **Purpose**: Create initial SCSS files (sb-inside.scss, sb-vdp.scss, etc.)
- **Rich Opportunities**: File creation progress, file status table

### 4. SCSS Style Migration (`sbm/scss/processor.py`)
- **Function**: `migrate_styles()`
- **Purpose**: Transform legacy SCSS to Site Builder format
- **Rich Opportunities**: File processing progress, transformation previews

### 5. Predetermined Styles Addition (`sbm/core/migration.py`)
- **Function**: `add_predetermined_styles()`
- **Purpose**: Add OEM-specific styles based on dealer
- **Rich Opportunities**: OEM detection display, style addition status

### 6. Map Components Migration (`sbm/core/migration.py`)
- **Function**: `migrate_map_components()`
- **Purpose**: Migrate map-related components if present
- **Rich Opportunities**: Component discovery, file copying progress

## Manual Review Phase

### Interactive Review Process
- **Location**: Lines 357-366 in `sbm/cli.py`
- **Current Pattern**: Plain text separators and file paths
- **Rich Enhancement**: Interactive file browser, diff viewer, status panels

### Post-Review Validation
- **Function**: `reprocess_manual_changes()`
- **Purpose**: Validate and fix manual changes
- **Rich Opportunities**: Reprocessing progress, before/after comparison

## Compilation Verification

### Docker Gulp Monitoring
- **Function**: `_verify_scss_compilation_with_docker()`
- **Purpose**: Test SCSS compilation in Docker environment
- **Rich Opportunities**: Real-time log monitoring, compilation status

### Error Recovery System
- **Function**: `_handle_compilation_with_error_recovery()`
- **Purpose**: Automatically fix compilation errors
- **Rich Opportunities**: Error analysis panels, fix application progress

## Git Operations and PR Creation

### Change Analysis
- **Function**: `_analyze_migration_changes()`
- **Purpose**: Analyze git changes and generate PR content
- **Rich Opportunities**: Change summary tables, diff visualization

### PR Creation
- **Function**: `create_pr()`
- **Purpose**: Create GitHub pull request
- **Rich Opportunities**: PR creation progress, content preview

## Key Functions Requiring Rich Enhancement

### High Priority Enhancement Points

1. **Migration Progress Tracking**
   - Function: `migrate_dealer_theme()` in `sbm/core/migration.py`
   - Current: Basic logger messages
   - Enhancement: Multi-step progress bars with step indicators

2. **Docker Log Monitoring**
   - Function: `_verify_scss_compilation_with_docker()`
   - Current: subprocess.run() with basic output
   - Enhancement: Real-time log streaming with syntax highlighting

3. **Error Recovery Display**
   - Function: `_handle_compilation_with_error_recovery()`
   - Current: Basic click.echo() messages
   - Enhancement: Interactive error panels with recovery options

4. **Manual Review Interface**
   - Function: Manual review prompts in `cli.py`
   - Current: Text separators and basic prompts
   - Enhancement: Interactive file browser with status indicators

5. **File Processing Status**
   - Function: `transform_scss_content()` in `sbm/scss/processor.py`
   - Current: Logger messages with line counts
   - Enhancement: Progress bars with file transformation previews

## Current Output Patterns

### Status Messages
- **Pattern**: `click.echo(f"✅ {message}")`
- **Enhancement**: Rich panels with structured information

### Progress Indicators
- **Pattern**: `time.sleep()` with manual status updates
- **Enhancement**: Real-time progress bars with spinners

### Error Displays
- **Pattern**: Plain text with separator lines
- **Enhancement**: Syntax-highlighted error panels

### User Confirmations
- **Pattern**: `click.confirm()` with basic text
- **Enhancement**: Rich prompts with context panels

## Configuration Integration

### Current Config Structure
```json
{
  "migration": {
    "cleanup_snapshots": true,
    "create_backups": true
  }
}
```

### Rich Configuration Additions
```json
{
  "ui": {
    "use_rich": true,
    "show_progress": true,
    "theme": "default",
    "compact_mode": false
  }
}
```

## Testing Considerations

### Current Testing Pattern
- **Location**: No comprehensive CLI testing
- **Enhancement**: Rich-aware testing with console capture

### Rich Testing Requirements
- Console output capture with StringIO
- Progress bar testing with mock time
- Interactive prompt testing with mock input
- Error display testing with exception simulation

## Performance Considerations

### Long-Running Operations
- Docker container startup (30-60 seconds)
- SCSS compilation cycles (5-10 seconds per file)
- Git operations (variable based on repository size)
- Network operations (AWS SSO, GitHub PR creation)

### Rich Performance Optimization
- Use transient progress bars for terminal performance
- Implement buffered output for large logs
- Use live updates for real-time monitoring
- Implement graceful degradation for unsupported terminals

## Environment Integration

### CI/CD Considerations
- Rich automatically detects CI environments
- Provides plain text fallbacks when needed
- Respects NO_COLOR environment variable
- Maintains compatibility with existing logging

### Terminal Compatibility
- Works with all major terminal emulators
- Gracefully degrades on unsupported terminals
- Maintains accessibility with screen readers
- Supports both light and dark terminal themes