name: "Migration Log Visibility and UI Enhancement PRP"
description: |

## Purpose

Comprehensive enhancement of migration log output, progress visibility, Rich UI formatting, and documentation consistency to provide users with complete migration visibility and eliminate hanging issues.

## Core Principles

1. **Complete Visibility**: Users see every step of migration from start to finish
2. **Rich UI Excellence**: Professional, colorful output without hanging issues  
3. **CI/CD Compatibility**: Graceful fallback for automated environments
4. **Documentation Accuracy**: All docs match current implementation

---

## Goal

Transform the migration log output from current state with visibility gaps and hanging issues to a polished, comprehensive progress tracking system that shows every migration step with enhanced formatting and resolves all documentation inconsistencies.

## Why

- **User Experience**: Users currently lose visibility during Docker startup (1-2 minute gaps) and AWS authentication
- **Hanging Issues**: Rich progress bars are disabled due to CLI hangs, degrading UX
- **Professional Polish**: Current output lacks the visual appeal expected from a production tool
- **Documentation Trust**: Multiple version/dependency conflicts undermine user confidence
- **Integration Clarity**: Full migration visibility enables better debugging and monitoring

## What

### User-Visible Behavior Changes

1. **Complete Migration Visibility**
   - Real-time Docker startup progress with container status updates
   - AWS authentication flow integration with Rich UI
   - No more silent periods during long-running operations

2. **Enhanced Rich UI Output**
   - Vibrant color scheme matching auto-sbm branding
   - Fixed progress bars that don't hang CLI
   - Professional status panels and completion summaries
   - Interactive prompts with proper context displays

3. **Documentation Consistency**
   - Version alignment across all configuration files
   - Updated README with accurate feature descriptions
   - Corrected CLI examples and setup instructions

### Technical Requirements

1. **Progress System Fixes**
   - Resolve Rich progress bar hanging issues
   - Implement non-blocking progress tracking for subprocess operations
   - Add periodic status updates during Docker operations

2. **Output Formatting**
   - Enhanced color palette and theming
   - Consistent branding across all UI components
   - Improved error displays with recovery guidance

3. **Documentation Updates**
   - Resolve v1.0 vs v2.0 architecture conflicts
   - Fix version inconsistencies in pyproject.toml, setup.py, __init__.py
   - Update test coverage claims and dependency specifications

### Success Criteria

- [ ] Full migration visibility from start to finish with no gaps longer than 10 seconds
- [ ] Rich progress bars work without hanging CLI
- [ ] Enhanced color scheme and formatting throughout migration output
- [ ] Documentation 100% accurate to current implementation
- [ ] All version conflicts resolved across configuration files
- [ ] Test coverage documentation matches actual coverage

## All Needed Context

### Documentation & References

```yaml
# MUST READ - Include these in your context window
- url: https://rich.readthedocs.io/en/stable/progress.html
  why: Progress tracking without hanging, threading patterns
  
- url: https://github.com/Textualize/rich/issues/189
  why: Known AsyncIO progress tracking issues and solutions

- url: https://github.com/Textualize/rich/issues/2046  
  why: Rich Handler deadlock issue - critical for subprocess integration

- file: /Users/nathanhart/auto-sbm/sbm/ui/progress.py
  why: Current MigrationProgress implementation patterns to preserve

- file: /Users/nathanhart/auto-sbm/sbm/cli.py:480-481
  why: Current hang workaround - progress_tracker=None comment

- file: /Users/nathanhart/auto-sbm/sbm/core/migration.py:98-165
  why: Docker startup visibility gap in run_just_start function

- file: /Users/nathanhart/auto-sbm/sbm/ui/simple_rich.py
  why: Current simplified Rich implementation to enhance

- docfile: /Users/nathanhart/auto-sbm/PRPs/ai_docs/rich_cli_patterns.md
  why: Established Rich UI patterns and best practices for this codebase

- file: /Users/nathanhart/auto-sbm/tests/test_ui/test_progress.py
  why: Testing patterns for Rich UI components with StringIO capture
```

