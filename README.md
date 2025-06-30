# Auto-SBM New Developer Setup Guide

Welcome to the Auto-SBM project! This guide will walk you through setting up your development environment from scratch, using only the master branch and the current project structure.

---

## 1. Prerequisites

- **Python 3.8+** (latest 3.x recommended)
- **Git** (with SSH access to GitHub)
- **GitHub CLI (`gh`)** (for PR automation)

---

## 2. Clone the Repository

```sh
git clone git@github.com:nate-hart-di/auto-sbm.git
cd auto-sbm
```

---

## 3. Set Up Python Environment

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 4. Verify Installation

```sh
sbm doctor
```

- This checks your environment and reports any issues.

---

## 5. First Migration Workflow

### a. Run Migration

```sh
sbm {slug}
```

OR

```sh
sbm migrate {slug}
```

OR

```sh
sbm auto {slug}
```

- Converts legacy SCSS to Site Builder format, replaces mixins, converts colors, creates new file structure.
- You'll be prompted to review changes, commit, push, and create a PR with the correct template, reviewers, and labels.

---

## 6. Troubleshooting

- **"command not found: sbm"**: Add `~/.local/bin` to your PATH or re-run setup.
- **GitHub CLI errors**: Run `gh auth login` and ensure you have access.
- **Python version errors**: Ensure you are using Python 3.8 or higher.

---

## 7. Project Structure

```
auto-sbm/
  sbm/                # Main package
    cli.py            # CLI entry point
    config.py         # Config management
    core/             # Core logic (migration, git, validation)
    scss/             # SCSS processing
    oem/              # OEM-specific logic
    utils/            # Utilities (logging, helpers)
  requirements.txt    # Python dependencies
  README.md           # Main project readme
```

---

## 8. Contributing

- Create a feature branch for each change.
- Use the provided PR templates and follow code review feedback.

---

For more details, see in-tool help (`sbm --help`).
