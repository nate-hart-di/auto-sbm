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
    - `git.py`: Manages all Git operations (branching, committing, pushing) using `GitPython`.
    - `maps.py`: Handles the migration of map-related components and styles.
    - `validation.py`: Provides validation for PHP and SCSS files.
  - `scss/`: Houses the SCSS processing engine.
    - `processor.py`: The `SCSSProcessor` class, which parses, categorizes, transforms, and validates all SCSS content.
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
4.  **File Creation**: Creates the necessary `sb-inside.scss`, `sb-vdp.scss`, and `sb-vrp.scss` files in the theme directory.
5.  **Style Migration**: The `SCSSProcessor` is invoked to:
    - Read the source `style.scss`.
    - Extract and categorize all SCSS rules into 'inside', 'vdp', or 'vrp'.
    - Apply transformations (e.g., convert variables, replace mixins).
    - Validate the resulting SCSS.
    - Write the processed styles to the corresponding `sb-` files.
6.  **Component Migration**:
    - Adds predetermined styles for common components like cookie banners.
    - Migrates map components and styles based on the detected OEM handler.

---

## 4. SCSS Processing

All SCSS logic is centralized in the `SCSSProcessor` class (`sbm/scss/processor.py`). This class provides a comprehensive solution for handling styles, replacing a collection of legacy parsers.

### Key Features

- **Syntax Validation**: Uses `libsass` to compile SCSS and catch syntax errors before writing files.
- **Block Extraction**: A state machine parses the SCSS content to extract balanced blocks, correctly handling nested rules and comments.
- **Rule Categorization**: Uses regex patterns to categorize each block as belonging to `vdp` (Vehicle Detail Page), `vrp` (Vehicle Results Page), or `inside` (all other pages).
- **Transformation**: A built-in transformation engine handles:
  - Replacing SCSS variables (`$variable`) with CSS variables (`var(--variable)`).
  - Replacing common mixins (`@include flexbox`) with standard CSS.
  - Converting relative image paths to absolute WordPress theme paths.
- **Atomic File Writes**: Ensures that files are only written if all processing and validation steps succeed.

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

`sbm migrate <theme_name> [OPTIONS]`
: Runs the full migration process for a given theme.

    -   **Arguments**:
        -   `THEME_NAME`: The slug of the dealer theme to migrate.
    -   **Options**:
        -   `--dry-run`: Shows what would be done without making any changes.
        -   `--scss-only`: Only processes the SCSS files without running the full migration workflow.

`sbm validate <theme_name>`
: Validates the structure and SCSS syntax of an already migrated theme.

    -   **Arguments**:
        -   `THEME_NAME`: The slug of the dealer theme to validate.

### Global Options

- `--verbose, -v`: Enables detailed debug logging.
- `--help`: Shows the help message.

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
