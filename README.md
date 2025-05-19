# Site Builder Migration (SBM) Tool

A comprehensive toolset for automating dealer website migrations to the Site Builder platform.

## Overview

The SBM tool suite automates the process of migrating dealer websites to the Site Builder platform, handling:

1. Website initialization
2. Style migration and optimization
3. Map components migration
4. Git operations and PR creation

## Scripts

### Main Scripts

- **sbm.sh**: Main entry point that orchestrates the entire migration workflow
- **site_builder_migration.py**: Core Python script that handles the actual migration logic

### Helper Scripts

- **start-dealer.sh**: Initializes a dealer website environment separately from the main migration
- **post-migration.sh**: Handles Git commit and push operations after a successful migration
- **create-pr.sh**: Creates a standardized PR with proper reviewers, labels, and formatting

## Workflow

### 1. Start the Dealer Website

```bash
./start-dealer.sh <dealer-slug> prod
```

This script:

- Changes to the platform directory
- Runs `just start <dealer-slug> prod` to initialize the environment
- Shows real-time output with proper error handling
- Allows users to fix environment issues before proceeding with migration

### 2. Run the Migration

```bash
./sbm.sh <dealer-slug>
```

This master script:

- Checks if the dealer site is already started (and starts it if needed)
- Runs the migration Python script with the --skip-just flag by default
- Shows real-time output of the migration process
- Generates a detailed migration report
- Opens the modified files for review
- Offers to run post-migration steps

### 3. Commit Changes

After the migration completes, the workflow automatically offers to:

```bash
./post-migration.sh <dealer-slug>
```

This script:

- Changes to the dealer directory (not the platform root)
- Shows git status and pending changes
- Asks for confirmation before proceeding
- Commits and pushes changes to a standardized branch name

### 4. Create Pull Request

```bash
./create-pr.sh <dealer-slug> <branch-name>
```

This script:

- Changes to the dealer directory
- Formats a standardized PR title and description
- Copies the description to clipboard
- Detects the current GitHub user
- Excludes the current user from reviewers list
- Creates a draft PR with required reviewers and labels
- Opens the PR in browser for final review

## Script Details

### `start-dealer.sh`

```bash
./start-dealer.sh <dealer-slug> [environment]
```

- `dealer-slug`: The dealer theme to start
- `environment`: prod (default) or dev

### `post-migration.sh`

```bash
./post-migration.sh <dealer-slug>
```

- `dealer-slug`: The dealer theme to commit changes for
- Handles commits in the dealer theme directory
- Uses standardized commit message format

### `create-pr.sh`

```bash
./create-pr.sh <dealer-slug> <branch-name>
```

- `dealer-slug`: The dealer theme being migrated
- `branch-name`: The branch to create PR from (default: {slug}-sbm{month}{year})

## Requirements

- macOS, Linux, or Windows with Git Bash
- Python 3.6+
- GitHub CLI (`gh`) for PR creation functionality
- Platform repository checked out at `/Users/nathanhart/di-websites-platform` (configurable via `DI_WEBSITES_PLATFORM_DIR`)

## Common Tasks

### Quick Migration

```bash
./start-dealer.sh fiatofportland prod  # Start the dealer first
./sbm.sh fiatofportland                # Run the migration
```

### Create PR Only

If you've already run the migration and committed changes:

```bash
./create-pr.sh fiatofportland fiatofportland-sbm0525
```

## PR Format

PRs created by the tool follow a standardized format:

- **Title**: `{slug} SBM FE Audit`
- **Labels**: `fe-dev` (Themes label added automatically)
- **Reviewers**: Default reviewers minus the current user
- **Description**: Standardized template with what was changed and review instructions

## Prerequisites

- Python 3
- Git
- `just` command (for running the `just start` command)
- Access to the DI Websites Platform repository

## Setup

You need to specify the location of your DI Websites Platform directory. There are two ways to do this:

### Option 1: Environment Variable

Set the `DI_WEBSITES_PLATFORM_DIR` environment variable:

