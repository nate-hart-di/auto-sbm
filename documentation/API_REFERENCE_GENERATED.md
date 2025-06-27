# SBM Tool - Generated API Reference

## Table of Contents

1. [CLI (`sbm.cli`)](#cli-sbmcli)
2. [Core Migration (`sbm.core.migration`)](#core-migration-sbmcoremigration)
3. [SCSS Processor (`sbm.scss.processor`)](#scss-processor-sbmscssprocessor)
4. [OEM Handling (`sbm.oem`)](#oem-handling-sbmoem)
5. [Git Operations (`sbm.core.git`)](#git-operations-sbmcoregit)
6. [Map Migration (`sbm.core.maps`)](#map-migration-sbmcoremaps)
7. [Utilities (`sbm.utils`)](#utilities-sbmutils)

---

## 1. CLI (`sbm.cli`)

Defines the command-line interface for the SBM tool.

### `cli()`

The main Click command group.

### `migrate(theme_name, dry_run, scss_only)`

Migrates a theme from Site Builder to a custom theme structure.

- **`theme_name`** (`str`): The slug of the dealer theme to migrate.
- **`--dry-run`** (`bool`): If set, shows what would be done without making changes.
- **`--scss-only`** (`bool`): If set, only processes the SCSS files.

### `validate(theme_name)`

Validates the theme structure and SCSS syntax.

- **`theme_name`** (`str`): The slug of the dealer theme to validate.

---

## 2. Core Migration (`sbm.core.migration`)

Orchestrates the main migration workflow.

### `migrate_dealer_theme(slug, skip_just, force_reset, skip_git, skip_maps, oem_handler)`

The main entry point for a dealer theme migration.

- **`slug`** (`str`): The dealer theme slug.
- **`skip_just`** (`bool`): If `True`, skips running the `just start` command.
- **`force_reset`** (`bool`): If `True`, resets existing Site Builder SCSS files.
- **`skip_git`** (`bool`): If `True`, skips all Git operations.
- **`skip_maps`** (`bool`): If `True`, skips migrating map components.
- **`oem_handler`** (`BaseOEMHandler`, optional): A specific OEM handler to use. If `None`, it will be auto-detected.
- **Returns** (`bool`): `True` if migration is successful, `False` otherwise.

### `migrate_styles(slug)`

Handles the style migration using the `SCSSProcessor`.

- **`slug`** (`str`): The dealer theme slug.
- **Returns** (`bool`): `True` if successful.

---

## 3. SCSS Processor (`sbm.scss.processor`)

### `SCSSProcessor(slug)`

A production-grade class for parsing, transforming, and validating SCSS.

#### `process_style_scss(theme_dir)`

The main method to process a `style.scss` file. It reads the file, categorizes the content, transforms it, and returns a dictionary of processed SCSS ready for writing.

- **`theme_dir`** (`str`): The path to the theme directory.
- **Returns** (`Dict[str, str]`): A dictionary where keys are filenames (`sb-inside.scss`, etc.) and values are the processed SCSS content.

#### `write_files_atomically(theme_dir, files)`

Writes the processed SCSS files to the theme directory. It validates each file's syntax with `libsass` before writing to prevent corrupting files.

- **`theme_dir`** (`str`): The path to the theme directory.
- **`files`** (`Dict[str, str]`): The dictionary of filenames and content from `process_style_scss`.
- **Returns** (`bool`): `True` if all files were written successfully.

#### `validate_scss_syntax(content)`

Validates a string of SCSS content using `libsass`.

- **`content`** (`str`): The SCSS content to validate.
- **Returns** (`Tuple[bool, Optional[str]]`): A tuple containing a boolean for validity and an optional error message.

---

## 4. OEM Handling (`sbm.oem`)

Manages OEM-specific logic and configurations.

### `OEMFactory` (`sbm.oem.factory`)

A factory class for creating the appropriate OEM handler.

#### `create_handler(slug, dealer_info)`

Creates a handler based on brand information in the slug or provided info.

- **Returns** (`BaseOEMHandler`): An instance of a specific handler (e.g., `StellantisHandler`) or `DefaultHandler`.

#### `detect_from_theme(slug, platform_dir)`

Detects the OEM by scanning the content of the theme's files for brand-specific patterns.

- **Returns** (`BaseOEMHandler`): The handler with the most pattern matches.

### `BaseOEMHandler` (`sbm.oem.base`)

The abstract base class for all OEM handlers. Defines the required interface.

#### `get_map_styles()`

#### `get_directions_styles()`

#### `get_map_partial_patterns()`

#### `get_shortcode_patterns()`

#### `get_brand_match_patterns()`

### `StellantisHandler` (`sbm.oem.stellantis`)

A concrete implementation for Stellantis brands, providing custom styles and patterns.

### `DefaultHandler` (`sbm.oem.default`)

A fallback handler providing generic styles that work for most dealers.

---

## 5. Git Operations (`sbm.core.git`)

Handles all Git interactions using the `GitPython` library.

### `checkout_main_and_pull()`

Checks out the `main` branch and pulls the latest changes from `origin`.

### `create_branch(slug)`

Creates and checks out a new branch for the migration. Handles cases where the branch already exists.

- **Returns** (`tuple[bool, str]`): A tuple of success status and the branch name.

### `commit_changes(slug, message)`

Adds and commits all changes within the specific dealer's theme directory.

### `push_changes(branch_name)`

Pushes the specified branch to the `origin` remote and sets it to track.

---

## 6. Map Migration (`sbm.core.maps`)

Handles the migration of map-related partials and styles.

### `migrate_map_components(slug, oem_handler)`

The main entry point for map migration. It finds shortcodes, identifies partials, copies them from `CommonTheme`, and migrates their styles.

### `find_map_shortcodes(slug, shortcode_patterns)`

Searches theme PHP files for map-related shortcodes using patterns from the OEM handler.

### `identify_map_partials(slug, oem_handler)`

Identifies the paths to map partials referenced in the theme.

### `copy_map_partials(slug, partials)`

Copies the identified map partials from `DealerInspireCommonTheme` into the dealer theme, preserving the directory structure.

### `migrate_map_styles(slug, oem_handler)`

Appends the OEM-specific map styles to the `sb-inside.scss` file.

---

## 7. Utilities (`sbm.utils`)

Shared helper functions used across the application.

- **`sbm.utils.path`**:
  - `get_platform_dir()`: Gets the platform directory from the `DI_WEBSITES_PLATFORM_DIR` environment variable.
  - `get_dealer_theme_dir(slug)`: Constructs the absolute path to a dealer's theme directory.
- **`sbm.utils.logger`**:
  - `setup_logger()`: Configures the centralized logger for console and file output.
- **`sbm.utils.helpers`**:
  - `get_branch_name(slug)`: Generates a standardized Git branch name.
  - And other miscellaneous helpers.
