#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/Users/nathanhart/auto-sbm"
PYTHON_BIN="$REPO_ROOT/.venv/bin/python3"

exec "$PYTHON_BIN" "$REPO_ROOT/scripts/refresh_run_metadata.py"
