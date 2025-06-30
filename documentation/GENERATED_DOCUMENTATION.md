# SBM Tool - Generated Documentation

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture & Components](#architecture--components)
3. [Core Workflow](#core-workflow)
4. [SCSS Processing](#scss-processing)
5. [OEM-Specific Handling](#oem-specific-handling)
6. [CLI Interface](#cli-interface)
7. [Getting Started](#getting-started)

---

## 1. Project Overview

The Site Builder Migration (SBM) tool is a Python-based command-line utility designed to automate and streamline the migration of dealer themes to the DealerInspire Site Builder platform. It provides a robust, modular, and extensible framework for handling theme migrations.

### Purpose

- Automate the migration of legacy theme styles to a modern, Site Builder-compatible format.
- Provide a consistent and repeatable process for all dealer migrations.
- Handle OEM-specific requirements through a modular handler system.
- Ensure code quality through integrated validation and robust error handling.

### Tech Stack

- **Language**: Python 3.6+
- **CLI Framework**: `click`
- **Git Integration**: `GitPython`
- **SCSS Processing**: `libsass`
- **Dependencies**: Handled via `requirements.txt`

---

## 2. Architecture & Components

The SBM tool is organized into a modular Python package (`sbm`) that promotes separation of concerns and maintainability.

- `sbm/`
  - `cli.py`: Defines the command-line interface, commands, and arguments.
  - `core/`: Contains the main application logic.
    - `migration.py`: Orchestrates the entire migration workflow.
    - `git.py`: Manages all Git operations (branching, committing, pushing) using `GitPython` and GitHub CLI integration for Pull Request creation.
    - `maps.py`: Handles the migration of map-related components and styles.
    - `validation.py`: Provides validation for PHP and SCSS files.
  - `scss/`: Houses the SCSS processing engine.
    - `processor.py`: The `SCSSProcessor` class, which intelligently inlines mixins and removes imports to create self-contained SCSS files.
  - `oem/`: Contains handlers for OEM-specific logic.
    - `factory.py`: Detects the correct OEM and creates the appropriate handler.
    - `base.py`: The abstract base class for all OEM handlers.
    - `stellantis.py`: Specific implementation for Stellantis brands.
    - `default.py`: A fallback handler for generic migrations.
  - `utils/`: A collection of shared utilities.
    - `path.py`: Handles dynamic path resolution.
    - `logger.py`: Provides centralized logging.
    - `helpers.py`: Contains miscellaneous helper functions.
    - `command.py`: A legacy helper for running shell commands.

---

## 3. Core Workflow

The main migration process is managed by the `migrate_dealer_theme` function in `sbm/core/migration.py`. It follows these steps:

1.  **OEM Detection**: The `OEMFactory` inspects the theme to determine the correct OEM handler (e.g., `StellantisHandler`, `DefaultHandler`).
2.  **Git Operations**: If not skipped, it uses `GitPython` to:
    - Check out the `main` branch and pull the latest changes.
    - Create a new feature branch for the migration (e.g., `{slug}-sbm{MMYY}`).
3.  **Local Environment Setup**: Optionally runs `just start {slug} prod` to set up the local development environment.
4.  **File Creation**: Creates the necessary `sb-inside.scss`, `sb-vdp.scss`, and `sb-vrp.scss` files in the theme directory if they don't exist.
5.  **Style Migration**: The `SCSSProcessor` is invoked to process the core style files:
    - It reads the source `style.scss` and any existing `sb-vdp.scss` or `sb-vrp.scss` files.
    - For each source file, it intelligently processes the content:
      - **Mixin Inlining**: Discovers all mixin definitions from the parent `DealerInspireCommonTheme`, parses their structure, and replaces `@include` statements with the full mixin body.
      - **Import Removal**: Aggressively removes all `@import` statements to create a standalone file.
    - The final, self-contained SCSS is written to the corresponding `sb-` files.
6.  **Component Migration**:
    - Adds predetermined styles for common components like cookie banners.
    - Migrates map components and styles based on the detected OEM handler.
7.  **Pull Request Creation** (Optional):
    - If enabled, automatically creates a GitHub Pull Request with default reviewers (`carsdotcom/fe-dev`) and labels (`fe-dev`).
    - Generates intelligent PR content based on Git changes using the Stellantis template.
    - Supports both draft and published PRs with customizable titles, bodies, reviewers, and labels.

---

## 4. SCSS Processing

All SCSS logic is centralized in the `SCSSProcessor` class (`sbm/scss/processor.py`). This class was completely redesigned to replace a fragile, regex-based system with a robust, compiler-like approach.

### Key Features

- **Mixin Inlining**: This is the core feature of the new processor. It performs a deep scan of the `DealerInspireCommonTheme`'s `css/mixins/` directory to build a library of all available mixins and their arguments. It then parses the source SCSS and replaces every `@include` statement with the corresponding full mixin body, correctly substituting any provided arguments. This eliminates the dependency on the parent theme at compile time.
- **Import Removal**: After inlining mixins, the processor removes all `@import` statements. This ensures the final `sb-*.scss` files are completely self-contained and have no external dependencies, preventing common `libsass` errors related to pathing and unresolved imports.
- **Syntax Validation**: As a final step, it uses `libsass` to perform a syntax check on the generated SCSS content, ensuring that the output is always valid and ready to be compiled by downstream tools.

---

## 5. OEM-Specific Handling

The tool is designed to be easily extendable for different Original Equipment Manufacturers (OEMs).

- **Factory Pattern**: The `OEMFactory` (`sbm/oem/factory.py`) automatically detects which OEM a dealer belongs to by inspecting the theme's `slug` and file contents.
- **Base Handler**: `BaseOEMHandler` (`sbm/oem/base.py`) defines a standard interface that all OEM handlers must implement, ensuring consistency.
- **Concrete Handlers**:
  - `StellantisHandler`: Provides specific map styles, partial patterns, and brand keywords for Stellantis dealers.
  - `DefaultHandler`: A fallback that provides generic styles and patterns suitable for most other dealers.
- **Extensibility**: Adding a new OEM is as simple as creating a new handler class and registering it in the factory.

---

## 6. CLI Interface

The command-line interface is powered by `click` and provides two main commands.

### Commands

`sbm auto <theme_name> [OPTIONS]` (Default Command)
: Runs the full, automated migration for a given theme. This is the recommended command for most migrations.

    -   **Arguments**:
        -   `THEME_NAME`: The slug of the dealer theme to migrate.
    -   **Options**:
        -   `--skip-just`: Skip running the 'just start' command.
        -   `--force-reset`: Force reset of existing Site Builder files.
        -   `--create-pr`: Create a GitHub Pull Request after successful migration (with defaults: reviewers=carsdotcom/fe-dev, labels=fe-dev).
        -   `--skip-post-migration`: Skip interactive manual review, re-validation, Git operations, and PR creation.

`sbm migrate <theme_name> [OPTIONS]` (Hidden)
: Runs the legacy migration process for a given theme.

    -   **Arguments**:
        -   `THEME_NAME`: The slug of the dealer theme to migrate.
    -   **Options**:
        -   `--dry-run`: Shows what would be done without making any changes.
        -   `--scss-only`: Only processes the SCSS files without running the full migration workflow.

`sbm validate <theme_name>`
: Validates the structure and SCSS syntax of an already migrated theme.

    -   **Arguments**:
        -   `THEME_NAME`: The slug of the dealer theme to validate.

`sbm pr <theme_name> [OPTIONS]`
: Creates a GitHub Pull Request for a given theme.

    -   **Arguments**:
        -   `THEME_NAME`: The slug of the dealer theme to create a PR for.
    -   **Options**:
        -   `-t, --title TEXT`: Custom PR title (otherwise auto-generated).
        -   `-b, --body TEXT`: Custom PR body (otherwise auto-generated).
        -   `--base TEXT`: Base branch for the Pull Request (default: main).
        -   `--head TEXT`: Head branch for the Pull Request (default: current branch).
        -   `-r, --reviewers TEXT`: Comma-separated list of reviewers (default: carsdotcom/fe-dev).
        -   `-l, --labels TEXT`: Comma-separated list of labels (default: fe-dev).
        -   `-d, --draft`: Create as draft PR.
        -   `-p, --publish`: Create as published PR (default: true).

`sbm post-migrate <theme_name> [OPTIONS]`
: Runs post-migration steps for a given theme, including manual review, re-validation, Git operations, and PR creation.

    -   **Arguments**:
        -   `THEME_NAME`: The slug of the dealer theme for post-migration workflow.
    -   **Options**:
        -   `--skip-git`: Skip Git operations (add, commit, push).
        -   `--create-pr`: Create a GitHub Pull Request after successful post-migration steps (with defaults: reviewers=carsdotcom/fe-dev, labels=fe-dev).
        -   `--skip-review`: Skip interactive manual review and re-validation.
        -   `--skip-git-prompt`: Skip prompt for Git operations.
        -   `--skip-pr-prompt`: Skip prompt for PR creation.

### Global Options

- `--verbose, -v`: Enables detailed debug logging.
- `--help, -h`: Shows the help message.
- `--config TEXT`: Path to config file (default: config.json).

---

## 7. Getting Started

1.  **Environment Setup**: Create a Python virtual environment.
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Install the Tool**: Install the `sbm` package in editable mode to make the command available.
    ```bash
    pip install -e .
    ```
4.  **Configure Environment**: Create a `.env` file in the project root with the path to your platform directory.
    ```
    DI_WEBSITES_PLATFORM_DIR="/path/to/your/di-websites-platform"
    ```
5.  **Run a Migration**:
    ```bash
    sbm migrate your-dealer-slug
    ```
