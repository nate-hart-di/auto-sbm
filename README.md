# Auto-SBM: Quick Start Guide

Welcome to Auto-SBM — the tool for automating dealer theme migrations to Site Builder format.

---

## 🚀 Getting Started

### 1. Prerequisites

- **Python 3.8+**
- **Git** (with SSH access)
- **GitHub CLI (`gh`)** (for PR automation)
- **just** (for starting dealer sites)
- **DI Websites Platform** cloned to `~/di-websites-platform` (i.e., `/Users/{youruser}/di-websites-platform`)

### 2. Setup

Clone the repo and run the setup script:

```sh
git clone git@github.com:nate-hart-di/auto-sbm.git
cd auto-sbm
bash setup.sh
```

This will:

- Create a Python virtual environment (`.venv`)
- Install all required dependencies
- Create a global `sbm` command so you can run it from any directory

> **How the Global Command Works:**
>
> The setup script places a small "wrapper" script at `~/.local/bin/sbm`. This standard directory is added to your shell's `PATH`.
>
> This wrapper automatically uses the correct Python interpreter and all the dependencies from within this project's `.venv` folder. This gives you the ability to call `sbm` from anywhere, without needing to activate the virtual environment manually.

---

## 🧭 Automated Migration Workflow (Actual Steps)

### 1. Start the Migration

No environment activation is needed. Just run the command:

```sh
sbm {slug}
```

- `{slug}` is your dealer theme (e.g., `fiatofportland`).

### 2. Site Initialization

- The tool runs `just start` to spin up the local DI Website Platform for the dealer.
- You'll see a welcome message with local URLs and credentials.

### 3. File Generation

- The tool creates new Site Builder SCSS files in your theme directory:
  - `sb-inside.scss`
  - `sb-vdp.scss`
  - `sb-vrp.scss`
- Log output confirms file creation and line counts.

### 4. Automated SCSS Migration

- The tool:
  - Converts legacy SCSS to Site Builder format
  - Processes variables into CSS custom properties
  - Converts relative image paths and enforces quotes
  - Converts all mixins to CSS (with warnings if any fail)
  - Trims and formats the output
- You'll see a summary of generated files and any warnings (e.g., mixin conversion errors)

### 5. Adding Predetermined Styles

- Cookie banner and directions row styles are added if needed (with log output for each)

### 6. Map Component Migration

- The tool searches for map shortcodes and migrates map components if found
- If none are found, it skips this step (with log output)

### 7. Manual Review Required

- The tool prints:
  - The list of generated SCSS files and their paths
  - Instructions to review and manually adjust as needed
- You must review the files in your editor
- When ready, you are prompted:
  - `Continue with the migration after manual review? [y/N]`

### 8. SCSS Re-Validation

- The tool re-validates all SCSS files after your manual review
- Prints validation results for each file (valid/invalid, line counts)
- If issues remain, you'll see a detailed validation report and can choose to fix or continue

### 9. Git Operations

- The tool prompts:
  - `Proceed with Git add, commit, and push to remote branch? [y/N]`
- If confirmed, it adds, commits, and pushes changes to a new branch
- Log output shows each git step and any errors

### 10. Pull Request Creation

- The tool prompts:
  - `Create a Pull Request for {slug}? [Y/n]`
- If confirmed, it creates a PR with reviewers and labels, and prints the PR URL

### 11. Completion

- The tool prints a final success message and PR link

---

## 🛠️ Migration Workflow

### 1. Start a Migration

Run one of the following (they are equivalent):

```sh
sbm {slug}
sbm migrate {slug}
sbm auto {slug}
```

- `{slug}` is the dealer theme slug (e.g., `fiatofportland`)
- The tool will:
  - Convert legacy SCSS to Site Builder format
  - Replace mixins, convert colors, and create the new file structure
  - Start the dealer site (unless you use `--skip-just`)
  - Prompt you to review, commit, push, and create a PR

### 2. Validate (Optional)

```sh
sbm validate {slug}
```

Checks SCSS and theme structure for issues.

### 3. Post-Migration (Optional)

```sh
sbm post-migrate {slug}
```

Manual review, re-validation, git, and PR steps if you want to run them separately.

### 🔍 Review & Refinement Phase

After the automated SCSS conversion, you'll enter a review session where you can:

- **Review the generated files** in your editor
- **Make manual improvements** as needed

**The tool will show you:**

- List of modified files with sizes
- Theme directory location
- Step-by-step instructions

### ✅ Validation Points

If unconverted SCSS is detected, you'll be prompted to:

- Continue with the migration
- Stop and fix issues
- See a detailed validation report

### 🚦 Final Steps

- **Confirm PR creation** after successful migration
- If Docker/Gulp compilation issues occur, you'll be prompted to retry
- **Note:** The tool tracks your manual changes separately from automated ones to help improve future migrations

---

## 🧩 Project Structure

```
auto-sbm/
  sbm/                # Main package
    cli.py            # CLI entry point
    core/             # Migration, git, validation
    scss/             # SCSS processing
    oem/              # OEM-specific logic
    utils/            # Utilities
  requirements.txt    # Python dependencies
  setup.sh            # Setup script
  README.md           # This file
```

---

## 🆘 Troubleshooting

- **"command not found: sbm"**: You may need to restart your terminal for the `PATH` change to take effect after the initial setup. If it still doesn't work, ensure that `~/.local/bin` is in your `PATH` by checking your `~/.zshrc` or `~/.bash_profile`.
- **GitHub CLI errors**: Run `gh auth login` and ensure you have access.
- **Python errors**: The wrapper script should handle the Python environment automatically. If you see Python errors, try re-running the `bash setup.sh` script to ensure the virtual environment is correctly built.

---

## ℹ️ More Help

- Run `sbm -h` for all commands and options.
- For issues, ask in the team chat or open an issue in this repo.
