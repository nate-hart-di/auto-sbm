---
project_name: 'auto-sbm'
user_name: 'Nate'
date: '2026-01-29T10:00:00Z'
sections_completed: ['technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'quality_style_rules', 'workflow_rules', 'anti_patterns']
status: 'complete'
rule_count: 38
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

- **Python 3.9+**: Strict type safety is mandatory.
- **Click 8.0+ / rich-click 1.7+**: For CLI command structure.
- **Rich 13.0+**: Primary UI framework. Use `SBMConsole` for all output.
- **Pydantic v2**: All data models and settings must use Pydantic v2.
- **tinycss2 / cssutils**: Core SCSS parsing and transformation engines.
- **Firebase Admin 6.5+**: For team stats synchronization.
- **Pytest 7.0+**: With 90% coverage target and specific markers (`unit`, `integration`, `slow`).

## Critical Implementation Rules

### Language-Specific Rules (Python)

- **Strict Type Hints**: All function signatures must have complete type annotations. Mypy strict mode is enforced.
- **Pydantic v2 Models**: Use Pydantic for all data validation and settings. Avoid raw dictionaries for structured data.
- **Pathlib over os.path**: Always use `pathlib` or `pathlib-mate` for filesystem paths and operations.
- **Modern Python (3.9+)**: Use `list[]` and `dict[]` for type hints instead of `List` and `Dict` from `typing`.
- **Ruff Compliance**: All code must pass `ruff check` and `ruff format` before submission.

### Framework-Specific Rules (Rich UI & SCSS Engine)

- **Console Singleton**: Always use `sbm.ui.console.get_console()` for output. Do not instantiate `rich.console.Console` directly.
- **Semantic Styling**: Use theme-defined styles (`success`, `warning`, `error`, `highlight`) instead of hardcoded hex codes or color names.
- **Progress Management**: Use `MigrationProgress` for any operation exceeding 2 seconds to provide visual feedback.
- **SCSS Transformation**: All SCSS rewriting must go through `SCSSProcessor`. Never use simple string replacement for SCSS transformation.
- **OEM Extensibility**: New manufacturer-specific logic must be implemented as a subclass of `BaseOEMHandler` and registered in `OEMHandlerFactory`.

### Testing Rules

- **🚨 tests/ Directory Only**: Never create `test_*.py` files outside the `tests/` directory.
- **90% Coverage Requirement**: All new code must be accompanied by tests. Aim for 90%+ branch coverage.
- **Pytest Markers**: Categorize tests using `@pytest.mark.unit`, `integration`, or `slow`.
- **Mocker Fixture**: Use `pytest-mock` (`mocker`) instead of standard `unittest.mock` for consistency.
- **Co-located Fixtures**: Use `conftest.py` for broad fixtures and `tests/fixtures/` for data files.
- **No Side Effects**: Integration tests must clean up any created branches, files, or temporary directories.

### Code Quality & Style Rules

- **Vertical Slice Architecture**: Organize code by capability (e.g., SCSS, OEM, UI) rather than technical layers.
- **Ruff for Everything**: Do not use Black or Flake8. Ruff handles linting, formatting, and import sorting.
- **Naming Consistency**: Follow PEP 8 strictly. Use descriptive suffixes for UI components (e.g., `*Panel`, `*Progress`).
- **Self-Documenting CLI**: Use Rich UI progress updates and status panels to describe complex operations to the user in real-time.
- **🚨 PRP First**: Major changes must reference a requirement document in the `PRPs/` directory.

### Development Workflow Rules

- **🚨 No Direct Master Commits**: Mandatory branch-based development. Use `feat/`, `fix/`, or `docs/` prefixes.
- **Atomic Commits**: Prefer small, focused commits over monolithic changes.
- **Changelog Mandate**: All code changes must be reflected in `CHANGELOG.md` under the appropriate version.
- **Version Bumping**: Functional changes require a version increment in `pyproject.toml`.
- **Pre-submission Checks**: Always run `ruff` and `mypy` locally before pushing changes.
- **Walkthrough Generation**: Provide a concise summary of changes and verification steps taken.

### Critical Don't-Miss Rules

- **SCSS Logic**: Never use string replacement for SCSS transformations. Use `tinycss2` and `SCSSProcessor`.
- **Error Handling**: Use `StatusPanel` for all terminal error reporting. Never let raw Python tracebacks reach the user.
- **Path Safety**: Always validate paths against the project root or theme directory to prevent traversal.
- **Resource Management**: Ensure all file handles and network connections (Firebase) are closed properly, even on failure.
- **CI/CD Detection**: Always verify `console.is_interactive` before prompting for user input to prevent hanging in automation.

---

## Usage Guidelines

**For AI Agents:**

- Read this file before implementing any code
- Follow ALL rules exactly as documented
- When in doubt, prefer the more restrictive option
- Update this file if new patterns emerge

**For Humans:**

- Keep this file lean and focused on agent needs
- Update when technology stack changes
- Review quarterly for outdated rules
- Remove rules that become obvious over time

Last Updated: 2026-01-29T10:00:00Z
