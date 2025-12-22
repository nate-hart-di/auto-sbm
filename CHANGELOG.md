# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
