# PRP: Migration Critical Fixes and Improvements

## Executive Summary

Address critical issues in auto-SBM migration workflow including progress bar bugs, compilation failure reporting, header/footer/navigation exclusion requirements, and pydantic validation errors. These issues are preventing successful migrations and creating false positive/negative reports.

## Problem Analysis

### 1. Progress Bar and Timer Issues

- Progress bars showing incorrect states during migration
- Timer bugs causing visual artifacts
- Need total time metric (standalone if complex to integrate)

### 2. False Compilation Failure Reports

- Automation reports failures even when compilation ultimately succeeds
- Disconnect between actual compilation state and reported state
- Manual fixes succeed but system still shows failure

### 3. Critical Migration Requirement Violation

**CRITICAL BUSINESS REQUIREMENT**: Header, footer, and navigation styles MUST NOT be migrated to Site Builder

- Site Builder uses same classes causing conflicts
- Current implementation migrates all styles indiscriminately
- Need filtering mechanism during or after style migration

### 4. Map Component Migration Issues

- Review needed to ensure map components migrate correctly
- May be related to broader component migration logic

### 5. Pydantic Validation Errors in Different Environments

```
wp_debug_display
  Extra inputs are not permitted [type=extra_forbidden, input_value='false', input_type=str]
wp_debug_log
  Extra inputs are not permitted [type=extra_forbidden, input_value='false', input_type=str]
wp_debug
  Extra inputs are not permitted [type=extra_forbidden, input_value='false', input_type=str]
```

- Occurs when running `sbm update` inside di-websites-platform venv
- Need cross-environment compatibility
- Self-update functionality broken

## Context Analysis

### Current Architecture Points of Interest

```
sbm/ui/progress.py - Progress tracking implementation
sbm/core/migration.py - Main migration orchestration
sbm/scss/processor.py - SCSS processing logic
sbm/core/validation.py - Post-migration validation
sbm/config.py - Configuration and pydantic models
```

### Key Requirements

1. **Header/Footer/Nav Exclusion**: Business-critical requirement
2. **Progress System**: Visual feedback during long operations
3. **Compilation Validation**: Accurate success/failure reporting
4. **Cross-Environment**: Works from any directory/venv
5. **Map Components**: Proper component migration

## Implementation Plan

### Pre-Phase: Critical Test System Repair (BLOCKING)

**Priority**: CRITICAL - Must be fixed before any other work
**Issue**: 47 test failures prevent proper validation of changes
**Impact**: Cannot verify implementations are working correctly

#### Critical Test Issues Identified:

1. **Progress System Tests**: 15+ failures in progress tracking logic
   - Task completion tracking broken
   - Step completion logic faulty
   - Thread safety issues
2. **UI Panel Tests**: 20+ failures in Rich UI panel generation
   - Panel content validation broken
   - String representation issues
3. **Configuration Tests**: Pydantic validation errors
   - GitHub token validation too strict
   - Directory validation failing on test paths
4. **Type Safety Tests**: Missing annotations causing failures
   - CLI functions missing return types
   - Progress methods missing annotations

#### Pre-Phase Immediate Actions Required:

```python
# Fix critical progress system issues first
# File: sbm/ui/progress.py - Line ~200
def complete_step(self, step_name: str) -> None:  # Add missing return type
    """Complete a migration step."""
    if step_name not in self.step_tasks:
        logger.error(f"Task {step_name} not found in step_tasks")
        return

    task_id = self.step_tasks[step_name]

    # Fix task completion logic
    try:
        task = self.progress.tasks[task_id]
        # Mark as complete properly
        self.progress.update(task_id, completed=task.total)
        self.progress.update(task_id, visible=False)

        # Remove from tracking and advance migration
        del self.step_tasks[step_name]
        self._advance_migration_progress()

    except (KeyError, IndexError) as e:
        logger.error(f"Task {task_id} not found in progress tracker: {e}")
```

### Phase 0: Environment Validation and Auto-Update System

**Priority**: BLOCKING - Must work before any other fixes
**Validation**: `sbm` commands work from anywhere, auto-update functions correctly
**Prerequisites**: Test system must be repaired first

#### 0.1 End-to-End Current State Test

