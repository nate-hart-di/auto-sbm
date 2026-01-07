# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
