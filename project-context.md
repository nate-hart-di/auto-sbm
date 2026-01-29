# Project Context: auto-sbm

**Version:** 2.0.0
**Purpose:** AI Agent Reference for Code Development
**Last Updated:** Wednesday, January 28, 2026

---

## 🚨 CRITICAL FILE ORGANIZATION RULES

- **Tests** → `tests/test_*.py` (NEVER in root or sbm/)
- **PRP docs** → `PRPs/*.md` (NEVER in root)
- **Source code** → `sbm/*.py` (Python modules)
- **Scripts** → `sbm/scripts/` (Specialized scripts) or root for setup
- **Documentation** → `*.md` (root directory only)
- **Data** → `stats/raw/` (Raw statistical data)

**Examples of CORRECT placement:**

- Tests → `tests/test_feature.py`
- Source → `sbm/core/migration.py`
- Documentation → `README.md` (root)
- Data → `stats/raw/migration_log.json`

**Examples of WRONG placement:**

- ❌ `test_feature.py` in root
- ❌ `sbm/test_feature.py` (tests inside source)
- ❌ `feature_spec.md` in root (should be in `PRPs/` if PRP-related)
- ❌ `PRP_draft.md` in root

---

## 🏗️ Architecture Principles

- **Vertical Slice Architecture**: Features organized by business capability (e.g., `sbm/core`, `sbm/scss`), not just technical layers.
- **Scan-Transform-Verify Lifecycle**: Distinct phases for safe migration.
- **Type Safety**: Pydantic v2 models used for all data validation (`pydantic>=2.5.0`).
- **Rich UI**: Interactive terminal experience using `rich` library, with automatic CI/CD fallbacks to plain text.
- **Async Processing**: SCSS transformation and heavy I/O operations optimized for performance.

---

## 🧪 Testing Standards

- **Framework**: `pytest` (>=7.0.0).
- **Coverage Target**: 90%+ coverage required.
- **Location**: ALL tests must reside in `tests/` directory.
- **Organization**: Co-located with features tested (e.g., `tests/test_ui/`, `tests/test_core/`).
- **Markers**: Use `@pytest.mark.slow`, `@pytest.mark.integration`, `@pytest.mark.unit`.

---

## 🎨 Code Style & Quality

- **Linting & Formatting**: `ruff` is the single source of truth (replaces black + flake8).
  - Run: `ruff check src/ --fix` and `ruff format src/`.
- **Type Checking**: `mypy` with `strict = true`. All functions must have type hints.
- **Pre-commit Hooks**: Mandatory installation (`pre-commit install`) and execution.
- **Import Ordering**: Standard library → Third-party → Local application (`sbm`).

---

## 📦 Module Responsibilities

**Core (`sbm/core/`):**
- `migration.py`: Central orchestration engine; manages state and workflow.
- `git.py`: Automates Git operations (branching, commits, PRs) via GitPython.
- `validation.py`: Performs pre- and post-migration integrity checks.
- `maps.py`: Specialized logic for detecting and migrating Google Maps components.

**SCSS (`sbm/scss/`):**
- `processor.py`: Primary transformation engine; variable mapping, path resolution.
- `mixin_parser.py`: Extracts and adapts CommonTheme mixins to prevent duplication.
- `classifiers.py`: Classifies styles (e.g., "Professional", "Standard") using rule-based logic.

**OEM Handlers (`sbm/oem/`):**
- `factory.py`: Factory pattern to instantiate OEM-specific handlers.
- `base.py`, `kia.py`, `stellantis.py`: Encapsulate manufacturer-specific migration rules.

**UI (`sbm/ui/`):**
- `console.py`, `progress.py`, `panels.py`: Rich-based TUI components.

**Utils (`sbm/utils/`):**
- `command.py`: Shell command wrapper.
- `path.py`: Path resolution utilities.
- `logger.py`: Unified logging configuration.

---

## 🔒 Security & Configuration

- **Configuration**: Managed via `sbm/config.py` and environment variables (`.env`).
- **Secrets**:
  - `GITHUB_TOKEN`: Required for Git operations (if not using `gh` CLI auth).
  - `FIREBASE_API_KEY` / `FIREBASE__API_KEY`: For stats sync.
  - `SLACK_WEBHOOK_URL`: For notifications.
- **Rule**: NEVER commit secrets, tokens, or private keys. Use `.env` (ignored by git).

---

## 🚀 Development Workflow

1. **Branching**: Create `feat/`, `fix/`, or `docs/` branches. NEVER commit directly to `master`.
2. **Version Consistency**: Update `pyproject.toml` version using `scripts/bump_version.py` for functional changes.
3. **Changelog**: Update `CHANGELOG.md` with every significant change.
4. **Commits**: Make small, descriptive commits.
5. **Quality Gate**: Ensure pre-commit hooks and tests pass before pushing.

---

## ⚠️ Common Pitfalls to Avoid

- Creating test files outside the `tests/` directory.
- Creating PRP (Project Requirements Proposal) documents outside `PRPs/`.
- Working directly on the `master` branch.
- Skipping type hints on new functions or arguments (`no_implicit_optional = true`).
- Missing docstrings on public APIs (classes/functions).
- Hardcoding file paths instead of using `sbm.utils.path`.

---

## 🎯 Critical Dependencies

- **Python**: 3.9+ (Tested on 3.9, 3.10, 3.11).
- **CLI/UI**: `click` (>=8.0.0), `rich` (>=13.0.0), `rich-click`.
- **Core**: `gitpython`, `jinja2`, `pyyaml`.
- **Data/Validation**: `pydantic` (>=2.5.0), `pandas`, `firebase-admin`.
- **SCSS**: `tinycss2`, `cssutils`.
- **Dev**: `pytest`, `ruff`, `mypy`.

---

## 📍 Key File Locations

- **Entry Point**: `sbm/cli.py`
- **Main Migration Logic**: `sbm/core/migration.py`
- **Configuration**: `sbm/config.py`
- **Global Command**: `~/.local/bin/sbm`
- **CommonTheme Path (Example)**: `/Users/nathanhart/di-websites-platform/app/dealer-inspire/wp-content/themes/DealerInspireCommonTheme`

---

_Generated for AI agent consumption. For human-readable docs, see `README.md` and `CLAUDE.md`._
