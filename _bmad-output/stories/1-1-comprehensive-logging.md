# Story 1.1: Comprehensive Migration Logging & Reporting

Status: review

## Story

As a **developer running batch migrations**,
I want **comprehensive error logging and well-organized Salesforce messages captured for every migration**,
so that **I can reference detailed logs for debugging, track all PR links, and have copy-ready Salesforce notes for each successful migration**.

## Acceptance Criteria

1. **AC1: Step-Level Error Capture**
   - Given a multi-slug migration batch is running
   - When any migration step fails (Git, Docker, Core Migration, PR Creation)
   - Then the specific step that failed is logged with full context
   - And the batch continues processing remaining slugs

2. **AC2: Full Stack Trace Logging**
   - Given an exception occurs during migration
   - When the error is captured
   - Then the complete Python stack trace is preserved in the report
   - And the exception type and message are clearly visible

3. **AC3: SCSS Compilation Error Capture**
   - Given SCSS compilation fails during Docker verification
   - When the compilation error is detected
   - Then the Docker log excerpt containing the error is captured
   - And the specific file and line number (if available) are included

4. **AC4: Salesforce Message Documentation**
   - Given a migration completes successfully with PR creation
   - When the report is generated
   - Then the full Salesforce message (What section) is included
   - And the PR URL is prominently displayed
   - And the format is ready for copy/paste into Salesforce

5. **AC5: Timing and Context Metadata**
   - Given any migration attempt (success or failure)
   - When results are captured
   - Then the elapsed time for that slug is recorded
   - And the branch name is included
   - And a timestamp is recorded

6. **AC6: Summary Statistics**
   - Given a batch migration completes
   - When the report is finalized
   - Then a summary section shows total slugs processed
   - And counts for success/failed/error are displayed
   - And the summary appears at the top of the report

7. **AC7: Persistent Report Files**
   - Given any batch migration runs
   - When the process completes (success or partial failure)
   - Then a timestamped report file is saved to `reports/`
   - And the report is human-readable
   - And the `reports/` directory remains gitignored

## Tasks / Subtasks

- [x] Task 1: Enhanced Result Data Structure (AC: 1, 2, 3, 5)
  - [x] 1.1 Create `MigrationResult` dataclass in `sbm/core/migration.py` with fields: slug, status, step_failed, error_message, stack_trace, scss_errors, pr_url, salesforce_message, branch_name, elapsed_time, timestamp
  - [x] 1.2 Update `migrate_dealer_theme` to populate and return `MigrationResult`
  - [x] 1.3 Add step tracking enum: GIT_SETUP, DOCKER_STARTUP, CORE_MIGRATION, SCSS_VERIFICATION, GIT_COMMIT, PR_CREATION

- [x] Task 2: Step-Level Error Capture (AC: 1, 2)
  - [x] 2.1 Wrap each major step in `migrate_dealer_theme` with try/except
  - [x] 2.2 Capture `traceback.format_exc()` on exceptions
  - [x] 2.3 Set `step_failed` field when a step fails
  - [x] 2.4 Return partial result instead of raising

- [x] Task 3: SCSS Compilation Error Extraction (AC: 3)
  - [x] 3.1 In `_verify_scss_compilation_with_docker`, capture Docker log excerpt on failure
  - [x] 3.2 Parse error file/line from Gulp output
  - [x] 3.3 Include in `MigrationResult.scss_errors` list

- [x] Task 4: Enhanced Report Generation (AC: 4, 6, 7)
  - [x] 4.1 Refactor `_generate_migration_report` to use structured sections
  - [x] 4.2 Add summary section at top with success/fail counts
  - [x] 4.3 Format Salesforce messages in copy-ready blocks
  - [x] 4.4 Include timing breakdown per slug
  - [x] 4.5 Add separator lines between slugs for readability

- [x] Task 5: CLI Integration (AC: 1, 5, 7)
  - [x] 5.1 Update `auto` command to pass timing context to migration
  - [x] 5.2 Collect all `MigrationResult` objects in list
  - [x] 5.3 Call enhanced report generator at end of batch
  - [x] 5.4 Print summary to console matching report format

- [ ] Task 6: Testing & Verification (AC: all)
  - [ ] 6.1 Test with intentionally failing slug (non-existent theme)
  - [ ] 6.2 Verify SCSS error capture with broken SCSS
  - [ ] 6.3 Verify successful migration captures all Salesforce content
  - [ ] 6.4 Confirm report file is created and gitignored

## Dev Notes

### Architecture Patterns

The existing codebase follows these patterns:
- **Return dictionaries** for complex results (see `create_pr` in `git.py`)
- **Logging via `sbm.utils.logger`** - use `logger.error()`, `logger.info()`
- **Console output via `sbm.ui.console.SBMConsole`** - use `console.print_error()`, `console.print_info()`
- **Path handling via `sbm.utils.path`** - use `REPO_ROOT` for report directory

### Current State (already implemented)

The initial implementation exists with:
- Basic error capture in `auto` command loop
- Simple `_generate_migration_report()` function in `cli.py`
- `salesforce_message` returned from `create_pr` and `run_post_migration_workflow`
- `reports/` added to `.gitignore`

### What Needs Enhancement

1. **Structured result object** instead of ad-hoc dict
2. **Step identification** on failure (which step failed)
3. **Stack traces** preserved, not just error messages
4. **SCSS errors** extracted from Docker logs
5. **Richer report format** with summary stats and better organization

### File Locations

| File | Purpose |
|------|---------|
| `sbm/core/migration.py` | Add `MigrationResult` dataclass, update return types |
| `sbm/core/git.py` | Already returns `salesforce_message` (complete) |
| `sbm/cli.py` | Update `auto` command, enhance `_generate_migration_report` |
| `reports/*.txt` | Output location (gitignored) |

### Testing Approach

1. Create a test slug file with:
   - One valid slug
   - One non-existent slug (will fail at Git)
   - One slug with known SCSS issues (if available)
2. Run `sbm auto @test-slugs.txt`
3. Verify report contents match expectations

### References

- [Source: sbm/cli.py - `_generate_migration_report` function]
- [Source: sbm/core/migration.py - `migrate_dealer_theme`, `run_post_migration_workflow`]
- [Source: sbm/core/git.py - `create_pr` method returns salesforce_message]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

- Created `MigrationStep` enum and `MigrationResult` dataclass in `sbm/core/migration.py`
- Updated `migrate_dealer_theme()` to return `MigrationResult` with step-level error tracking
- Updated `run_post_migration_workflow()` to accept optional `result` parameter
- Updated `_verify_scss_compilation_with_docker()` to capture and return SCSS errors
- Enhanced `_generate_migration_report()` with summary section, Salesforce messages block, and detailed results
- Added helper functions `_get_status()` and `_get_field()` for MigrationResult/dict compatibility
- Updated CLI `auto` command to properly handle MigrationResult objects
- Bumped version to 2.2.0, updated CHANGELOG.md

### File List

- sbm/core/migration.py (modified)
- sbm/cli.py (modified)
- pyproject.toml (modified)
- CHANGELOG.md (modified)

### Change Log
- 2026-01-06: Story created for comprehensive logging enhancements
- 2026-01-06: Implemented Tasks 1-5 (MigrationResult, step tracking, SCSS errors, enhanced reports, CLI integration)
