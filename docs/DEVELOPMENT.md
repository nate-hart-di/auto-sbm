# Development

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Lint and Format

```bash
ruff check . --fix
ruff format .
```

## Type Checking

```bash
mypy sbm/
```

## Tests

```bash
python -m pytest tests/ -v
python -m pytest tests/ --cov=sbm --cov-report=html
python -m pytest tests/test_migration.py -v
```

## Contributing

1. Create a feature branch.
2. Run lint, type checks, and tests.
3. Open a pull request.

## Release Workflow

Version bumps are mandatory for code changes. Use the bump script so
`pyproject.toml`, `CHANGELOG.md`, and `README.md` stay aligned.

```bash
# Bugfix (patch)
python3 scripts/bump_version.py --type bugfix --notes "Fix <short summary>"

# Feature (minor)
python3 scripts/bump_version.py --type feature --notes "Add <short summary>"

# Major
python3 scripts/bump_version.py --type major --notes "Break <short summary>"
```

Validation hook:

```bash
python3 scripts/validate_release.py --staged
```

## References

- `CLAUDE.md`
- `docs/PRPs`