```bash
# FIRST: Fix test system, THEN run these tests
cd /Users/nathanhart/auto-sbm

# Fix critical test failures
python -m pytest tests/test_ui/test_progress.py -v # Should pass after fixes
python -m pytest tests/test_config_migration.py -v # Should pass after config fixes

# THEN test current jamesriverchryslerdodgejeepram migration
git add . && git commit -m "Pre-test snapshot" && git push
sbm update # Ensure latest version locally

# Test from different locations and venvs
cd /Users/nathanhart/di-websites-platform
source venv/bin/activate
sbm --version # Should work without errors
sbm update    # Should update auto-sbm regardless of current venv

# Clean test from neutral location
cd /tmp
sbm migrate jamesriverchryslerdodgejeepram --dry-run
```

#### 0.2 Auto-Update Integration

```python
# sbm/cli.py - Add auto-update check to main command group
@click.group()
@click.pass_context
def cli(ctx):
    """Auto-SBM migration tool."""
    # Always check for updates on first command in session
    if should_auto_update():
        console.print("[yellow]Checking for auto-sbm updates...[/yellow]")
        try:
            update_result = update_sbm()
            if update_result.updated:
                console.print(f"[green]✅ Updated to version {update_result.new_version}[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠ Update check failed: {e}[/yellow]")

    ctx.ensure_object(dict)
```

#### 0.3 Environment Isolation Fixes

```python
# sbm/config.py - Fix Pydantic model to handle extra inputs
class AutoSBMSettings(BaseSettings):
    """Auto-SBM configuration settings with Pydantic validation."""

    class Config:
        extra = "ignore"  # CRITICAL: Allow extra inputs to prevent cross-env failures
        env_prefix = "SBM_"
        case_sensitive = False

    # Add wp_debug fields to handle di-websites-platform environment variables
    wp_debug: Optional[bool] = Field(None, description="WordPress debug setting (ignored)")
    wp_debug_log: Optional[bool] = Field(None, description="WordPress debug log setting (ignored)")
    wp_debug_display: Optional[bool] = Field(None, description="WordPress debug display setting (ignored)")

# sbm/utils/environment.py - New module for environment handling
class EnvironmentManager:
    """Handle cross-environment compatibility."""

    @staticmethod
    def detect_venv_conflicts():
        """Detect if we're in conflicting venv with old auto-sbm."""
        current_venv = os.environ.get('VIRTUAL_ENV')
        if current_venv and 'di-websites-platform' in current_venv:
            # Check for conflicting installations
            pass

    @staticmethod
    def ensure_clean_environment():
        """Ensure clean environment for auto-sbm execution."""
        pass
```

### Phase 1: Critical Business Requirement - Style Exclusion System

**Priority**: CRITICAL
**Validation**: Verify no header/footer/nav styles in migrated files

#### 1.1 Create Style Classification System

```python
# sbm/scss/classifiers.py
class StyleClassifier:
    """Classify CSS/SCSS rules to determine if they should be migrated."""

    EXCLUDED_PATTERNS = [
        # Header patterns
        r'\.header\b', r'#header\b', r'\.main-header\b',
        r'\.site-header\b', r'\.page-header\b',

        # Navigation patterns
        r'\.nav\b', r'\.navigation\b', r'\.main-nav\b',
        r'\.navbar\b', r'\.menu\b', r'\.primary-menu\b',

        # Footer patterns
        r'\.footer\b', r'#footer\b', r'\.main-footer\b',
        r'\.site-footer\b', r'\.page-footer\b'
    ]

    def should_exclude_rule(self, css_rule: str) -> bool:
        """Return True if rule should be excluded from migration."""
        pass

    def filter_scss_content(self, content: str) -> str:
        """Remove excluded styles from SCSS content."""
        pass
```

#### 1.2 Integration Points

- **Option A**: Filter during initial style extraction
- **Option B**: Filter after SCSS transformation
- **Recommendation**: Option A (cleaner, prevents downstream issues)

#### 1.3 Validation

```bash
# Test command to verify exclusion
sbm validate < theme > --check-exclusions
```

### Phase 2: Progress System Fixes

**Priority**: HIGH
**Validation**: Progress bars display correctly, no visual artifacts

#### 2.1 Progress Bar State Management

```python
# sbm/ui/progress.py improvements
class MigrationProgress:
    def __init__(self):
        self._start_time = None
        self._step_times = {}
        self._current_step = None

    def start_migration(self):
        """Initialize migration timing."""
        self._start_time = time.time()

    def complete_migration(self):
        """Finalize migration and return total time."""
        if self._start_time:
            return time.time() - self._start_time
        return None
```

