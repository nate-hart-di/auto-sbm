# Module Summaries: auto-sbm

## Core Engine (`sbm.core`)

Provides the high-level orchestration and integration logic for migrations.

- **`migration.py`**: The central workflow engine. Manages state, environment checks, and coordinates specialized migrators.
- **`git.py`**: Automates Git operations including branch creation, staging, committing, and GitHub PR generation via `GitPython` and `gh` CLI.
- **`validation.py`**: Performs pre- and post-migration integrity checks to ensure the codebase remains in a valid state.
- **`maps.py`**: specialized logic for detecting and migrating Google Maps components and related styles.

## Transformation Engine (`sbm.scss`)

Handles the low-level parsing and rewriting of SCSS files.

- **`processor.py`**: The primary transformation class. Implements variable remapping, image path resolution, and function normalization.
- **`mixin_parser.py`**: Analyzes the Common Theme and Dealer Theme to extract and adapt mixins, preventing collision and duplication.
- **`classifiers.py`**: Uses rule-based logic and regex patterns to classify styles (e.g., "Professional", "Standard") for targeted migration.

## Manufacturer Logic (`sbm.oem`)

Encapsulates requirements unique to different automotive manufacturers.

- **`factory.py`**: Implements the Factory Pattern to instantiate the correct OEM handler based on the theme slug.
- **`kia.py` / `stellantis.py`**: Specific handlers providing rules for colors, fonts, and required global styles (e.g., cookie disclaimers).

## UI & User Interaction (`sbm.ui`)

Provides the Rich-based Terminal User Interface (TUI).

- **`progress.py`**: Manages multi-threaded progress tracking with dedicated bars for SCSS transformation, Git ops, and compilation.
- **`panels.py`**: Creates status dashboards and summary tables using `rich.panel` and `rich.table`.
- **`prompts.py`**: Handles interactive user confirmations and theme selection with styled inputs.
- **`subprocess_ui.py`**: Captures and styles output from external processes (Docker, Just, AWS) for a unified TUI experience.

## Infrastructure & Helpers (`sbm.utils`)

Reusable utility modules for system-level operations.

- **`command.py`**: Robust wrapper for running shell commands with support for real-time output streaming and exit code handling.
- **`path.py`**: Resolves theme and platform directories using `pathlib-mate`.
- **`tracker.py`**: Implements a metric collection system for migration duration and success rates.
- **`timer.py`**: Provides fine-grained performance monitoring for individual migration steps.
- **`logger.py`**: Configures the unified logging system with support for both standard and Rich output.
