# SBM Tool - AI Memory Reference

## 🚀 Quick Context Summary

**Project**: Site Builder Migration (SBM) Tool  
**Purpose**: A Python-based CLI tool to automate the migration of legacy dealer themes to the DealerInspire Site Builder platform.  
**Tech Stack**: Python, Click, GitPython, libsass  
**Repository**: `auto-sbm` (local)

---

## 🎯 Core Concepts

1.  **Modular Architecture**: The project is structured into distinct modules (`core`, `scss`, `oem`, `utils`). All core logic resides within the `sbm` package.
2.  **Centralized SCSS Processing**: All SCSS logic (parsing, categorization, transformation, validation) is handled exclusively by the `SCSSProcessor` class in `sbm/scss/processor.py`. Legacy parsers have been archived.
3.  **OEM-Specific Logic**: The tool uses a factory pattern (`sbm/oem/factory.py`) to detect the dealer's OEM and load the appropriate handler (`StellantisHandler` or `DefaultHandler`). This allows for easy extension.
4.  **Robust Git Integration**: All Git operations are handled by the `sbm/core/git.py` module, which uses the `GitPython` library for safe and reliable interactions. It does **not** use `subprocess` or `os.chdir`.
5.  **Dynamic Pathing**: The tool relies on the `DI_WEBSITES_PLATFORM_DIR` environment variable to locate the dealer themes. There are no hardcoded absolute paths. Configuration is handled via a `.env` file in the project root.
6.  **CLI Entry Point**: The command-line interface is defined in `sbm/cli.py` using `click`. The main command is `sbm`, installed via `pip install -e .`.

---

## 🚨 Critical Information & Standards

- **Primary Entry Point**: The main migration workflow is orchestrated by `migrate_dealer_theme()` in `sbm/core/migration.py`.
- **Dependencies**: All dependencies are listed in `requirements.txt`.
- **Installation**: The tool is installed as a command-line script by running `pip install -e .` in a virtual environment.
- **Configuration**: A `.env` file containing `DI_WEBSITES_PLATFORM_DIR` is required in the project root.
- **Archived Code**: Legacy scripts and modules are stored in the `archived/` directory for historical reference but are **not** part of the active codebase.

---

## 🛠️ Common Tasks

- **Running a Migration**: `sbm migrate <dealer-slug>`
- **Validating a Theme**: `sbm validate <dealer-slug>`
- **Extending for a New OEM**:
  1.  Create a new handler class in `sbm/oem/` that inherits from `BaseOEMHandler`.
  2.  Implement the required methods (e.g., `get_map_styles`, `get_brand_match_patterns`).
  3.  Register the new handler in the `_handlers` list in `sbm/oem/factory.py`.
- **Modifying SCSS Logic**: All changes to SCSS processing should be made within the `SCSSProcessor` class in `sbm/scss/processor.py`.