#### 2.2 Timer Integration

- Add total time tracking to migration workflow
- Display at completion (standalone metric)
- Fix visual artifacts in progress display

### Phase 3: Compilation Status Accuracy

**Priority**: HIGH  
**Validation**: Reported status matches actual compilation state

#### 3.1 Compilation State Tracking

```python
# sbm/core/validation.py improvements
class CompilationValidator:
    def __init__(self):
        self._compilation_history = []
        self._final_state = None

    def track_compilation_attempt(self, attempt: int, success: bool, errors: list):
        """Track each compilation attempt."""
        pass

    def get_final_status(self) -> bool:
        """Return true final compilation status."""
        pass
```

#### 3.2 Status Reporting Fix

- Separate attempt tracking from final status
- Only report final success/failure state
- Clear distinction between retry attempts and final outcome

### Phase 4: Comprehensive Environment Testing

**Priority**: HIGH  
**Validation**: All environment scenarios work correctly

#### 4.1 DI Platform Venv Cleanup

```bash
# Clean di-websites-platform venv of conflicts
cd /Users/nathanhart/di-websites-platform
source venv/bin/activate
pip uninstall auto-sbm -y # Remove any old installations
pip list | grep sbm       # Verify clean
deactivate

# Test sbm accessibility from di venv
source venv/bin/activate
sbm --version # Should work via global installation
sbm update    # Should update global installation
```

#### 4.2 Pydantic Model Fixes

```python
# sbm/config.py - Fix extra inputs issue
class Config(BaseSettings):
    class Config:
        extra = "ignore"  # Allow extra inputs, ignore them
        env_prefix = "SBM_"

    # Add validation for wp_debug fields if needed
    wp_debug: Optional[bool] = None
    wp_debug_log: Optional[bool] = None
    wp_debug_display: Optional[bool] = None
```

#### 4.3 Global Command Isolation

```python
# Ensure sbm command works from anywhere
class SBMEnvironment:
    @staticmethod
    def ensure_global_access():
        """Ensure sbm command accessible globally."""
        import sys
        import subprocess

        # Check if sbm is in PATH
        try:
            result = subprocess.run(['which', 'sbm'], capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError("sbm command not in PATH")
        except Exception:
            # Fallback to direct Python execution
            pass
```

### Phase 5: Map Component Review

**Priority**: MEDIUM
**Validation**: Map components migrate correctly

#### 5.1 Component Migration Audit

- Review `sbm/core/maps.py` implementation
- Ensure map-specific styles handled correctly
- Validate against exclusion system (no nav-related map styles)

## Implementation Details

### File Modifications Required

#### 1. New Files

```
sbm/scss/classifiers.py - Style classification system
sbm/core/timing.py - Migration timing utilities
```

#### 2. Modified Files

```
sbm/scss/processor.py - Add classification filtering
sbm/ui/progress.py - Fix progress bar state management
sbm/core/migration.py - Integrate timing and status tracking
sbm/core/validation.py - Improve compilation status accuracy
sbm/config.py - Fix pydantic extra inputs
sbm/cli.py - Fix update command isolation
sbm/core/maps.py - Review and validate component migration
```

### Testing Strategy

#### 1. Unit Tests

```python
# tests/test_style_classification.py
def test_header_styles_excluded():
    """Verify header styles are properly excluded."""

def test_footer_styles_excluded():
    """Verify footer styles are properly excluded."""

def test_nav_styles_excluded():
    """Verify navigation styles are properly excluded."""

# tests/test_progress_timing.py
def test_progress_state_transitions():
    """Verify progress bars transition correctly."""

def test_total_time_calculation():
    """Verify total migration time calculated correctly."""
```

#### 2. Integration Tests

```python
# tests/test_migration_workflow.py
def test_full_migration_excludes_nav_styles():
    """End-to-end test ensuring nav styles excluded."""

def test_compilation_status_accuracy():
    """Verify reported status matches actual compilation."""
```

#### 3. Environment Tests

```bash
# Test cross-environment compatibility
cd /tmp && sbm update
cd ~/different-venv && sbm migrate test-theme
```

## Validation Gates

### Level 0: Critical Test System Repair (NEW - BLOCKING)

