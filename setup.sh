#!/bin/bash
set -e

# Auto-SBM Comprehensive Setup Script
# For new developers - master branch only
# This script will install all required tools using Homebrew if missing, configure your shell, and set up the Python environment.

LOGFILE="setup.log"
echo "[INFO] Logging all actions to $LOGFILE"
exec > >(tee -a "$LOGFILE") 2>&1

# --- Helper Functions ---
function log() {
  echo "[INFO] $1"
}
function warn() {
  echo "[WARN] $1"
}
function error() {
  echo "[ERROR] $1" >&2
}

# --- Homebrew ---
if ! command -v brew &> /dev/null; then
  log "Homebrew not found. Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$($(brew --prefix)/bin/brew shellenv)"
else
  log "Homebrew found."
fi

# --- Required Packages ---
REQUIRED_BREW_PACKAGES=(git gh pre-commit node just python)
for pkg in "${REQUIRED_BREW_PACKAGES[@]}"; do
  if ! brew list --formula | grep -q "^$pkg$"; then
    log "$pkg not found. Installing $pkg via Homebrew..."
    brew install "$pkg"
  else
    log "$pkg already installed."
  fi
  # For python, ensure python3 is available
  if [[ "$pkg" == "python" ]]; then
    if ! command -v python3 &> /dev/null; then
      error "python3 not found after brew install. Please check your Python installation."
      exit 1
    fi
  fi
  # For node, ensure npm is available
  if [[ "$pkg" == "node" ]]; then
    if ! command -v npm &> /dev/null; then
      error "npm not found after node install. Please check your Node.js installation."
      exit 1
    fi
  fi
  # For just, ensure just is available
  if [[ "$pkg" == "just" ]]; then
    if ! command -v just &> /dev/null; then
      error "just not found after install. Please check your just installation."
      exit 1
    fi
  fi
  # For gh, ensure gh is available
  if [[ "$pkg" == "gh" ]]; then
    if ! command -v gh &> /dev/null; then
      error "gh not found after install. Please check your GitHub CLI installation."
      exit 1
    fi
  fi
  # For pre-commit, ensure pre-commit is available
  if [[ "$pkg" == "pre-commit" ]]; then
    if ! command -v pre-commit &> /dev/null; then
      error "pre-commit not found after install. Please check your pre-commit installation."
      exit 1
    fi
  fi
  # For git, ensure git is available
  if [[ "$pkg" == "git" ]]; then
    if ! command -v git &> /dev/null; then
      error "git not found after install. Please check your git installation."
      exit 1
    fi
  fi
  log "$pkg installation check complete."
done

# --- Docker Desktop ---
if ! command -v docker &> /dev/null; then
  warn "Docker Desktop is not installed. Please download and install it from https://www.docker.com/products/docker-desktop/ and start Docker Desktop before continuing."
else
  log "Docker Desktop found."
fi

# --- Ensure ~/.local/bin is in PATH in ~/.zshrc ---
ZSHRC="$HOME/.zshrc"
if ! grep -q 'export PATH="$HOME/.local/bin:$PATH"' "$ZSHRC"; then
  log "Adding ~/.local/bin to PATH in $ZSHRC"
  echo -e '\n# Add local Python bin to PATH for sbm and other tools\nexport PATH="$HOME/.local/bin:$PATH"' >> "$ZSHRC"
  log "Appended export statement to $ZSHRC."
else
  log "~/.local/bin already in PATH in $ZSHRC."
fi

# --- Python Virtual Environment ---
if [ ! -d ".venv" ]; then
  log "Creating Python virtual environment (.venv)"
  python3 -m venv .venv
fi
source .venv/bin/activate

log "Installing Python dependencies"
pip install --upgrade pip
pip install -r requirements.txt

log "Installing pre-commit hooks"
pip install pre-commit
pre-commit install

# --- GitHub CLI Authentication ---
if ! gh auth status &> /dev/null; then
  warn "GitHub CLI is not authenticated. Launching 'gh auth login'..."
  gh auth login
else
  log "GitHub CLI is already authenticated."
fi

log "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Restart your terminal or run 'source ~/.zshrc' to update your PATH."
echo "2. Run: sbm doctor   # To verify your environment."
echo "3. To start a migration:"
echo "     cd ~/di-websites-platform/dealer-themes/<dealer-slug>"
echo "     sbm setup <dealer-slug> --auto-start"
echo "     sbm migrate <dealer-slug>"
echo ""
echo "See documentation/ for more details."

exit 0
