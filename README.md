# Auto-SBM: Quick Start Guide

Welcome to Auto-SBM — the tool for automating dealer theme migrations to Site Builder format.

---

## 🚀 Getting Started

### 1. Prerequisites

- **Python 3.8+**
- **Git** (with SSH access)
- **GitHub CLI (`gh`)** (for PR automation)
- **just** (for starting dealer sites)

### 2. Setup

Clone the repo and run the setup script:

```sh
git clone git@github.com:nate-hart-di/auto-sbm.git
cd auto-sbm
bash setup.sh
```

This will:

- Create a Python virtual environment
- Install all dependencies
- Ensure your PATH is set up
- Authenticate GitHub CLI if needed

> **Note on Virtual Environments:**
>
> - If you also work in `di-websites-platform`, its virtualenv will auto-activate when you `cd` into that directory. This will not interfere with Auto-SBM.
> - The `sbm` alias always uses the correct Python environment for Auto-SBM, so you can run `sbm` commands from **anywhere** in your terminal.
> - **Tip:** Always use the `sbm` alias (not `python -m sbm.cli`) to avoid any environment issues.

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

- **"command not found: sbm"**: Add `~/.local/bin` to your PATH or re-run setup.
- **GitHub CLI errors**: Run `gh auth login` and ensure you have access.
- **Python errors**: Make sure you are using Python 3.8 or higher and your virtualenv is activated.

---

## ℹ️ More Help

- Run `sbm --help` for all commands and options.
- For issues, ask in the team chat or open an issue in this repo.