### Current Codebase Tree

```bash
auto-sbm/
├── sbm/                      # Legacy v1.0 structure (ACTIVE)
│   ├── ui/
│   │   ├── console.py        # SBMConsole with theming
│   │   ├── progress.py       # MigrationProgress (currently unused due to hangs)
│   │   ├── simple_rich.py    # Simplified Rich UI (currently used)
│   │   └── panels.py         # Rich status panels
│   ├── core/
│   │   ├── migration.py      # Main migration logic with visibility gaps
│   │   └── git.py           # Git operations
│   └── cli.py               # CLI entry point with hang workarounds
├── src/auto_sbm/            # New v2.0 structure (INCOMPLETE)
│   ├── features/
│   │   ├── migration/       # New migration service (not integrated)
│   │   └── scss_processing/ # New SCSS processing
│   └── shared/ui/           # New UI components (not used)
├── pyproject.toml           # Points to v1.0 but claims v2.0
├── setup.py                 # Points to v1.0 with v1.0 version
└── README.md                # Documents v2.0 but v1.0 is active
```

### Desired Codebase Tree with Enhanced Components

```bash
auto-sbm/
├── sbm/                      # Enhanced v1.0 structure (stabilized)
│   ├── ui/
│   │   ├── console.py        # Enhanced SBMConsole with new theme
│   │   ├── progress.py       # Fixed MigrationProgress (no hangs)
│   │   ├── panels.py         # Enhanced panels with Docker/AWS status
│   │   └── subprocess_ui.py  # NEW: Subprocess progress tracking
│   ├── core/
│   │   ├── migration.py      # Enhanced with real-time Docker monitoring
│   │   └── docker_monitor.py # NEW: Docker container status tracking
│   └── cli.py               # Restored progress tracking functionality
├── tests/
│   ├── test_ui/             # Enhanced UI testing with subprocess mocking
│   └── test_integration/    # Full migration visibility testing
├── pyproject.toml           # Corrected v1.0 references and dependencies
├── setup.py                 # Version consistency with pyproject.toml
└── README.md                # Accurate v1.0 documentation
```

### Known Gotchas & Library Quirks

```python
# CRITICAL: Rich Progress + subprocess hangs CLI
# Current workaround in cli.py:480: progress_tracker=None  
# Root cause: Progress.track() blocks on subprocess.run() in migration.py:139

# CRITICAL: Docker container startup takes 1-2 minutes with no output
# Location: migration.py:105 suppress_output=True
# User Experience: Silent gap from 08:25:42 → 08:27:18 in logs

# CRITICAL: AWS authentication prompts interfere with Rich UI
# Location: migration.py:122-137 AWS login process
# Issue: Interactive prompts not properly integrated with progress tracking

# GOTCHA: Multiple Rich console instances cause formatting conflicts
# Pattern: Use get_console() singleton from sbm/ui/console.py consistently

# GOTCHA: Rich auto-detection fails in some CI environments
# Solution: Explicit force_terminal=False in CI via environment detection

# GOTCHA: Version conflicts between package files
# pyproject.toml version="2.0.0" but points to sbm.cli (v1.0 structure)
# setup.py version="1.0.0" but should match pyproject.toml
# sbm/__init__.py version="1.0.0" vs src/auto_sbm/__init__.py version="2.0.0"
```

## Implementation Blueprint

### Data Models and Structure

Enhanced UI state management and progress tracking models:

```python
# Enhanced progress tracking without hanging
@dataclass
class EnhancedMigrationProgress:
    """Non-blocking migration progress tracker with subprocess integration"""
    step: int
    total_steps: int
    current_operation: str
    subprocess_status: Optional[str] = None
    docker_containers: List[str] = field(default_factory=list)
    aws_auth_stage: Optional[str] = None
    
# Docker monitoring state
@dataclass  
class DockerStatus:
    """Real-time Docker container status"""
    containers: Dict[str, str]  # name -> status
    logs_tail: List[str]
    startup_stage: str  # 'init', 'starting', 'ready'
    
# Enhanced Rich theme
class SBMTheme:
    """Enhanced color theme for auto-sbm"""
    primary: str = "bold blue"
    success: str = "bold green" 
    warning: str = "bold yellow"
    error: str = "bold red"
    progress: str = "cyan"
    docker: str = "bright_blue"
    aws: str = "magenta"
```

