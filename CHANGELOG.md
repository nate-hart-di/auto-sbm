# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
