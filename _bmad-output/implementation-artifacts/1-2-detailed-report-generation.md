# Story 1.2: Detailed Report Generation

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a User,
I want a detailed markdown report generated after every migration,
So that I can review exactly what changed, what files were created, and how much manual effort was saved.

## Acceptance Criteria

**Given** a successful migration run
**When** the process finishes
**Then** a new markdown file is created in `.sbm-reports/{slug}-{timestamp}.md`
**And** the report contains: Summary, File Breakdown, Component Details, and Time Savings analysis
**And** an `index.md` in `.sbm-reports/` is updated with a link to the new report
**And** the report path is returned to the tracker for storage

## Tasks / Subtasks

- [x] Task 1: Create `sbm/utils/report_generator.py` module (AC: All criteria)
  - [x] Implement `generate_migration_report()` function
  - [x] Implement `MigrationReportData` dataclass to hold all migration data
  - [x] Create markdown report template rendering
  - [x] Save to `.sbm-reports/{slug}-{timestamp}.md`
  - [x] Update `.sbm-reports/index.md` table of contents
  - [x] Return report path from function

- [x] Task 2: Update `sbm/utils/tracker.py` to track report paths (AC: Report path stored)
  - [x] Add `report_path` parameter to `record_run()` function signature
  - [x] Update `MigrationRun` data schema to include `report_path` field
  - [x] Ensure backward compatibility for existing runs without report_path

- [x] Task 3: Update `sbm/core/migration.py` to generate reports (AC: Reports generated after migration)
  - [x] Collect migration data during execution (files created, SCSS stats, component details, validation results)
  - [x] Call `generate_migration_report()` after successful migration
  - [x] Pass report_path to `record_run()`

- [x] Task 4: Write comprehensive unit tests (AC: All tests pass)
  - [x] Create `tests/test_report_generator.py` with mock data tests
  - [x] Test markdown formatting and structure
  - [x] Test index.md updates and appending
  - [x] Create `tests/test_tracker_reports.py` for report_path recording
  - [x] Test backward compatibility with old data

- [x] Task 5: Verify integration end-to-end (AC: Fully functional)
  - [x] Run real migration and verify markdown report created
  - [x] Verify report path tracked in `~/.sbm_migrations.json`
  - [x] Verify `index.md` updated correctly
  - [x] Run full test suite to ensure no regressions

## Dev Notes

### Critical Context from Analysis

#### Review Follow-ups (AI)
- [x] [AI-Review][Critical] Missing Tests: `tests/test_report_generator.py` and `tests/test_tracker_reports.py` are listed in tasks but do not exist in the codebase.
- [x] [AI-Review][Medium] Untracked File: `sbm/utils/report_generator.py` is present but not committed to git.
- [x] [AI-Review][Medium] File List missing in Dev Agent Record.


**Existing `.txt` Report Implementation:**
- Current implementation in `sbm/cli.py:_generate_migration_report()` (lines 881-985)
- Generates plain text reports in `reports/` directory for bulk migrations
- Format: `migration_report_{timestamp}.txt`
- Contains: Summary, Salesforce Messages, Detailed Results
- This is for **bulk operations** and will remain unchanged

**New Markdown Report System (This Story):**
- Create NEW module: `sbm/utils/report_generator.py`
- Generate **markdown** reports in `.sbm-reports/` directory
- Format: `.sbm-reports/{slug}-{timestamp}.md`
- For **individual migrations** (single slug runs)
- Maintain `.sbm-reports/index.md` as table of contents
- Return report path to be tracked in migration history

### Architecture Patterns and Constraints

**From Architecture.md:**
- Tech Stack: Python 3.9+, Click, Rich
- Follow existing patterns in `sbm/utils/` modules
- Use Path objects from pathlib (not string paths)
- Log with `from sbm.utils.logger import logger`
- Handle errors gracefully without crashing CLI

**Project Structure:**
- Source code: `sbm/` directory
- Utilities: `sbm/utils/` (where report_generator.py goes)
- Core logic: `sbm/core/migration.py` (where we call reports)
- Tracker: `sbm/utils/tracker.py` (where we store report_path)
- Tests: `tests/` directory (NOT in sbm/)

### MigrationResult Data Structure