### List of Tasks to be Completed (In Order)

```yaml
Task 1 - Fix Rich Progress Hanging:
MODIFY sbm/ui/progress.py:
  - FIND: "class MigrationProgress" 
  - ADD: Non-blocking subprocess integration methods
  - PRESERVE: Existing context manager patterns from tests
  - IMPLEMENT: Background thread for progress updates

Task 2 - Docker Startup Visibility:
MODIFY sbm/core/migration.py:
  - FIND: "def run_just_start" function (line 98)
  - REPLACE: suppress_output=True with progress monitoring
  - ADD: Docker container status checking
  - PRESERVE: Error handling and timeout logic

Task 3 - Enhanced Rich Theme:
MODIFY sbm/ui/console.py:
  - FIND: "class SBMConsole"
  - ENHANCE: Color palette with auto-sbm branding
  - ADD: Docker and AWS specific styling
  - PRESERVE: CI detection and fallback patterns

Task 4 - AWS Authentication Integration:
MODIFY sbm/core/migration.py:
  - FIND: AWS login section (lines 122-137)
  - INTEGRATE: AWS prompts with Rich UI progress
  - ADD: Authentication stage tracking
  - PRESERVE: Interactive prompt functionality

Task 5 - Subprocess Progress Wrapper:
CREATE sbm/ui/subprocess_ui.py:
  - PATTERN: Mirror from tests/test_ui/test_progress.py
  - IMPLEMENT: Non-blocking subprocess progress tracking
  - ADD: Real-time output streaming with Rich
  - INTEGRATE: With existing MigrationProgress class

Task 6 - CLI Progress Restoration:
MODIFY sbm/cli.py:
  - FIND: "progress_tracker=None" comment (line 480)
  - RESTORE: Progress tracking with fixed MigrationProgress
  - TEST: No hanging issues with subprocess operations
  - PRESERVE: CI compatibility and error handling

Task 7 - Documentation Version Consistency:
MODIFY pyproject.toml:
  - CORRECT: version to match actual implementation state
  - FIX: Entry point references to current structure  
  - ALIGN: Dependencies with requirements.txt

MODIFY setup.py:
  - SYNC: Version with pyproject.toml
  - VERIFY: Entry points match actual structure

MODIFY README.md:
  - REMOVE: References to incomplete v2.0 features
  - CORRECT: CLI examples to match current implementation
  - UPDATE: Coverage claims to match actual test coverage

Task 8 - Enhanced Testing:
ENHANCE tests/test_ui/test_progress.py:
  - ADD: Subprocess integration testing
  - TEST: Docker monitoring functionality  
  - VERIFY: No hanging with new progress implementation
  - VALIDATE: CI compatibility of Rich UI enhancements
```

### Per Task Pseudocode

