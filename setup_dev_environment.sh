#!/bin/bash
#
# setup_dev_environment.sh
#
# Description:
#   This script automates the setup of the development environment for the auto-sbm project.
#   It performs the following actions:
#   1. Validates that Python 3 is installed.
#   2. Creates a Python virtual environment (.venv) if one doesn't exist.
#   3. Installs all required Python packages from requirements.txt.
#   4. Installs the 'sbm' package in editable mode for development.
#   5. Validates that Node.js and npm are installed.
#   6. Installs Node.js developer dependencies (like Prettier).
#   7. Checks for and adds a required 'sbm' alias to ~/.zshrc if not present.
#   8. Provides clear instructions for the user upon completion.
#
# Usage:
#   ./setup_dev_environment.sh
#

set -e # Exit immediately if a command exits with a non-zero status.

# --- Helper Functions ---
print_info() {
  echo -e "\033[34m[INFO]\033[0m $1"
}

print_success() {
  echo -e "\033[32m[SUCCESS]\033[0m $1"
}

print_warning() {
  echo -e "\033[33m[WARNING]\033[0m $1"
}

print_error() {
  echo -e "\033[31m[ERROR]\033[0m $1" >&2
  exit 1
}

# --- Main Setup Logic ---

# 1. Verify Python Installation
print_info "Checking for Python 3..."
if ! command -v python3 &> /dev/null; then
  print_error "Python 3 is not installed. Please install it to continue."
fi
print_success "Python 3 found."

# 2. Create Python Virtual Environment
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
  print_info "Creating Python virtual environment in '$VENV_DIR'..."
  python3 -m venv "$VENV_DIR"
  print_success "Virtual environment created."
else
  print_info "Virtual environment already exists."
fi

# Activate the virtual environment for this script's session
source "$VENV_DIR/bin/activate"

# 3. Install Python Dependencies
print_info "Installing Python dependencies from requirements.txt..."
pip install -r requirements.txt
print_success "Python dependencies installed."

# 4. Install SBM project in editable mode
print_info "Installing 'sbm' package in editable mode..."
pip install -e .
print_success "'sbm' package installed."

# 5. Verify Node.js and npm Installation
print_info "Checking for Node.js and npm..."
if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
  print_warning "Node.js or npm not found. Please install them to use JS-based tools like Prettier."
else
  print_success "Node.js and npm found."
  # 6. Install Node.js Dependencies
  print_info "Installing Node.js dev dependencies..."
  npm install
  print_success "Node.js dependencies installed."
fi

# 7. Check and add alias to .zshrc
ZSHRC_PATH="$HOME/.zshrc"
ALIAS_COMMAND="alias sbm='$(pwd)/.venv/bin/python -m sbm.cli'"
ALIAS_COMMENT="# Always use the sbm from the auto-sbm project"

if [ -f "$ZSHRC_PATH" ]; then
  if grep -qF -- "$ALIAS_COMMAND" "$ZSHRC_PATH"; then
    print_info "SBM alias already exists in $ZSHRC_PATH."
  else
    print_info "Adding SBM alias to $ZSHRC_PATH..."
    echo -e "\n$ALIAS_COMMENT\n$ALIAS_COMMAND" >> "$ZSHRC_PATH"
    print_success "Alias added. Please restart your shell or run 'source ~/.zshrc'."
  fi
else
  print_warning "$ZSHRC_PATH not found. Could not add alias. Please add it manually:"
  echo "$ALIAS_COMMAND"
fi

# --- Final Instructions ---
echo
print_success "Development environment setup is complete!"
print_info "To activate the virtual environment, run: source .venv/bin/activate"
print_info "To use the 'sbm' command globally, please restart your terminal or run: source ~/.zshrc"
echo