From `sbm/core/migration.py` (lines 51-109), the `MigrationResult` dataclass includes:
```python
class MigrationResult:
    slug: str
    status: str  # 'success', 'failed', 'error'
    pr_url: Optional[str] = None
    salesforce_message: Optional[str] = None
    branch_name: Optional[str] = None
    elapsed_time: float = 0.0
    lines_migrated: int = 0  # NEW field from Story 1.1
    step_failed: Optional[MigrationStep] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    scss_errors: list[str] = field(default_factory=list)
```

This object will be the input to `generate_migration_report()`.

### Report Format Specification

**From PRD (lines 333-352), the markdown report must include:**

1. **Summary Section:**
   - Theme slug
   - Migration timestamp
   - Success/failure status
   - Duration
   - Lines migrated
   - Time saved calculation (lines/800 hours)
   - PR URL if created

2. **File Breakdown:**
   - List of files created (`sb-home.scss`, `sb-vdp.scss`, etc.)
   - File sizes
   - Line counts per file

3. **Component Details:**
   - SCSS transformation stats (mixins converted, variables mapped)
   - OEM-specific styles added (Stellantis cookie banner, etc.)
   - Map component migration status

4. **Time Savings Analysis:**
   - Lines migrated
   - Estimated manual effort (default: 4 hours = 240 minutes)
   - Automation time
   - Time saved calculation

5. **Validation Results:**
   - SCSS compilation status
   - Any errors or warnings

6. **Links:**
   - PR URL
   - Branch name

**Index.md Format:**
Table of contents with columns:
- Date
- Slug
- Status (✅/❌)
- Duration
- Lines Migrated
- Link to report

### Integration Points

**1. `sbm/core/migration.py` calls:**
```python
from sbm.utils.report_generator import generate_migration_report

# After successful migration in migrate_dealer_theme()
if result.status == "success":
    report_path = generate_migration_report(result)
    # Then pass to tracker
```

**2. `sbm/utils/tracker.py` modification:**
```python
def record_run(
    slug: str,
    command: str,
    status: str,
    duration: float,
    automation_time: float,
    lines_migrated: int = 0,
    manual_estimate_minutes: int = 240,
    report_path: Optional[str] = None,  # NEW parameter
) -> None:
```

### Testing Strategy

**From existing test patterns (`tests/test_migration_stats_fix.py`):**
- Use `pytest` with `unittest.mock`
- Mock external dependencies
- Test with `MigrationResult` objects
- Use `tempfile.TemporaryDirectory()` for file operations
- Verify file contents with `.read_text()`
- Test backward compatibility

**Specific tests needed:**
1. `test_report_generator.py`:
   - Test report generation with success result
   - Test report generation with failed result
   - Test markdown formatting
   - Test index.md creation and updates
   - Test file path sanitization

2. `test_tracker_reports.py`:
   - Test `record_run()` with report_path
   - Test backward compatibility (existing data without report_path)
   - Test that report_path is stored in JSON

### File Location Discovery

The repository root is: `/Users/nathanhart/auto-sbm`
- New module path: `/Users/nathanhart/auto-sbm/sbm/utils/report_generator.py`
- Reports directory: `/Users/nathanhart/auto-sbm/.sbm-reports/`
- Test path: `/Users/nathanhart/auto-sbm/tests/test_report_generator.py`

### Latest Technology Information

**Python Markdown Libraries:**
- No external markdown library needed - we're generating raw markdown strings
- Use f-strings for template formatting
- Python 3.9+ supports `from __future__ import annotations` for type hints

**Testing:**
- pytest 7.x+ (already in use per `tests/` structure)
- Use `@patch` decorator from `unittest.mock`
- Follow existing test patterns in codebase

### References

- [Source: enumerated-petting-puffin.md#Phase 1: History Display & Report Generation]
- [Source: epics.md#Story 1.2: Detailed Report Generation]
- [Source: architecture.md#Tech Stack]
- [Source: sbm/core/migration.py#MigrationResult dataclass]
- [Source: sbm/utils/tracker.py#record_run function]
- [Source: tests/test_migration_stats_fix.py#Testing patterns]

## Dev Agent Record

### Agent Model Used

_To be filled by dev agent_

### Debug Log References

_To be filled by dev agent_

### Completion Notes List

_To be filled by dev agent_

### File List

- `sbm/utils/report_generator.py`
- `tests/test_report_generator.py`
- `tests/test_tracker_reports.py`
- `sbm/core/migration.py`
- `sbm/utils/tracker.py`