```python
# Task 1 - Fix Rich Progress Hanging
class MigrationProgress:
    def __init__(self):
        # PATTERN: Use threading.Lock for thread safety (see existing tests)
        self._lock = threading.Lock()
        self._background_thread = None
        
    def track_subprocess(self, cmd: List[str], description: str):
        # CRITICAL: Don't block Rich UI with subprocess.run()
        # PATTERN: Use asyncio or threading for non-blocking execution
        def _run_background():
            with self._lock:
                # Run subprocess without blocking Rich progress
                process = subprocess.Popen(cmd, stdout=PIPE, stderr=PIPE)
                # Stream output without blocking UI
                for line in process.stdout:
                    self.update_status(line.decode().strip())
        
        self._background_thread = threading.Thread(target=_run_background)
        self._background_thread.start()

# Task 2 - Docker Startup Visibility  
def run_just_start(theme_name: str, config: Config):
    # REPLACE: suppress_output=True with progress monitoring
    progress = MigrationProgress()
    
    with progress.step("Starting Docker containers"):
        # PATTERN: Monitor container status instead of suppressing
        docker_monitor = DockerStatusMonitor()
        cmd = ["just", "start", theme_name, "prod"]
        
        # CRITICAL: Show Docker startup progress, don't hide it
        progress.track_subprocess(cmd, "Initializing Docker environment")
        
        # Monitor until containers are ready
        while not docker_monitor.all_containers_ready():
            time.sleep(2)
            progress.update_docker_status(docker_monitor.get_status())

# Task 3 - Enhanced Rich Theme
class SBMConsole:
    def __init__(self):
        # ENHANCE: Color palette with auto-sbm branding 
        self.theme = Theme({
            "sbm.primary": "bold #0066CC",      # Auto-SBM blue
            "sbm.success": "bold #00AA44",      # Success green
            "sbm.docker": "bright_blue",        # Docker operations
            "sbm.aws": "bold magenta",          # AWS operations  
            "sbm.progress": "cyan",             # Progress tracking
            # PRESERVE: Existing accessibility themes
            "high_contrast.text": "white on black"
        })
```

### Integration Points

```yaml
CONFIGURATION:
  - update: sbm/config.py
  - add: "UI_THEME = os.getenv('SBM_UI_THEME', 'default')"
  - add: "DOCKER_MONITOR_INTERVAL = int(os.getenv('DOCKER_MONITOR_INTERVAL', '2'))"

TESTING:
  - enhance: tests/test_ui/test_progress.py  
  - add: Subprocess mocking patterns for Docker operations
  - validate: No hanging issues with new progress implementation

DOCUMENTATION:
  - update: README.md with accurate CLI examples
  - fix: Version consistency across pyproject.toml, setup.py
  - align: Feature descriptions with actual implementation

CLI ENTRY POINTS:
  - verify: pyproject.toml [project.scripts] matches actual structure
  - test: Global 'sbm' command works with enhanced UI
  - maintain: Development mode compatibility (python -m auto_sbm.main)
```

## Validation Loop

### Level 1: Syntax & Style

```bash
# Run these FIRST - fix any errors before proceeding
ruff check sbm/ --fix         # Auto-fix formatting
mypy sbm/ui/ sbm/core/        # Type checking for modified files
ruff format sbm/              # Consistent formatting

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests with Rich UI Testing

```python
# ENHANCE tests/test_ui/test_progress.py
def test_migration_progress_no_hanging():
    """Progress tracking doesn't hang with subprocess operations"""
    with StringIO() as fake_stdout:
        console = Console(file=fake_stdout, force_terminal=True)
        progress = MigrationProgress(console=console)
        
        # Simulate Docker startup without hanging
        progress.track_subprocess(["echo", "test"], "Docker startup")
        progress.wait_completion(timeout=5)  # Should not hang
        
        output = fake_stdout.getvalue()
        assert "Docker startup" in output
        assert not progress.is_hanging()

def test_docker_status_monitoring():
    """Docker status monitoring works without blocking"""
    monitor = DockerStatusMonitor()
    with mock.patch('subprocess.run') as mock_run:
        mock_run.return_value.stdout = "container1\trunning\n"
        
        status = monitor.get_status()
        assert status.containers["container1"] == "running"
        assert status.startup_stage in ["init", "starting", "ready"]

def test_enhanced_rich_theme():
    """Enhanced color theme renders correctly"""
    console = SBMConsole()
    with StringIO() as output:
        console.print("Test message", style="sbm.primary")
        rendered = output.getvalue()
        # Verify ANSI color codes present
        assert "\x1b[" in rendered  # ANSI escape sequence
```

```bash
# Run and iterate until passing:
uv run pytest tests/test_ui/ -v
# If failing: Read error, understand root cause, fix code, re-run
```

### Level 3: Integration Test - Full Migration Visibility

```bash
# Test complete migration visibility without hangs
uv run python -m sbm.cli auto test-theme --dry-run

