# Essential Tests Needed for Auto-SBM

**Date:** July 25, 2025  
**Context:** After cleanup of old config tests and analysis of current test failures  
**Goal:** Define mandatory core functionality tests only - ensure nothing is broken  

## Current Test Status Summary

### ✅ **Tests Working (Keep):**
- **Type Safety Tests** (14 tests) - All passing ✅
- **Console Tests** (13 tests) - All passing ✅  
- **Basic Progress Tests** (9 tests) - Mostly passing ✅

### ❌ **Tests Broken (Need Fixing or Replacement):**
- **UI Panel Tests** (13 failed) - Testing Rich UI internals incorrectly
- **Progress Task Tests** (5 failed) - Wrong assertions about Rich task IDs
- **Coverage at 20%** - Below 50% requirement

## Essential Tests We Actually Need

### 🔴 **CRITICAL CORE TESTS (Must Have)**

#### 1. **Config Loading & Validation**
**File:** `tests/test_core_config.py`
**What it tests:**
- Config loads from environment variables
- Required fields (github_token, github_org) are validated  
- Default values work correctly
- Pydantic validation catches invalid values

```python
def test_config_loads_from_env():
    """Test config loads required fields from environment."""
    
def test_config_validates_github_token():
    """Test config requires valid GitHub token."""
    
def test_config_default_values():
    """Test config provides sensible defaults."""
    
def test_config_pydantic_validation():
    """Test Pydantic catches invalid configuration."""
```

#### 2. **CLI Command Registration**
**File:** `tests/test_core_cli.py`
**What it tests:**
- All CLI commands are registered and callable
- Help text works for each command
- CLI doesn't crash on invalid input
- Basic argument parsing works

```python
def test_cli_commands_registered():
    """Test all expected CLI commands are available."""
    
def test_cli_help_works():
    """Test --help works for main command and subcommands."""
    
def test_cli_handles_invalid_arguments():
    """Test CLI gracefully handles bad input."""
    
def test_cli_version_command():
    """Test version command returns expected format."""
```

#### 3. **Path Utilities**
**File:** `tests/test_core_paths.py`
**What it tests:**
- Path discovery functions work
- Directory validation functions
- Platform directory detection
- Theme directory resolution

```python
def test_get_platform_dir():
    """Test platform directory discovery."""
    
def test_get_dealer_theme_dir():
    """Test theme directory resolution."""
    
def test_path_validation_functions():
    """Test path validation utilities."""
    
def test_path_security():
    """Test paths don't allow traversal attacks."""
```

#### 4. **File Operations**
**File:** `tests/test_core_file_ops.py`
**What it tests:**
- File reading/writing works safely
- Directory creation works
- File backup/restore functions
- Error handling for permission issues

```python
def test_safe_file_operations():
    """Test file read/write operations work safely."""
    
def test_directory_creation():
    """Test directory creation functions."""
    
def test_file_permission_handling():
    """Test graceful handling of permission errors."""
    
def test_file_backup_restore():
    """Test file backup and restore functionality."""
```

### 🟡 **IMPORTANT FEATURE TESTS (Should Have)**

#### 5. **Git Operations Basic**
**File:** `tests/test_core_git.py`
**What it tests:**
- Git repository detection
- Basic git commands work
- Branch creation/switching
- Commit creation (basic)

```python
def test_git_repo_detection():
    """Test Git repository detection works."""
    
def test_git_branch_operations():
    """Test basic Git branch operations."""
    
def test_git_commit_creation():
    """Test Git commit creation functionality."""
    
def test_git_error_handling():
    """Test Git error handling and recovery."""
```

#### 6. **SCSS Processing Core**
**File:** `tests/test_core_scss.py`
**What it tests:**
- SCSS file reading
- Basic SCSS parsing doesn't crash
- Variable extraction works
- Output file generation

```python
def test_scss_file_reading():
    """Test SCSS files can be read and parsed."""
    
def test_scss_variable_extraction():
    """Test SCSS variable extraction functionality."""
    
def test_scss_output_generation():
    """Test SCSS output file generation."""
    
def test_scss_error_handling():
    """Test SCSS processing error handling."""
```

### 🟢 **INTEGRATION TESTS (Nice to Have)**

