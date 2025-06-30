#!/bin/bash
set -e

# Auto-SBM Comprehensive Setup Script
# For new developers - master branch only

# --- Prerequisite Checks ---

function check_command() {
  if ! command -v "$1" &> /dev/null; then
    echo "[ERROR] $1 is not installed. Please install it before continuing." >&2
    exit 1
  fi
}

function check_python_version() {
  PYTHON_VERSION=$(python3 -c 'import sys; print("{}.{}".format(sys.version_info[0], sys.version_info[1]))')
  REQUIRED="3.8"
  if [[ $(echo -e "$PYTHON_VERSION\n$REQUIRED" | sort -V | head -n1) != "$REQUIRED" ]]; then
    echo "[ERROR] Python 3.8+ is required. Found: $PYTHON_VERSION" >&2
    exit 1
  fi
}

function check_node_version() {
  NODE_VERSION=$(node -v 2> /dev/null || echo "none")
  if [[ "$NODE_VERSION" == "none" ]]; then
    echo "[ERROR] Node.js is not installed. Please install Node.js (16+ recommended)." >&2
    exit 1
  fi
}

function check_docker() {
  if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker is not installed. Please install Docker Desktop." >&2
    exit 1
  fi
}

# --- Start Setup ---

# 1. Prerequisite checks
check_command git
check_command python3
check_python_version
check_command pip
check_command pre-commit
check_command gh
check_command just
check_node_version
check_docker

echo "[OK] All prerequisites found."

# 2. Python virtual environment
if [ ! -d ".venv" ]; then
  echo "==> Creating Python virtual environment (.venv)"
  python3 -m venv .venv
fi
source .venv/bin/activate

echo "==> Installing Python dependencies"
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Installing pre-commit hooks"
pip install pre-commit
pre-commit install

echo "==> Setup complete!"
echo ""
echo "Next steps:"
echo "1. If you have not already, clone the DealerInspire platform repo and set DI_PLATFORM_PATH if needed."
echo "2. Run: sbm doctor   # To verify your environment."
echo "3. To start a migration:"
echo "     cd ~/di-websites-platform/dealer-themes/<dealer-slug>"
echo "     sbm setup <dealer-slug> --auto-start"
echo "     sbm migrate <dealer-slug>"
echo ""
echo "For advanced AI features, add your Context7 API key and GitHub token to ~/.cursor/mcp.json as documented."
echo "See documentation/ for more details."

exit 0