# Expected output pattern:
# ╭─ Migration Progress ─╮
# │ Step 1/6: Git Setup  │ ✓ Complete
# │ Step 2/6: Docker...  │ 🐳 Starting containers...
# │ Step 3/6: Files...   │ ⏳ Waiting
# ╰─────────────────────╯

# Critical: No silent periods > 10 seconds
# Critical: No CLI hanging
# Critical: Rich UI renders properly

# Test CI compatibility:
FORCE_COLOR=0 uv run python -m sbm.cli auto test-theme --dry-run
# Expected: Plain text output, no Rich formatting, no errors
```

### Level 4: Documentation Validation

```bash
# Verify version consistency
python -c "
import toml
import ast

# Check pyproject.toml vs package versions
pyproject = toml.load('pyproject.toml')
with open('sbm/__init__.py') as f:
    init_content = f.read()
    
version_line = [line for line in init_content.split('\n') if '__version__' in line][0]
package_version = ast.literal_eval(version_line.split('=')[1].strip())

assert pyproject['project']['version'] == package_version
print('✓ Version consistency verified')
"

# Test CLI entry points work
sbm --help  # Should work with enhanced UI
python -m sbm.cli --help  # Should work with enhanced UI

# Validate README examples
grep -n "sbm migrate" README.md  # Should match actual CLI commands
grep -n "90%" README.md  # Should match actual test coverage
```

### Level 5: Creative Validation - Performance & UX

```bash
# Performance testing with realistic migration
time sbm auto real-theme-name --dry-run 2>&1 | tee migration_output.log

# Analyze output for:
# 1. No gaps > 10 seconds without output
grep -n "timestamp" migration_output.log | awk 'calculate time gaps'

# 2. Rich UI performance impact
# Migration should not be significantly slower with enhanced UI

# 3. Memory usage during long operations
# Monitor memory during Docker startup to ensure no leaks

# User Experience validation:
# 1. Color scheme looks professional
# 2. Progress tracking is intuitive  
# 3. Error messages are actionable
# 4. Completion summary is satisfying
```

## Final Validation Checklist

- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] No linting errors: `uv run ruff check sbm/`
- [ ] No type errors: `uv run mypy sbm/ui/ sbm/core/`
- [ ] Full migration has no visibility gaps > 10 seconds
- [ ] Rich progress bars don't hang CLI
- [ ] Docker startup shows real-time progress
- [ ] AWS authentication integrates with Rich UI
- [ ] Enhanced colors and formatting throughout
- [ ] Version consistency across all files
- [ ] README matches actual implementation
- [ ] CI compatibility maintained
- [ ] Manual migration test successful: `sbm auto test-theme --dry-run`

---

## Anti-Patterns to Avoid

- ❌ Don't break existing CI/CD compatibility with Rich UI changes
- ❌ Don't introduce new hanging issues while fixing progress bars
- ❌ Don't hardcode Docker container names or AWS regions
- ❌ Don't suppress subprocess output without providing alternatives
- ❌ Don't create multiple console instances (use singleton pattern)
- ❌ Don't claim features in documentation that don't exist
- ❌ Don't mix v1.0 and v2.0 architecture references
- ❌ Don't ignore test failures due to Rich UI complexity

## Success Score

**Confidence Level: 9/10** for one-pass implementation success

**High Confidence Factors:**
- Comprehensive research of current implementation and issues
- Clear identification of root causes (hanging, subprocess integration)
- Existing Rich UI infrastructure to build upon  
- Well-defined testing patterns with StringIO capture
- Specific file locations and code patterns identified

**Risk Mitigation:**
- Rich progress hanging issue has known solutions and workarounds
- Docker monitoring can be implemented incrementally
- Documentation fixes are straightforward
- CI compatibility is well-established pattern

This PRP provides complete context for implementing enhanced migration visibility, Rich UI improvements, and documentation consistency in a single focused effort.