```bash
export DI_WEBSITES_PLATFORM_DIR=/path/to/di-websites-platform
```

You can add this to your `.bashrc`, `.zshrc`, or other shell configuration file to make it permanent.

### Option 2: Command Line Argument

Use the `--platform-dir` argument when running the tool:

```bash
./site_builder_migration.sh --platform-dir=/path/to/di-websites-platform <slug>
```

## Usage

### Basic Usage

```bash
./site_builder_migration.sh <slug>
```

Replace `<slug>` with the dealer theme slug you want to migrate.

### Migrating Multiple Themes

```bash
./site_builder_migration.sh <slug1> <slug2> <slug3>
```

### Examples

```bash
# Migrate a single theme
./site_builder_migration.sh fiatofportland

# Migrate multiple themes
./site_builder_migration.sh fiatofportland fordofsalem toyotaofportland

# Specify platform directory on command line
./site_builder_migration.sh --platform-dir=/Users/username/di-websites-platform fiatofportland
```

## What the Tool Does

For each dealer theme slug provided, the tool:

1. Performs Git operations:

   - Checks out the main branch
   - Pulls the latest changes
   - Creates a new branch named `{slug}-sbm{MMYY}` (where MMYY is the current month and year)

2. Runs the `just start {slug}` command

3. Creates necessary Site Builder SCSS files if they don't exist:

   - sb-vrp.scss
   - sb-vdp.scss
   - sb-inside.scss
   - sb-home.scss

4. Migrates styles from source files to Site Builder files:

   - Copies styles from lvdp.scss to sb-vdp.scss
   - Copies styles from vdp.scss to sb-vdp.scss (if found)
   - Copies styles from lvrp.scss to sb-vrp.scss
   - Copies styles from vrp.scss to sb-vrp.scss (if found)
   - Copies styles from inside.scss to sb-inside.scss
   - Copies styles from home.scss to sb-home.scss (if found)
   - Extracts and migrates any LVRP/LVDP/Inside page styling from style.scss to the appropriate files
   - Adds cookie disclaimer styles to sb-inside.scss and sb-home.scss
   - Replaces hardcoded color values with SiteBuilder variables

5. Dynamically discovers and migrates map components:

   - Scans theme PHP files for map-related shortcodes
   - Identifies the partials used by these shortcodes
   - Copies map partials from CommonTheme to DealerTheme preserving the directory structure
   - Migrates associated map styles to sb-inside.scss
   - Handles dealer-specific map implementations for any OEM/dealer group

6. Special Handling:
   - Creates a separate cookie-consent-homepage.css file with styles for the homepage CSS box
   - Adds Stellantis directions row styles for applicable dealer brands (Fiat, Chrysler, Dodge, Jeep, Ram)
   - Converts relative paths to absolute paths using the /wp-content/themes/ format
   - Intelligently handles font variables by extracting from theme's \_variables.scss file
   - Removes undefined SCSS variables, mixins, and functions
   - Validates PHP syntax in functions.php to prevent deployment errors

## Dynamic Map Migration

The tool automatically handles the migration of map components:

### 1. Discovery Process

- Searches for map-related shortcodes in all PHP files in the dealer theme
- Looks for patterns like `add_shortcode('full-map'`, `add_shortcode('map'`, etc.
- Extracts the paths to map partials from shortcode definitions
- If no shortcodes are found directly, looks for common map partial patterns in the CommonTheme directory

### 2. Verification

- Checks if map styles exist in style.scss, home.scss, or inside.scss
- Looks for map-related imports or direct map styles
- Skips map migration if no map components are found

### 3. Dynamic Migration

- For each map partial found, determines the OEM/dealer group from the path
- Creates the necessary directory structure in the dealer theme
- Copies the partial file from CommonTheme to DealerTheme
- Preserves the exact path structure to maintain compatibility

### 4. Style Migration

- Identifies associated map styles based on the partial path pattern
- Tries various common variations of map style paths
- Copies found styles to sb-inside.scss with proper import fixes and variable replacements
- Ensures all references use absolute paths

### 5. Optimization

