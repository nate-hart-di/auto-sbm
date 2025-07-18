#!/bin/bash
# Development setup script for auto-sbm v2.0
# This script sets up the development environment with all tools and pre-commit hooks

set -e

function log() { echo "[INFO] $1"; }
function warn() { echo "[WARN] $1"; }
function error() { echo "[ERROR] $1" >&2; }

log "Setting up auto-sbm development environment..."

# Check for required tools
REQUIRED_TOOLS=(git python3)
for tool in "${REQUIRED_TOOLS[@]}"; do
  if ! command -v "$tool" &> /dev/null; then
    error "$tool is required but not installed. Please install it first."
    exit 1
  fi
done

# Create virtual environment
if [ ! -d ".venv" ]; then
  log "Creating Python virtual environment (.venv)"
  python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate
log "Activated virtual environment"

# Upgrade pip
log "Upgrading pip"
pip install --upgrade pip

# Detect package manager preference
if command -v uv &> /dev/null; then
    log "Installing dependencies with UV (fast mode)"
    uv pip install -e .[dev]
else
    log "Installing dependencies with pip"
    pip install -e .[dev]
fi

# Setup environment configuration
if [ ! -f ".env" ]; then
    log "Creating .env from template"
    cp .env.example .env
    warn "Please edit .env with your GitHub token and preferences"
else
    log ".env file already exists"
fi

# Install pre-commit hooks
log "Installing pre-commit hooks"
pre-commit install

# Verify installation
log "Verifying installation..."

# Test imports
python -c "
import auto_sbm
import pydantic
import rich
print('✅ Core imports working')
"

# Test CLI
python -m auto_sbm.main --help > /dev/null && echo "✅ CLI working" || echo "❌ CLI issues"

# Run type checking
log "Running mypy type checking..."
mypy src/auto_sbm/ || warn "Type checking found issues - see output above"

# Run linting
log "Running ruff linting..."
ruff check src/ || warn "Linting found issues - see output above"

# Run tests if they exist
if [ -d "tests" ] || [ -d "src/auto_sbm/*/tests" ]; then
    log "Running tests..."
    pytest src/ -v || warn "Some tests failed - see output above"
else
    warn "No tests found - consider adding tests"
fi

echo ""
log "Development setup complete!"
echo ""
echo "🔧 Development Commands:"
echo "  ruff check src/ --fix    # Fix linting issues"
echo "  mypy src/auto_sbm/       # Type checking"
echo "  pytest src/ --cov       # Run tests with coverage"
echo "  pre-commit run --all     # Run all pre-commit hooks"
echo ""
echo "🚀 Testing Commands:"
echo "  python -m auto_sbm.main --help           # Test CLI"
echo "  python -m auto_sbm.main migrate --help   # Test migration command"
echo ""
echo "📝 Don't forget to:"
echo "  1. Edit .env with your GitHub token"
echo "  2. Review CLAUDE.md for development guidelines"
echo "  3. Check pyproject.toml for available dependencies"