```bash
# FIRST: Repair broken test system
cd /Users/nathanhart/auto-sbm

# Fix critical progress system tests
python -m pytest tests/test_ui/test_progress.py::TestMigrationProgress::test_step_completion -v
# Should PASS after implementing complete_step fix

# Fix critical config tests
python -m pytest tests/test_config_migration.py::TestPydanticConfiguration::test_github_token_validation -v
# Should PASS after implementing config.py extra="ignore" fix

# Fix critical UI panel tests
python -m pytest tests/test_ui/test_panels.py::TestStatusPanels::test_migration_status_panel_basic -v
# Should PASS after fixing panel string representation

# Verify test coverage improves significantly
python -m pytest tests/ --cov=sbm --cov-report=term-missing --cov-fail-under=50
# Should achieve >50% coverage (up from 21% currently)
```

### Level 1: Environment Prerequisites

```bash
# Commit and push current state
cd /Users/nathanhart/auto-sbm
git add . && git commit -m "Pre-implementation snapshot" && git push

# Clean DI platform venv of conflicts
cd /Users/nathanhart/di-websites-platform
source venv/bin/activate
pip uninstall auto-sbm -y 2> /dev/null || true
pip list | grep -i sbm # Should be empty
deactivate

# Update local auto-sbm installation
cd /Users/nathanhart/auto-sbm
sbm update --force # Ensure latest version
```

### Level 2: Environment Compatibility

```bash
# Test from auto-sbm directory
cd /Users/nathanhart/auto-sbm
sbm --version && sbm update

# Test from DI platform directory with venv active
cd /Users/nathanhart/di-websites-platform
source venv/bin/activate
sbm --version # Should work without pydantic errors
sbm update    # Should update global installation
deactivate

# Test from completely neutral location
cd /tmp
sbm --version && sbm update
```

### Level 3: Real Migration Test

```bash
# Test actual jamesriverchryslerdodgejeepram migration from different environments
cd /Users/nathanhart/di-websites-platform
source venv/bin/activate
sbm migrate jamesriverchryslerdodgejeepram --dry-run
deactivate

# Test from neutral location
cd /tmp
sbm migrate jamesriverchryslerdodgejeepram --dry-run

# Full migration test (after fixes implemented)
cd /Users/nathanhart/auto-sbm
sbm migrate jamesriverchryslerdodgejeepram
```

### Level 4: Style Exclusion Validation

```bash
# After implementing style exclusion system
cd /Users/nathanhart/di-websites-platform/dealer-themes/jamesriverchryslerdodgejeepram

# Check for excluded patterns in migrated files
grep -E -i "(\.header|#header|\.footer|#footer|\.nav|\.navigation|\.navbar|\.menu)" sb-*.scss
# Should return NO matches

# Verify essential styles are still present
grep -E "(\.hero|\.content|\.section)" sb-*.scss
# Should return matches (these should be migrated)
```

### Level 5: End-to-End Workflow Validation

```bash
# Complete migration workflow with all fixes
sbm migrate jamesriverchryslerdodgejeepram

# Verify all requirements:
# 1. Auto-update ran at start of session ✓
# 2. No header/footer/nav styles in sb-*.scss files ✓
# 3. Progress displays correctly without artifacts ✓
# 4. Compilation status accurate (success = success, fail = fail) ✓
# 5. Works from any directory/venv ✓
# 6. Total time displayed ✓
# 7. Map components migrate correctly ✓
```

## Success Criteria

### Must Have (Blocking)

- [ ] **Test system repaired: >50% test coverage, critical tests passing**
- [ ] **Header/footer/nav styles completely excluded from migration**
- [ ] **Compilation status reporting accurate (no false failures)**
- [ ] **Cross-environment compatibility (works from any directory/venv)**
- [ ] **Self-update functionality works**

### Should Have (Important)

- [ ] Progress bars display without artifacts
- [ ] Total migration time displayed
- [ ] Map component migration verified correct

### Nice to Have (Enhancement)

- [ ] Progress system fully integrated with timing
- [ ] Enhanced visual feedback during migration

## Quality Gates for 100% Readiness

### Code Quality Gates

1. **Test Coverage**: Minimum 50% (currently 21%)
2. **Critical Test Passage**: All progress, config, and UI tests pass
3. **Linting**: Maximum 10 ruff violations (currently 139)
4. **Type Safety**: All public functions properly typed

### Functional Quality Gates

