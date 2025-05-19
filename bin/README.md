# SBM Shell Scripts

This directory contains shell scripts for the Site Builder Migration (SBM) tool.

## Main Scripts

- `sbm.sh`: Main entry point that orchestrates the entire migration workflow
- `site_builder_migration.sh`: Legacy compatibility wrapper for the main script

## Helper Scripts

- `start-dealer.sh`: Initializes a dealer website environment separately from the main migration
- `post-migration.sh`: Handles Git commit and push operations after a successful migration
- `create-pr.sh`: Creates a standardized PR with proper reviewers, labels, and formatting
- `test-scss-syntax.sh`: Script to test SCSS syntax validation

## Usage

The primary script to use is `sbm.sh`:

```bash
./bin/sbm.sh <dealer-slug>
```

For more options:

```bash
./bin/sbm.sh --help
```

## Notes

These scripts are synchronized with copies in the root directory for backward compatibility. Future updates should be made to the scripts in this directory.
