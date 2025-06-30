#!/bin/bash
set -e

LOGFILE="setup.log"
echo "[INFO] Logging all actions to $LOGFILE"
exec > >(tee -a "$LOGFILE") 2>&1

function log() { echo "[INFO] $1"; }
function warn() { echo "[WARN] $1"; }
function error() { echo "[ERROR] $1" >&2; }

# --- Homebrew (for macOS only) ---
if [[ "$OSTYPE" == "darwin"* ]]; then
  if ! command -v brew &> /dev/null; then
    log "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$($(brew --prefix)/bin/brew shellenv)"
  else
    log "Homebrew found."
  fi
fi

# --- Required CLI Tools ---
REQUIRED_TOOLS=(git gh python3)
for tool in "${REQUIRED_TOOLS[@]}"; do
  if ! command -v "$tool" &> /dev/null; then
    error "$tool is required but not installed. Please install it and re-run this script."
    exit 1
  fi
  log "$tool is installed."
done

# --- Docker Desktop (optional, for local platform dev) ---
if ! command -v docker &> /dev/null; then
  warn "Docker Desktop is not installed. If you need local DealerInspire platform development, install it from https://www.docker.com/products/docker-desktop/"
else
  log "Docker Desktop found."
fi

# --- Ensure ~/.local/bin is in PATH in ~/.zshrc ---
ZSHRC="$HOME/.zshrc"
PATH_ADDED=false
if ! grep -q 'export PATH="$HOME/.local/bin:$PATH"' "$ZSHRC"; then
  log "Adding ~/.local/bin to PATH in $ZSHRC"
  echo -e '\n# Add local Python bin to PATH for sbm and other tools\nexport PATH="$HOME/.local/bin:$PATH"' >> "$ZSHRC"
  log "Appended export statement to $ZSHRC."
  PATH_ADDED=true
else
  log "~/.local/bin already in PATH in $ZSHRC."
fi

# --- Source ~/.zshrc if it was modified ---
if [ "$PATH_ADDED" = true ]; then
  log "Sourcing $ZSHRC to update PATH in current shell."
  source "$ZSHRC"
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
echo "1. You can now use sbm and other CLI tools immediately (PATH updated)."
echo "2. Run: sbm doctor   # To verify your environment."
echo "3. To start a migration:"
echo "     sbm {slug}"
echo "     sbm migrate {slug}"
echo "     sbm auto {slug}"
echo ""
echo "For more details, see in-tool help (sbm --help)."

touch .sbm_setup_complete
log ".sbm_setup_complete marker file created."

exit 0