1. **Cross-Environment**: Works from auto-sbm, di-websites-platform, and /tmp
2. **Auto-Update**: Functions correctly regardless of current directory
3. **Business Logic**: Header/footer/nav styles completely excluded
4. **Status Accuracy**: Compilation success/failure reported correctly

### Documentation Quality Gates

1. **Implementation Steps**: Each phase has clear, actionable steps
2. **Validation Commands**: Every requirement has testable validation
3. **Error Recovery**: Known failure modes documented with fixes
4. **Timeline Realism**: Timeline accounts for test system repair

## Risk Analysis

### High Risk

- **Style exclusion implementation**: Complex regex/parsing logic
- **Progress system refactor**: Rich UI integration complexity

### Medium Risk

- **Compilation status tracking**: Async Docker operations
- **Cross-environment testing**: Many edge cases

### Low Risk

- **Map component review**: Likely working correctly
- **Pydantic model fixes**: Well-understood issue

## Dependencies

### External Dependencies

- Rich UI framework (progress bars)
- Docker Gulp compilation system
- Pydantic validation framework

### Internal Dependencies

- SCSS processing pipeline
- Git workflow system
- Configuration management

## Implementation Timeline

### Day 0: Critical Test System Repair (NEW - BLOCKING)

- Fix 47 failing tests preventing proper validation
- Repair progress system task completion logic
- Fix Pydantic config model to handle extra inputs
- Address UI panel string representation issues
- Get test coverage above 50% threshold
- **Deliverable**: All critical test suites passing

### Day 1: Environment Validation and Cleanup

- Execute Level 0-1 validation gates
- Clean DI platform venv conflicts
- Test current state with jamesriverchryslerdodgejeepram
- Document all current issues
- **Deliverable**: Cross-environment functionality confirmed

### Day 2-3: Auto-Update and Environment Isolation

- Implement auto-update on first command
- Complete Pydantic model extra inputs fix
- Ensure global command accessibility
- Test cross-environment compatibility
- **Deliverable**: Tool works from any environment

### Day 4-5: Style Exclusion System (Critical)

- Implement StyleClassifier with header/footer/nav patterns
- Integrate filtering into SCSS processor
- Test exclusion with jamesriverchryslerdodgejeepram
- Validate no excluded styles in output
- **Deliverable**: Business requirement satisfied

### Day 6-7: Progress and Status Accuracy

- Complete progress bar state management fixes
- Improve compilation status tracking
- Add total time metrics
- Test with real migration workflow
- **Deliverable**: Accurate progress and status reporting

### Day 8: Final Validation

- Execute all validation levels 0-5
- Full jamesriverchryslerdodgejeepram migration test
- Document results and any remaining issues
- **Deliverable**: Complete, working system

## Context for AI Implementation

### Architecture Understanding Required

- Rich UI progress system integration
- SCSS processing pipeline flow
- Docker Gulp compilation workflow
- Pydantic model validation system

### Business Logic Critical Points

- **Header/footer/nav exclusion is business-critical**
- **Compilation success/failure must be accurately reported**
- **Tool must work cross-environment**

### Implementation Approach

1. **Start with style exclusion** (highest business impact)
2. **Fix status reporting** (user experience critical)
3. **Address environment issues** (deployment critical)
4. **Polish progress system** (nice-to-have)

### Testing Philosophy

- Unit tests for classification logic
- Integration tests for workflow
- Environment tests for compatibility
- End-to-end validation of business requirements

This PRP addresses all identified issues with clear priorities, validation gates, and implementation guidance while maintaining the existing architecture and Rich UI integration.

## APPENDIX A: Critical Test Fixes Required for 100% Readiness

### A.1 Progress System Test Fixes (15+ failing tests)

