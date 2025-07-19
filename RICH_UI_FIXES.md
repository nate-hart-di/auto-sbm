# Rich UI CLI Enhancement Fixes

## Issues Addressed

### 1. Docker Output "Seizure" 🚫📺
**Problem**: Verbose Docker output during `just start` was causing visual chaos and interfering with Rich UI progress bars.

**Solution**: 
- Enhanced `execute_interactive_command()` with `suppress_output` parameter
- Added intelligent authentication prompt detection that switches to interactive mode when needed
- Default behavior now suppresses Docker container build output while maintaining auth prompts

### 2. Map Migration Hanging ⏸️
**Problem**: `click.confirm()` prompts in map migration were hanging the CLI when running in Rich UI context.

**Solution**:
- Added `interactive` parameter to map migration functions
- Non-interactive mode automatically handles missing partials without prompts
- Interactive mode preserved for manual debugging when needed

### 3. Rich UI Progress Interference 🔄
**Problem**: Raw command output was interfering with Rich progress bars and status displays.

**Solution**:
- Integrated progress tracking with suppressed command execution
- Added indeterminate progress tasks for Docker operations
- Clean progress completion with proper status messages

## New Features

### Enhanced Command Execution (`sbm/utils/command.py`)

```python
def execute_interactive_command(
    command, 
    error_message="Command failed", 
    cwd=None, 
    suppress_output=False, 
    progress_tracker=None, 
    task_id=None
):
    # Intelligent output suppression with auth detection
    # Progress integration for Rich UI
    # Cross-platform compatibility (Unix/Windows)
```

### Verbose Docker Option

New CLI flag: `--verbose-docker`
```bash
sbm auto theme-name --verbose-docker  # For debugging Docker issues
sbm auto theme-name                   # Clean UI (default)
```

### Non-Interactive Map Migration

```python
migrate_map_components(slug, oem_handler, interactive=False)
# Automatically handles missing partials without user prompts
```

## Benefits

1. **🎯 Clean UI Experience**: No more Docker output "seizure" during startup
2. **🔧 Debugging Support**: `--verbose-docker` flag when you need to see everything
3. **⚡ No Hanging**: Map migration runs without interactive prompts by default
4. **🔐 Smart Auth**: Automatically detects and switches to interactive mode for AWS/auth prompts
5. **📊 Better Progress**: Rich UI progress bars work cleanly with command execution
6. **🌐 Cross-Platform**: Works on both Unix and Windows systems

## Usage Examples

### Standard Clean Migration
```bash
sbm auto dealer-theme-name
# Clean Rich UI with suppressed Docker output
```

### Debug Mode with Full Output
```bash
sbm auto dealer-theme-name --verbose-docker
# Shows all Docker container build output for debugging
```

### Interactive Map Migration (Manual Mode)
```python
# For manual debugging/review
migrate_map_components(slug, oem_handler, interactive=True)
```

## Technical Implementation

### 1. Command Execution Enhancement
- **Output Suppression**: Captures stdout/stderr when suppress_output=True
- **Progress Integration**: Updates Rich progress bars during long-running commands
- **Auth Detection**: Monitors output for authentication keywords and switches modes
- **Error Handling**: Proper cleanup and error reporting

### 2. Rich UI Integration  
- **Indeterminate Tasks**: Used for Docker startup (unknown duration)
- **Progress Context**: Proper setup/teardown of Rich UI components
- **Status Updates**: Real-time status messages during suppressed operations

### 3. Non-Interactive Defaults
- **Map Migration**: Skips missing partials automatically
- **CLI Commands**: Non-interactive by default for automation
- **Manual Override**: Interactive flags available when needed

## Files Modified

1. **`sbm/utils/command.py`**: Enhanced command execution with suppression
2. **`sbm/core/migration.py`**: Updated Docker startup with progress integration
3. **`sbm/core/maps.py`**: Non-interactive map migration by default
4. **`sbm/cli.py`**: Added `--verbose-docker` option

## Backward Compatibility

- ✅ All existing commands work unchanged
- ✅ Interactive mode still available via flags
- ✅ Debug mode accessible via `--verbose-docker`
- ✅ No breaking changes to existing workflows

## AWS Authentication Support

The enhanced command execution automatically detects AWS/authentication prompts:
- Monitors for keywords: 'password', 'login', 'credentials', 'aws', 'mfa'
- Automatically switches to interactive mode when detected
- User sees clean UI until auth is needed, then seamless transition

This ensures AWS login prompts work correctly while maintaining clean UI for normal operations.