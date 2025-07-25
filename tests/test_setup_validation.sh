#!/bin/bash
# 
# Setup validation test for auto-sbm
# Tests the complete setup process in a clean environment
#

set -e

TEST_DIR="/tmp/auto-sbm-setup-validation-$(date +%s)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

function log() { echo "[TEST] $1"; }
function error() { echo "[ERROR] $1" >&2; }
function success() { echo "[SUCCESS] $1"; }

log "Starting setup validation test"
log "Test directory: $TEST_DIR"
log "Repository root: $REPO_ROOT"

# Create clean test environment
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

log "Cloning repository to test directory..."
git clone "$REPO_ROOT" .

log "Running setup.sh..."
if bash setup.sh; then
    success "Setup script completed without errors"
else
    error "Setup script failed"
    exit 1
fi

log "Testing sbm command availability..."
if [ -f "$HOME/.local/bin/sbm" ]; then
    success "sbm command wrapper created successfully"
else
    error "sbm command wrapper not found"
    exit 1
fi

log "Testing sbm command execution..."
if ./venv/bin/python -m sbm.cli --help > /dev/null 2>&1; then
    success "sbm CLI module loads successfully"
else
    error "sbm CLI module failed to load"
    exit 1
fi

log "Testing configuration loading..."
if ./venv/bin/python -c "
import sys
sys.path.insert(0, '.')
from sbm.config import get_settings
settings = get_settings()
print('Settings loaded:', type(settings).__name__)
"; then
    success "Configuration loads successfully"
else
    error "Configuration loading failed"
    exit 1
fi

log "Testing environment file creation..."
if [ -f ".env" ]; then
    success ".env file created successfully"
else
    error ".env file not created"
    exit 1
fi

# Cleanup
log "Cleaning up test directory..."
rm -rf "$TEST_DIR"

success "🎉 All setup validation tests passed!"
log "The setup process works correctly for new users"
