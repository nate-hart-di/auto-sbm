# Auto-SBM New Developer Setup Guide

Welcome to the Auto-SBM project! This guide will walk you through setting up your development environment from scratch, using only the master branch and the current project structure.

---

## 1. Prerequisites

- **Python 3.8+** (latest 3.x recommended)
- **Git** (with SSH access to GitHub)
- **Docker Desktop** (for local DealerInspire platform development)
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

## 4. Configuration

- If your DealerInspire platform is not at `~/di-websites-platform`, set:
  ```sh
  export DI_PLATFORM_PATH="/path/to/your/di-websites-platform"
  ```

---

## 5. Verify Installation

```sh
sbm doctor
```

- This checks your environment and reports any issues.

---

## 6. First Migration Workflow

### a. Navigate to a Dealer Theme

```sh
cd ~/di-websites-platform/dealer-themes/<dealer-slug>
```

### b. Pre-Migration Git Setup

```sh
sbm setup < dealer-slug > --auto-start
```

- Switches to `main` branch, pulls latest, prunes, creates a migration branch, adds the theme to sparse checkout, and starts Docker.

### c. Run Migration

```sh
sbm migrate <dealer-slug>
```

- Converts legacy SCSS to Site Builder format, replaces mixins, converts colors, creates new file structure.

### d. Review and PR

- You'll be prompted to review changes, commit, push, and create a PR with the correct template, reviewers, and labels.

---

## 7. Troubleshooting

- **"command not found: sbm"**: Add `~/.local/bin` to your PATH or re-run setup.
- **GitHub CLI errors**: Run `gh auth login` and ensure you have access.
- **Docker not starting**: Ensure Docker Desktop is running and you have access to the DealerInspire platform repo.
- **Python version errors**: Ensure you are using Python 3.8 or higher.

---

## 8. Project Structure

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

## 9. Contributing

- Create a feature branch for each change.
- Use the provided PR templates and follow code review feedback.

---
