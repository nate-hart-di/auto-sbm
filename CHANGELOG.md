# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.15.3] - 2026-02-11

### Fixed
- **Stats Accuracy**: `lines_migrated` now uses GitHub PR `additions` count instead of local SCSS output line count, matching what GitHub shows on PRs
- **Git Retry Resilience**: `commit_changes()` now returns `False` when `git add` fails instead of silently succeeding
- **Git Auto-Stash**: `checkout_main_and_pull()` auto-stashes dirty working tree from previous SBM migrations instead of permanently blocking retries
- **Post-Migrate Tracking**: `sbm post-migrate` now records runs in stats so manual recoveries are visible in reporting
- 855b976 Fix map detection for template parts
- 34cc0bc Merge branch 'fix/log-duplication'
- 8709d41 Fix map migration detection and SCSS cleanup (#6)
- acaf889 Fix map migration detection and SCSS cleanup
- 6f161a7 chore: bump version to 2.13.16
- db46062 fix: AttributeError in remigration prompt - use console.console.print()
- be36584 Auto-add new files
- 2916b1f Auto-add new files
- 8f7c278 Auto-add new files
- ac45d4a fix: Use superseded flag for remigration instead of corrupting pr_state

## [2.15.2] - 2026-02-11

### Changed
- Update default PR reviewers from carsdotcom/fe-dev to carsdotcom/fe-dev-sbm

## [2.15.1] - 2026-02-11

### Fixed
- **Rich Markup Bug**: Fixed retry prompt displaying `[/]` as literal text instead of closing Rich markup tag; replaced `sys.stdout.write` with `console.console.print` for proper rendering
- **Missing Error Handler**: Fixed undefined `logger` reference in retry prompt exception handler; now uses console output consistently

### Changed
- **Scheduled Reports - Weekdays Only**: Scheduler now skips Saturday and Sunday; only sends reports Mon-Fri
- **Monday Weekly Report - Calendar Week**: Monday summary now covers the previous calendar week (Mon 00:00 through Sun 23:59) instead of a rolling 7-day window
- **Slack Channel Config**: Added `SLACK_CHANNEL` to `.env` for scheduled report delivery

## [2.15.0] - 2026-01-29

### Added
- **PR Merge CLI Command**: Added `sbm pr merge` command for enabling auto-merge on PRs
  - New command: `sbm pr merge` - Enable auto-merge on all open PRs matching pattern
  - Option: `-p/--pattern` to specify branch name pattern (default: pcon-864)
  - Option: `--dry-run` to preview changes without making them
  - Automatically updates branches to be current with base before enabling auto-merge
  - Shows detailed status and diagnostics for each PR
  - Examples:
    - `sbm pr merge` - Enable auto-merge on all pcon-864* PRs
    - `sbm pr merge -p pcon-123` - Enable for specific project PRs
    - `sbm pr merge --dry-run` - Preview without making changes

### Changed
- **PR Command Restructured**: Converted `sbm pr` from simple command to command group
  - `sbm pr create <theme>` - Create a new PR (formerly `sbm pr <theme>`)
  - `sbm pr merge` - Enable auto-merge on existing PRs (new)
  - Maintains backward compatibility through command group structure

## [2.14.2] - 2026-01-29

### Fixed
- **Auto-Merge Branch Update**: Auto-merge now updates branches to be current with base before enabling
  - New `_update_branch()` method updates PR branches when behind base
  - Prevents "branch must be up to date" blocking issue
  - Script `enable_auto_merge.sh` now updates branches before enabling auto-merge
  - Handles BEHIND and DIRTY merge states automatically

## [2.14.1] - 2026-01-29

### Added
- **Auto-Merge Diagnostic Script**: Added `scripts/enable_auto_merge.sh` for batch enabling auto-merge on existing PRs
  - Shows detailed diagnostics for each PR (merge status, checks, reviews)
  - Explains why PRs aren't merging (conflicts, pending reviews, failing checks)
  - Usage: `./scripts/enable_auto_merge.sh pcon-864`

## [2.14.0] - 2026-01-29

### Added
- **Auto-Merge Support**: PRs now automatically enable auto-merge (squash strategy) upon creation
  - New `_enable_auto_merge()` method enables auto-merge with squash on PR creation
  - New `_check_pr_merge_status()` method provides diagnostics on merge blockers
  - Auto-merge enabled for both new and existing PRs
  - Detailed logging shows why PRs might not merge immediately (pending checks, failing checks, review requirements, merge conflicts, branch protection)
  - Refactored GitHub token env setup into reusable `_get_gh_env()` method

## [2.13.20] - 2026-01-29

### Changed
- Skip missing CommonTheme map partials without warning when styles are migrated

## [2.13.19] - 2026-01-29

### Changed
- Detect do_shortcode('[full-map]') usage in templates to trigger map style migration
- Add shortcode-based CommonTheme SCSS resolution fallback

## [2.13.18] - 2026-01-29

### Changed
- Detect map template parts with /partials prefix and section-directions paths
- Improve map migration reporting to treat template-derived imports as map components
- Update Lexus map partial patterns for section-directions

## [2.13.17] - 2026-01-29

### Changed
- Fix map import regex for underscore-prefixed filenames
- Prevent SCSS comment cleanup from orphaning selectors with top-level at-rules
- Reduce verbose compilation error logging

## [2.13.16] - 2026-01-29

### Fixed
- **Log Noise**: Fixed duplicate 'Detected invalid_css' log messages by filtering verbose Gulp error objects and downgrading detection logs to debug.

## [2.13.15] - 2026-01-29

### Fixed
- **CRITICAL: AttributeError in Remigration Prompt**: Fixed `'SBMConsole' object has no attribute 'print'` crash
  - Bug: `prompts.py:502` called `console.print()` on SBMConsole wrapper instead of wrapped Rich Console
  - Impact: Remigration prompt crashed with AttributeError when trying to display menu
  - Fix: Use `console.console.print()` to access the actual Rich Console

## [2.13.14] - 2026-01-29

### Fixed
- **CRITICAL: Remigration Menu Not Showing**: Fixed batch operations bypassing remigration prompt
  - Bug: `cli.py:1207` checked `yes` (set to True for batch mode) instead of `explicit_yes` (user's original flag)
  - Impact: ALL batch operations with multiple slugs were enabling non_interactive mode, hiding the 3-option menu
  - Fix: Changed condition to use `explicit_yes` so remigration menu shows correctly for batch operations

## [2.13.13] - 2026-01-29

### Fixed
- **CRITICAL: Remigration Data Integrity**: Fixed remigration to use `superseded` flag instead of changing `pr_state`, preserving GitHub truth
  - Old PRs now marked with `superseded: true` and `superseded_at` timestamp
  - PR state (OPEN/MERGED/CLOSED) remains accurate to GitHub reality
  - Daily PR sync no longer overwrites remigration markers
  - Stats correctly exclude superseded runs without data corruption

### Added
- **Status Constants**: Created `sbm/utils/constants.py` with type-safe constants for PR states and completion states
- **Shared Helper Function**: Created `sbm/utils/run_helpers.py` with `is_complete_run()` to prevent duplicate logic
- **Comprehensive Tests**: Added 18 new tests covering remigration and helper functions
  - `tests/test_run_helpers.py`: 10 tests for shared helper
  - `tests/test_tracker_remigration.py`: 8 tests for remigration logic
- **Superseded State Display**: Added "Superseded" status to CLI stats with dim styling
- **Performance Warning**: Log warning when marking >10 runs for remigration

### Changed
- **Code Deduplication**: Replaced duplicate `is_complete_run()` definitions in `firebase_sync.py` (lines 418 and 546) with shared helper
- **Stats Filtering**: All stats calculations now exclude superseded runs automatically
- **Completion State Priority**: Superseded state now checked first in `get_pr_completion_state()`

## [2.13.12] - 2026-01-29

### Added
- **Remigration Support**: Added interactive prompt with three options when duplicates are detected:
  - Skip duplicates (existing behavior - proceed with remaining sites only)
  - Remigrate (new feature - mark old PRs as superseded, create new migrations)
  - Cancel (abort the entire operation)
- **Status Tracking**: Implemented `mark_runs_for_remigration()` to update Firebase records with remigration metadata
- **Enhanced Testing**: Updated duplicate prevention tests to cover all three action types (Skip, Remigrate, Cancel)

### Changed
- **Duplicate Prompt**: Replaced yes/no confirmation with numbered menu for better UX
- **Non-Interactive Mode**: Now skips duplicates by default in `--yes` mode with improved logging

## [2.13.11] - 2026-01-28

### Fixed
- **CLI Stats**: Fixed `NameError` in `sbm stats --history` and expanded team panels to include `Total Users` and `Time Saved`.
- **Consistency**: Renamed 'Lines of Code' to 'Lines Migrated' in Slack reports for 100% parity with CLI.
- **Validation**: Ensured 'Lines Migrated' is visible in all stat boxes across all command variations.

## [2.13.10] - 2026-01-28

### Added
- **Stats Metrics Alignment**: Restored "Time Saved" to all CLI stats views and aligned with Slack reports using the `lines / 800` formula.
- **Global Firebase Sync**: Enabled "Global Janitor" mode, allowing any authenticated user to refresh PR statuses across the team.
- **Slack App Improvements**: Defaulted `/sbm-stats` to "week" view and fixed command parsing for custom periods and top contributors.
- **Maintenance Scripts**: Added `scripts/delete_verification_run.py` to purge test noise from the database.

## [2.13.9] - 2026-01-28

### Fixed
- **Map Migration**: Fixed critical path traversal vulnerability where external CommonTheme files were treated as local and skipped.
- **Map Detection**: Enhanced detection logic to always scan template files for map partials, fixing issues with dynamic shortcode registration.
- **Partial Migration**: Enabled copying of PHP partials even if they exist in CommonTheme, ensuring standalone functionality.
- **Keywords**: Added `section-directions` to map component detection keywords.

## [2.13.8] - 2026-01-23

### Changed
- Force GitHub re-auth during setup if scopes/permissions are insufficient

## [2.13.7] - 2026-01-23

### Changed
- Make devtools-cli optional in setup (warn-only, no clone attempts)

## [2.13.6] - 2026-01-23

### Changed
- Ensure `sbm update` installs dependencies using the repo virtualenv Python

## [2.13.5] - 2026-01-23

### Changed
- Ensure GitHub auth scopes/permissions and improve Firebase key fetch fallback
- Always set Firebase database URL in .env during setup

## [2.13.4] - 2026-01-23

### Changed
- Make setup resilient to Firebase workflow failures and missing PATH entries

## [2.13.3] - 2026-01-23

### Changed
- Update PCON-864 pattern matching across scripts

## [2.13.2] - 2026-01-23

### Changed
- Update PCON number to 864 for future SBM runs

## [2.13.1] - 2026-01-23

### Changed
- Miscellaneous updates and documentation/testing tweaks

## [2.13.0] - 2026-01-22

### Changed
- **Firebase Authentication**: Simplified to use GitHub Secrets → .env only
- Removed 1Password CLI integration (op) - no longer required
- Removed macOS Keyring/secure_store - simpler authentication flow
- Added automatic Firebase API key fetch via GitHub Actions during setup
- Added manual fallback prompt if GitHub fetch fails
- Added mandatory Firebase API key validation before all migration commands

## [2.12.8] - 2026-01-22

### Changed
- require FIREBASE__API_KEY during setup/doctor for authenticated stats access
- document Firebase auth rules and secure key distribution

## [2.12.7] - 2026-01-22

### Changed
- add Firebase author backfill utilities for fixing unknown runs

## [2.12.6] - 2026-01-22

### Fixed
- enforce GitHub user id attribution for Firebase runs in user mode
- warn when GitHub auth is missing during run tracking

## [2.12.5] - 2026-01-22

### Changed
- remove Success Rate from Slack/CLI stats displays and add configurable Auto-SBM PR link
- normalize stats team/history views to use shared tracker imports
- restore commented selector blocks during SCSS processing and recovery to prevent invalid braces

## [2.12.4] - 2026-01-21

### Changed
- Enforce GitHub-authored stats attribution and sync gating

## [2.12.3] - 2026-01-20

### Changed
- ensure rich-click is installed during setup/update and wrapper health checks
- add rich-click dependency test

## [2.12.2] - 2026-01-20

### Changed
- Fix team stats filtering for --since/--user team views.

## [2.12.1] - 2026-01-20

### Changed
- disable keychain prompts by making keyring opt-in via SBM_ENABLE_KEYRING

## [2.12.0] - 2026-01-20

### Changed
- add PR state-aware stats filtering and merged-run dedupe across CLI/Slack
- fix team stats timezones and global slug totals to prevent overcounts
- add metadata refresh/backfill scripts with GH PR enrichment
- add rich-click help grouping and align runtime dependencies

## [2.11.8] - 2026-01-16
### Fixed
- **Stats CLI**: Fixed datetime comparison bug (offset-naive vs offset-aware) causing crashes with `--since` filter.
- **Stats CLI**: Added period-based filtering support (`--since day`, `--since week`, `--since month`, `--since N`).
- **Stats CLI**: Fixed merged_at preference for filtering/sorting (better backfill accuracy).
- **Tests**: Rewrote `test_history_filtering.py` with 22 comprehensive tests.

## [2.11.7] - 2026-01-15
### Fixed
- Committed missing `datetime` import in `sbm/utils/firebase_sync.py`.
- Updated `.gitignore` to exclude generated markdown reports.

## [2.11.6] - 2026-01-15
### Added
- New scripts for data hygiene: `scripts/backfill_verified_runs.py` and `scripts/archive_extra_runs.py`.
- Verified & Backfilled 20 missing historical SBM migrations to Firebase.
- Archived 100+ non-production/test runs to `archived_runs` node to align CLI stats with official tracking.

## [2.11.5] - 2026-01-15
### Added
- **Maintenance Scripts**: Added comprehensive suite of database maintenance and verification scripts in `scripts/` (including `clean_db_duplicates.py`, `monitor_progress.py`, `fix_false_success.py`).

## [2.11.3] - 2026-01-15
### Changed
- **CLI UX**: Implemented "Smart Spinner" for `sbm stats` that displays exactly what is being retrieved (e.g., "Retrieving Stats for user 'username' since 2024-01-01...").

## [2.11.2] - 2026-01-15
### Changed
- **CLI Polish**: Replaced raw "Firebase initialized" logs with a sleek "Retrieving Stats..." spinner in `sbm stats`.
- **Strict Stats**: Removed all "Estimation" logic (500 lines/site) from `sbm stats --team`. Stats now strictly reflect successful runs in the database (1:1 with reality).
- **Cleanup**: Purged users with 0 successful runs and removed non-success runs (failed/invalid) from the database team-wide.
- **Database Keys**: Migrated all random Firebase Push IDs to readable `slug_timestamp` keys for better auditability.

## [2.11.1] - 2026-01-14

### Fixed
- **Syntax Error**: Fixed broken multiline string in `scheduled_slack_reports.py` that caused SyntaxError on dry-run.
- **Code Quality**: Reorganized imports in `tracker.py` to follow isort conventions.
- **Linting**: Fixed inefficient `.keys()` iteration, unused loop variable, and nested else/if patterns in `tracker.py`.
- **Style**: Updated type ignore comment specificity and line length violations in Slack scripts.

## [2.11.0] - 2026-01-13

### Changed
- **Stats Accuracy**: Refined Firebase sync logic to strictly match SBM-related PRs (ignoring theme updates and unrelated fixes) and prioritize MERGED status.
- **Backfill**: Added robust verification to `scripts/backfill_firebase_runs.py` to ensure only valid SBM PRs are tracked.
- **Reporting**: Added timezone-aware filtering (CST) for daily Slack reports to ensure accurate "Yesterday's" stats.

### Fixed
- **Configuration**: Corrected default value handling for Firebase settings to ensure proper initialization in user mode.
- **Robustness**: `sbm update` now reliably detects and aborts incomplete rebases before attempting updates.
- **Setup**: `setup.sh` wrapper generation now correctly unsets `PYTHONPATH` to prevent environment bleeding.

## [2.10.9] - 2026-01-13

### Changed
- **Legacy Sync**: Optimized stats synchronization to be a one-time migration using a marker file (`~/.sbm_legacy_sync_complete`).

## [2.10.8] - 2026-01-13

### Fixed
- **Robus Update**: `sbm update` now aborts stuck rebases, syncs legacy stats to Firebase, and resets `stats/archive` to handle conflicts automatically.
- **Stats Display**: Fixed `sbm stats` showing raw UID (`dZMC...`) instead of the user's name. It now prioritizes the system name.
- **False Positives**: `sbm` now filters out migrations with 0 lines migrated from being synced to Firebase to prevent data skew.

## [2.10.7] - 2026-01-12

### Fixed
- **Slack reports**: Fall back to `stats/archive` when Firebase is unavailable.

## [2.10.6] - 2026-01-12

### Fixed
- **Slack reports**: Use Firebase runs + legacy migrations for all-time stats.
- **Slack reports**: Avoid "No Activity" when migrations exist without runs.

## [2.10.5] - 2026-01-12

### Fixed
- **Setup noise**: Skip NVM config and `load-nvmrc` when NVM is missing.

## [2.10.4] - 2026-01-12

### Fixed
- **Setup prompts**: Remove interactive Firebase prompts by using built-in defaults.

## [2.10.3] - 2026-01-12

### Fixed
- **CLI imports**: Restore missing `sbm.utils.tracker` module.

## [2.10.2] - 2026-01-12

### Changed
- Fix wrapper import check to use PYTHONPATH

## [2.10.1] - 2026-01-12

### Changed
- Stop prompting for Firebase secrets when 1Password refs missing

## [2.10.0] - 2026-01-12

### Added
- **1Password refs**: Save `op://` references once and avoid future prompts.
- **Local marker**: Store refs in `.sbm_op_refs` with a completion marker.

### Changed
- **Setup flow**: Auto-detect 1Password refs from env or saved file before prompting.

## [2.9.0] - 2026-01-12

### Added
- **1Password integration**: Read Firebase URL/API key via `op://` references during setup/update.
- **Setup requirements**: Install 1Password CLI (`op`) as a required tool.

## [2.8.1] - 2026-01-12

### Changed
- Fix missing get_settings import for secure store

## [2.8.0] - 2026-01-12

### Added
- **Firebase user auth**: Anonymous auth token flow for REST reads/writes under team stats rules.
- **Secure storage**: Store Firebase URL/API key in system keychain and scrub from `.env` on setup/update.
- **Stats reliability**: User-mode stats use Firebase UID for consistent history.

### Fixed
- **CLI internals**: Removed duplicate `internal-refresh-stats` command registration.

## [2.7.10] - 2026-01-12

### Added
- **Legacy Backfill**: Added `scripts/backfill_firebase.py` to restore historical run data from local archives to Firebase.

## [2.7.9] - 2026-01-12

### Fixed
- **Stats display**: Fixed stats showing 0 lines migrated and 0h time saved when runs data is missing from Firebase.
  - Stats now estimate metrics using **500 lines/migration** (median from 104 actual runs, IQR filtered to exclude outliers).
  - Team stats (`--team`) apply same data-driven estimation for users with legacy migration lists but no run history.
  - Personal stats correctly blend actual run data with estimates for migrations without run records.
- **Team stats UI**: Changed team stats display to show "Lines Migrated" instead of "Automation Time".
- **Test fixes**: Added `is_official_slug` mock to tracker tests so test slugs pass validation.



## [2.7.5] - 2026-01-12

### Changed
- **Stats performance**: Remove slug validation from stats reads to keep `sbm stats` fast.
- **Slug checks**: Validate slugs via devtools only before Firebase sync; invalid runs are not stored.

## [2.7.4] - 2026-01-12

### Added
- **Devtools setup**: Setup and update now auto-clone the devtools CLI if missing.

## [2.7.3] - 2026-01-12

### Added
- **Slug validation**: Filter stats to verified dealer slugs using `devtools search` (cached), so test slugs do not appear in history or team totals.

## [2.7.2] - 2026-01-12

### Changed
- **Team stats**: Count per-user migrations (from legacy slug lists + run history) so contributor totals sum to the team total.
- **UI**: Remove "(Firebase)" label from team stats header.

## [2.7.1] - 2026-01-12

### Fixed
- **Legacy counts**: Backfill migration slug lists into Firebase so historical totals match legacy `stats/*.json` counts.
- **Team totals**: Include legacy slug lists when aggregating Firebase team stats and duplicate checks.

## [2.7.0] - 2026-01-12

### Added
- **Firebase-first stats**: Realtime sync with REST fallback for non-admin users, team aggregation, and duplicate detection for bulk runs.
- **Offline queue**: Pending run uploads with background retry on subsequent CLI invocations.
- **Migration reports**: Markdown reports in `.sbm-reports/` with `index.md` table of contents.
- **Legacy import utility**: `scripts/stats/migrate_to_firebase.py` for backfilling local history.
- **History filters**: `sbm stats --history` now supports `--limit`, `--since`, `--until`, and `--user`.

### Changed
- **Stats source of truth**: Firebase replaces git-based stats files and sync flow.
- **History display**: Adds duration, lines migrated, time saved, and report path columns.

### Fixed
- **Report generation**: Report path persisted in run records for history display.

## [2.6.0] - 2026-01-09

### Added
- **Firebase Infrastructure**: Initial infrastructure setup for team-wide statistics synchronization (Epic 2).
  - Added `firebase-admin` dependency.
  - Implemented `FirebaseSettings` in configuration with environment variable support.
  - Created lazy initialization module for Firebase Admin SDK.
  - Added safe connection validation and integration tests.

## [2.5.6] - 2026-01-09

### Fixed
- **Stat Tracking**: Fixed critical bug where `lines_migrated` was always recorded as 0 in migration stats
  - Added `lines_migrated` field to `MigrationResult` dataclass with comprehensive documentation
  - Updated migration flow to properly store lines_migrated count in result object
  - Fixed CLI to use actual `result.lines_migrated` instead of hardcoded 0
  - Added backfill script and fixed 20 historical runs with 0 values (now use default 800 lines)
  - Added test coverage for edge cases (failed migrations with partial progress)
  - This resolves incorrect totals and hours saved calculations in global stats

## [2.5.5] - 2026-01-09
### Fixed
- **Dependencies**: Added `rapidfuzz` to project dependencies to resolve `ModuleNotFoundError` in downstream `di-websites-platform` scripts.

## [2.5.4] - 2026-01-09

### Fixed
- **CLI**: Fixed `UnboundLocalError` in `auto` command caused by redundant local import.

## [2.5.3] - 2026-01-08

### Added
- **Automated Batch Retry**: Added automated retry mechanism for batch migrations.
  - Automatically identifies failed slugs and updates the source file.
  - Prompts user to rerun failed migrations immediately with a 30-second timeout.
  - Defaults to "No" on timeout to support automated pipelines.
  - Notes the retry update in the migration report.

## [2.5.2] - 2026-01-08

### Changed
- **Data Location**: Moved `slugs.json` and `slugs.txt` output to `data/` directory to keep repository root clean
- **Gitignore**: Added `data/` to `.gitignore` to prevent committing run data

## [2.5.1] - 2026-01-08

### Fixed
- **Platform Directory Detection**: Fixed `get_platform_dir()` to correctly locate the repository in `~/code/dealerinspire/di-websites-platform` (was defaulting to `~/di-websites-platform`)
- **CLI Path Handling**: Fixed tilde expansion for file arguments (e.g. `sbm @~/Downloads/...`)
- **Execution Context**: Resolved git "not a git repository" errors when running `sbm` from outside the platform directory by correctly setting `cwd` for all git operations
- **Release Validation**: Removed overly strict README version check from pre-commit hooks

## [2.5.0] - 2026-01-08

### Added
- **Auto-process CSV/Excel in CLI**: Use `sbm @report.csv` to automatically extract slugs from Salesforce exports
  - Filters by "Mockup Approved" stage (skips "In QC" and other stages)
  - Opens `slugs.txt` for user review before proceeding
  - Asks for explicit confirmation before migration starts
  - Warns that `slugs.txt` will be overwritten
- **Stage Filtering**: `_read_csv()` now only includes rows where Stage = "Mockup Approved"

## [2.4.0] - 2026-01-08

### Added
- **Slug Retrieval Tool**: New `sbm get-slugs` command to retrieve dealer slugs from Excel/CSV files
  - Reads dealer account names from Excel (.xlsx, .xls) or CSV files
  - Uses devtools search command to find corresponding slugs for each dealer
  - Outputs formatted slug list to `slugs.txt` (or custom location)
  - Added pandas and openpyxl dependencies for Excel file support
  - Created `scripts/retrieve_slugs.py` with comprehensive error handling
  - Intelligent matching: handles exact matches, multiple results, and similarity scoring

## [2.3.0] - 2026-01-07

### Changed
- Add release guardrails and README rewrite

## [2.2.3] - 2026-01-06
### Fixed
- Restore commented selector blocks when declarations are active to prevent invalid CSS output.
- Fail Git setup early with a clear message when the repo is dirty.

## [2.2.2] - 2026-01-06

### Fixed

- **Batch Migration Error**: Fixed `print_timing_summary()` being called with `theme_name` argument when function takes no parameters. This was causing batch migrations to crash with "print_timing_summary() takes 0 positional arguments but 1 was given" error.

## [2.2.1] - 2026-01-06

### Fixed

- **SCSS Import Removal Bug**: Fixed `_remove_imports()` regex that was consuming indentation and whitespace from the line following @import statements. Changed trailing `\s*` to `\n?` to only remove one newline, preserving indentation and blank lines. This bug was causing selectors after imports to lose their indentation, potentially causing SCSS compilation errors.

## [2.2.0] - 2026-01-06

### Added

- **Comprehensive Migration Logging**: New `MigrationResult` dataclass with step-level error tracking (Git Setup, Docker Startup, Core Migration, SCSS Verification, Git Commit, PR Creation).
- **Enhanced Error Reporting**: Full stack traces and SCSS compilation errors now captured and included in migration reports.
- **Improved Report Format**: Reports now include summary statistics (success/fail counts), dedicated Salesforce Messages section for copy/paste, timing per slug, and branch names.
- **Step Identification on Failure**: Failed migrations now clearly indicate which step failed for easier debugging.

### Changed

- **migrate_dealer_theme Return Type**: Now returns `MigrationResult` object instead of dict for richer error information.
- **run_post_migration_workflow**: Accepts optional `result` parameter for step-level failure tracking.
- **_verify_scss_compilation_with_docker**: Now optionally returns captured SCSS compilation errors.

## [2.1.9] - 2026-01-06

### Fixed

- **Stats Reporting**: Resolved an issue where `lines_migrated` was being recorded as 0 in stats, causing "0 lines migrated" errors in reports. Fixed manual and auto migration commands to correctly propagate line counts from the SCSS processor.

## [2.1.8] - 2026-01-05

### Fixed

- **SCSS Comment Cleanup**: Fixed aggressive regex that caused valid code removal or corruption when comments were mixed with block comments on newlines. Switched to horizontal-whitespace-only matching.
- **Migration Reporting**: `sbm auto` now generates detailed migration reports in `reports/` and correctly handles new return types from migration functions.
- **Breaking Change Handling**: Added backward compatibility for migration function return types (tuple vs dict).
- **CLI**: Fixed syntax error in `cli.py` that prevented tests from running.

## [2.1.7] - 2026-01-05

### Fixed

- **Infinite Loop**: Resolved critical bug where manual verification changes were overwritten, causing an infinite reprocessing loop.
- **SCSS Processor**: Fixed naive brace counting logic that caused partial rule exclusion and syntax errors when braces appeared inside strings or comments.

## [2.1.6] - 2025-12-23

### Added

- **Scheduled Reports**: Added launchd template for 9am CST scheduled Slack reports.
- **Scheduler Test**: Verified scheduled run execution via launchd.

### Changed

- **Slack Context**: Updated context line to “Auto-SBM /sbm-stats … received”.

## [2.1.5] - 2025-12-23

### Added

- **Slack Parity**: `/sbm-stats` now reads from the same data sources as CLI stats.
- **Slash Command UX**: Added support for optional username and `top` flag.
- **Slack Layout**: Cleaner, less noisy Slack report formatting with command context.
- **Ops Helper**: Added shared reporting loader in tracker for consistent aggregation.
 - **Scheduled Reports**: Added daily/weekly/monthly Slack report scheduler.

## [2.1.3] - 2025-12-22

### Added

- **Slack Slash Commands**: Added `/sbm-stats` support using Socket Mode.
- **Reporting Improvements**: Scripts now support semantic dating (`daily`, `weekly`, `monthly`, `all`).
- **Data Accuracy**: Fixed discrepancies in reporting unique sites migrated vs runs.
- **Dependency Management**: Added `slack-bolt` and `slack-sdk` to project dependencies.

## [2.1.2] - 2025-12-19

### Added

- **Workflow Enforcement**: Injected mandatory git workflow steps (Branch/Version/Changelog) into all Agent definitions and critical workflows to enforce strict development process adherence.

## [2.1.1] - 2025-12-19

### Fixed

- **SCSS Compilation**: Fixed regex logic to correctly strip broken block comments that caused "Invalid CSS" errors.
- **Error Handling**: Improved compilation error detection to be case-insensitive, ensuring checking halts on failure.
- **Environment**: Fixed recursion loop in environment setup/health checks.

## [2.1.0] - 2025-12-19

### Added

- **Versioning Automation**: Introduced `scripts/bump_version.py` for semantic versioning.
- **Dynamic Versioning**: CLI now pulls version directly from `pyproject.toml`.
- **Changelog Command**: `sbm version --changelog` for terminal-based change tracking.
- **UI Enhancement**: Upgraded automation UI with dynamic spinners and enhanced summary panels.

### Changed

- **Fullauto Reimplementation**: Completely overhauled the full-automation mode for better reliability.
- **Map Migration Upgrade**: Significant improvements to map component detection and migration logic.
- **Project Reorganization**: Hardened background automation and reorganized project structure.
- **Stats & Tracking**: Recalibrated "time saved" metrics and added historical backfill with GitHub usernames.

### Fixed

- **CLI Polish**: Removed duplicate logs and downgraded noisy output for a cleaner experience.
- **Map Detection**: Enforced strict map detection to prevent false positives and fallback "guessing".
- **Update Logic**: Fixed misleading "Already up to date" messages and corrected verification advice.
- **Stats Dashboard**: Fixed date formatting and added "Personal Impact" titles.

## [2.0.0] - 2025-11-20

### Added

- Initial v2.0.0 release of `auto-sbm`.
- New migration engine for DealerInspire Site Builder.
- Support for SCSS/CSS variable mapping.
- Configurable environment-based settings via Pydantic.