```python
# File: sbm/ui/progress.py
# Issue: Task completion tracking broken, step completion logic faulty

def complete_step(self, step_name: str) -> None:
    """Complete a migration step and advance migration progress."""
    if step_name not in self.step_tasks:
        logger.warning(f"Task {step_name} not found in step_tasks")
        return

    task_id = self.step_tasks[step_name]

    try:
        # Mark task as complete and hide it
        task = self.progress.tasks[task_id]
        self.progress.update(task_id, completed=task.total, visible=False)

        # Remove from tracking
        del self.step_tasks[step_name]

        # Advance migration progress
        if hasattr(self, 'migration_task_id') and self.migration_task_id is not None:
            migration_task = self.progress.tasks[self.migration_task_id]
            new_completed = migration_task.completed + 1
            self.progress.update(self.migration_task_id, completed=new_completed)

    except (KeyError, IndexError) as e:
        logger.error(f"Task {task_id} not found in progress tracker: {e}")

def update_step_progress(self, step_name: str, completed: int, description: str = None) -> None:
    """Update progress for a specific step."""
    if step_name not in self.step_tasks:
        logger.warning(f"Task {step_name} for step {step_name} no longer exists")
        return

    task_id = self.step_tasks[step_name]

    try:
        # Update progress
        self.progress.update(task_id, completed=completed)

        # Update description if provided
        if description:
            self.progress.update(task_id, description=f"[progress]{description}[/]")

    except (KeyError, IndexError):
        logger.warning(f"Task {task_id} for step {step_name} no longer exists")
```

### A.2 Pydantic Configuration Test Fixes (3+ failing tests)

```python
# File: sbm/config.py
# Issue: Extra inputs validation too strict, GitHub token validation errors

class AutoSBMSettings(BaseSettings):
    """Auto-SBM configuration settings."""

    model_config = SettingsConfigDict(
        extra="ignore",  # CRITICAL: Allow extra inputs
        env_prefix="SBM_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8"
    )

    # Add WordPress debug fields to prevent validation errors
    wp_debug: Optional[bool] = Field(None, exclude=True)
    wp_debug_log: Optional[bool] = Field(None, exclude=True)
    wp_debug_display: Optional[bool] = Field(None, exclude=True)

class GitSettings(BaseSettings):
    """Git-related settings."""

    model_config = SettingsConfigDict(extra="ignore")

    @field_validator('github_token')
    @classmethod
    def validate_github_token(cls, v: Optional[str]) -> Optional[str]:
        """Validate GitHub token format and content."""
        if v is None or v == "":
            return v

        # Check for placeholder value
        if v == "your_github_personal_access_token_here":
            raise ValueError("GitHub token cannot be the placeholder value")

        # Relaxed validation - just check if it looks like a token
        if len(v) < 10:
            raise ValueError("GitHub token appears too short to be valid")

        return v
```

### A.3 UI Panel Test Fixes (20+ failing tests)

```python
# File: sbm/ui/panels.py
# Issue: Panel string representation tests failing

@staticmethod
def create_migration_status_panel(
    theme_name: str,
    stage: str,
    status: str,
    additional_info: Optional[Dict[str, Any]] = None
) -> Panel:
    """Create a migration status panel with proper content rendering."""

    # Status emoji mapping
    status_emojis = {
        "in_progress": "🔄",
        "completed": "✅",
        "failed": "❌",
        "warning": "⚠️"
    }

    emoji = status_emojis.get(status, "ℹ️")

    # Build content with proper escaping
    content_lines = [
        f"Theme: [bold]{theme_name}[/bold]",
        f"Stage: {stage}",
        f"Status: {emoji} {status.replace('_', ' ').title()}"
    ]

    if additional_info:
        content_lines.append("")
        for key, value in additional_info.items():
            content_lines.append(f"{key}: {value}")

    content = "\n".join(content_lines)

    # Create panel with proper title and border
    return Panel(
        content,
        title=f"[bold cyan]Migration Status[/bold cyan]",
        border_style="blue",
        padding=(1, 2)
    )
```

### A.4 CLI Type Annotation Fixes (10+ failing tests)

```python
# File: sbm/cli.py
# Issue: Missing return type annotations on public functions

def is_env_healthy() -> bool:  # Add missing return type
    """Check if the environment has all required tools and packages."""
    # ... existing implementation

def auto_update_repo() -> None:  # Add missing return type
    """Automatically pull the latest changes from the auto-sbm repository."""
    # ... existing implementation

def test_compilation(theme_name: str) -> None:  # Add missing return type
    """Test compilation error handling on an existing theme."""
    # ... existing implementation

def post_migrate(
    theme_name: str,
    skip_git: bool,
    create_pr: bool,
    skip_review: bool,
    skip_git_prompt: bool,
    skip_pr_prompt: bool
) -> None:  # Add missing return type
    """Run post-migration steps for a given theme."""
    # ... existing implementation
```

These fixes address the core test failures that prevent proper validation of the PRP implementation. Once these are applied, the test coverage should improve significantly and the validation gates can be properly executed.
