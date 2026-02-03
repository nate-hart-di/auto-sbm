# CLI & Configuration Overview: auto-sbm

## Command Line Interface

The `sbm` tool provides a comprehensive suite of commands for theme migration and maintenance.

### Core Commands

| Command        | Description                                   | Key Options                             |
| :------------- | :-------------------------------------------- | :-------------------------------------- |
| `auto`         | Full automated migration workflow.            | `--yes`, `--create-pr`, `--skip-just`   |
| `migrate`      | Targeted migration of specific themes.        | `--force-reset`, `--skip-maps`          |
| `reprocess`    | Re-runs transformations on existing SB files. | N/A                                     |
| `validate`     | Checks SCSS syntax and theme structure.       | `--check-exclusions`, `--show-excluded` |
| `post-migrate` | Manual review and Git/PR workflow.            | `--skip-git`, `--create-pr`             |

### Utility Commands

| Command   | Description                                           |
| :-------- | :---------------------------------------------------- |
| `stats`   | Displays migration metrics and team performance.      |
| `diff`    | Shows differences between legacy and migrated styles. |
| `cleanup` | Removes temporary snapshots and cache files.          |
| `update`  | Manually triggers a check for tool updates.           |

## Configuration System

`auto-sbm` uses a dual-layer configuration system powered by **Pydantic v2**, allowing for type-safe settings via environment variables or `.env` files.

### Configuration Categories

#### Git Settings (`git`)

- `github_token`: Personal Access Token for PR creation.
- `github_org`: target organization (default: `dealerinspire`).
- `default_reviewers`: List of users/teams for PR review.
- `default_labels`: Labels applied to new PRs.

#### Logging Settings (`logging`)

- `use_rich`: Toggles advanced TUI logging.
- `log_level`: Severity filter (DEBUG, INFO, etc.).
- `mask_sensitive`: Automatically hides tokens in log output.

#### Progress Settings (`progress`)

- `update_interval`: Frequency of UI refreshes.
- `thread_timeout`: Safety limit for background migration tasks.

### Environment Integration

Settings can be overridden using the prefix `AUTOSBM__`:

- Example: `AUTOSBM__LOGGING__LOG_LEVEL=DEBUG`
- Loads from: `~/.auto-sbm/.env` or project root `.env`.

## Developer Notes

- **Lazy Loading**: Configuration is loaded only when needed via the `get_settings()` singleton.
- **Backward Compatibility**: A `Config` wrapper class is provided to support legacy modules that still expect a dictionary-like interface.
- **Health Checks**: The CLI automatically checks for required system tools (`git`, `just`, `docker`) and Python dependencies on startup.