- Updates variables and mixins in the migrated map styles
- Removes any undefined SCSS functions or variables
- Ensures the map components work correctly in the Site Builder environment

## Variable Replacement

The tool automatically replaces:

- SCSS variables (e.g., `$primary`) with SiteBuilder CSS variables (e.g., `var(--primary)`)
- SCSS mixins (e.g., `@include flexbox()`) with their CSS equivalents (e.g., `display: flex`)
- Hardcoded color values with appropriate variables

### Font Variables Handling

The script automatically:

1. Reads the dealer theme's `_variables.scss` file
2. Finds the imported base theme file (e.g., `_variables-2.scss`)
3. Extracts font definitions like `$heading-font` and `$maintextfont`
4. Directly replaces these variables with their actual values in the SiteBuilder files

For example, if `_variables-2.scss` defines `$heading-font: 'Lato', sans-serif;`, all instances of `$heading-font` in the migrated files will be replaced with `'Lato', sans-serif`.

### Cleanup of SCSS Functions and Mixins

The script automatically removes or converts SCSS-specific functions that aren't compatible with SiteBuilder:

- Converts `darken($primary, 10%)` to `var(--primaryhover)`
- Converts `lighten($primary, 10%)` to `var(--primary)`
- Removes unused or undefined `@include` statements
- Removes `@extend` directives
- Replaces SCSS operations like `$variable + 10px` with `auto`
- Cleans up any empty CSS rules that might be left behind after processing

This ensures the migrated CSS is compatible with SiteBuilder and avoids compilation errors.

## Path Replacement

The tool automatically converts relative paths to absolute paths with WordPress theme references:

- `../../DealerInspireCommonTheme/file.png` → `/wp-content/themes/DealerInspireCommonTheme/file.png`
- `../../DealerInspireDealerTheme/images/logo.png` → `/wp-content/themes/DealerInspireDealerTheme/images/logo.png`
- `../images/background.jpg` → `/wp-content/themes/DealerInspireDealerTheme/images/background.jpg`
- Handles both URL and @import formats in CSS/SCSS files

## Cookie Disclaimer and Consent Styles

The tool automatically adds cookie disclaimer styles to:

- sb-inside.scss
- sb-home.scss
- A separate cookie-consent-homepage.css file for use in the Homepage CSS Box

This follows the DI SiteBuilder Migration Process documentation requirements.

## PHP Syntax Validation

To prevent PHP fatal errors during deployment, the tool automatically checks functions.php for proper syntax:

- Counts opening `{` and closing `}` braces to ensure they match
- Warns if a mismatch is detected
- Automatically fixes issues by adding missing closing braces when needed
- Optionally uses `php -l` for deeper syntax validation if the PHP CLI is available
- Performs validation after map component migration and at the end of the process

This helps prevent common issues with PHP files, particularly missing closing braces that might be removed during code formatting.

## Troubleshooting

- **The script exits with an error about DI_WEBSITES_PLATFORM_DIR**:
  Make sure you've set the environment variable to the correct directory or use the `--platform-dir` command line option.

- **The Git operations fail**:
  Ensure you have the correct Git permissions and that you're connected to the repository.

- **The 'just start' command fails**:
  Verify that the 'just' command is installed and available in your PATH.

- **The style migration fails**:
  Check that the required source files exist and are readable.

- **Variable transformations not working as expected**:
  The script attempts to replace hardcoded colors with variables. You may need to manually fix some specific cases.

- **Path replacements not working correctly**:
  Some complex path patterns might need manual adjustment. Check the converted files for any unusual or broken paths.

- **Font variables not being replaced correctly**:
  Check that the dealer theme's \_variables.scss properly imports a base theme file. If not, you may need to manually update font variables.

- **SCSS mixins or functions still present in the output files**:
  Some complex SCSS constructs might not be caught by the cleanup process. You may need to manually fix these cases.

## Customization

If you need to modify the script behavior, you can edit:

- `site_builder_migration.py`: The main Python script that performs the migration
- `site_builder_migration.sh`: The shell wrapper that executes the Python script