#### 7. **Setup Script Validation**
**File:** `tests/test_integration_setup.py`
**What it tests:**
- Setup script completes without errors
- Required directories are created
- Virtual environment works
- Global command is available

```python
def test_setup_script_completion():
    """Test setup script runs to completion."""
    
def test_setup_creates_venv():
    """Test setup creates working virtual environment."""
    
def test_setup_creates_global_command():
    """Test setup creates functional global sbm command."""
    
def test_setup_dependency_installation():
    """Test setup installs required dependencies."""
```

#### 8. **Environment Health Check**
**File:** `tests/test_integration_health.py`
**What it tests:**
- All required tools are available
- Permissions are correct
- Network connectivity for GitHub
- Basic end-to-end functionality

```python
def test_required_tools_available():
    """Test required external tools are available."""
    
def test_github_connectivity():
    """Test GitHub API connectivity."""
    
def test_file_permissions():
    """Test file system permissions are correct."""
    
def test_basic_end_to_end():
    """Test basic migration flow doesn't crash."""
```

## Test Implementation Priority

### Week 1: Critical Core Tests
1. **Config Loading** - Ensures configuration system works
2. **CLI Registration** - Ensures commands are available  
3. **Path Utilities** - Ensures file operations are safe
4. **File Operations** - Ensures basic I/O works

### Week 2: Feature Tests  
5. **Git Operations** - Ensures Git integration works
6. **SCSS Processing** - Ensures core transformation works

### Week 3: Integration Tests
7. **Setup Validation** - Ensures deployment works
8. **Health Checks** - Ensures production readiness

## Test Coverage Goals

### Immediate (After Week 1):
- **Target:** 40% coverage minimum
- **Focus:** Core configuration, CLI, and file operations
- **Success:** No crashes on basic operations

### Short-term (After Week 2):
- **Target:** 60% coverage 
- **Focus:** Git and SCSS processing functionality
- **Success:** Core features work reliably

### Long-term (After Week 3):
- **Target:** 75% coverage
- **Focus:** Integration and edge cases
- **Success:** Production-ready reliability

## What NOT to Test

### ❌ **Don't Test These (Low Priority):**
1. **Rich UI Internals** - Too fragile, changes frequently
2. **External Tool Outputs** - git, gh CLI specifics
3. **Performance Benchmarks** - Not critical for functionality
4. **Edge Case UI Formatting** - Rich handles this
5. **Detailed SCSS Transformation** - Too complex for core tests

### ❌ **Don't Test Rich UI Objects:**
The current failing tests are testing Rich UI object internals:
```python
# BAD - Testing Rich internal representation
assert "✅" in str(panel)  # This fails because str(Panel) != rendered output

# GOOD - Test functional behavior instead  
assert panel is not None
assert isinstance(panel, Panel)
assert panel.title == expected_title
```

## Test Writing Guidelines

### ✅ **DO Test:**
- **Function return values** - Does the function return what it should?
- **Error handling** - Does it fail gracefully on bad input?
- **File system effects** - Are files created/modified correctly?
- **Basic integration** - Do components work together?

### ❌ **DON'T Test:**
- **UI rendering details** - Rich handles this internally
- **External tool internals** - We don't control git/gh behavior  
- **Performance specifics** - Focus on functionality first
- **Implementation details** - Test behavior, not implementation

## Success Criteria

### ✅ **Tests Pass When:**
1. **Config loads without errors** from environment
2. **CLI commands are callable** and don't crash
3. **File operations work** and handle errors gracefully
4. **Path functions return valid paths** and prevent traversal
5. **Git operations don't crash** on basic commands
6. **SCSS processing doesn't crash** on valid input

### ✅ **Production Ready When:**
- **50%+ test coverage** achieved
- **All core tests pass** consistently
- **Setup script validation** passes
- **No undefined names** (F821 errors) remain
- **Basic migration flow** works end-to-end

---

**Next Steps:**
1. **Remove broken UI tests** - They test Rich internals incorrectly
2. **Implement core config tests** - Essential for reliability  
3. **Add CLI command tests** - Ensure commands are registered
4. **Add path security tests** - Critical for security
5. **Add file operation tests** - Essential for functionality
