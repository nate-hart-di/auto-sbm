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

# --- Ensure ~/.local/bin exists and is in PATH ---
LOCAL_BIN_DIR="$HOME/.local/bin"
ZSHRC_FILE="$HOME/.zshrc"

# Create the directory if it doesn't exist
mkdir -p "$LOCAL_BIN_DIR"

# Add to .zshrc if not already present
if ! grep -q "export PATH=\"\$HOME/.local/bin:\$PATH\"" "$ZSHRC_FILE"; then
    log "Adding ~/.local/bin to PATH in $ZSHRC_FILE"
    echo -e "\nexport PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$ZSHRC_FILE"
    # Export it for the current session as well
    export PATH="$LOCAL_BIN_DIR:$PATH"
    log "~/.local/bin added to PATH. You may need to restart your terminal for this to take effect in all new sessions."
else
    log "~/.local/bin is already in PATH."
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

log "Installing project in editable mode"
pip install -e .

# --- Create the sbm wrapper script ---
PROJECT_ROOT=$(pwd)
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
WRAPPER_PATH="$LOCAL_BIN_DIR/sbm"

log "Creating wrapper script at $WRAPPER_PATH"

# Using a heredoc for clarity
cat > "$WRAPPER_PATH" << EOF
#!/bin/bash
# Wrapper script for the auto-sbm tool
# Auto-generated by setup.sh

VENV_PYTHON="$VENV_PYTHON"
PROJECT_CLI_MODULE="sbm.cli"

# Check if the venv python exists
if [ ! -f "\$VENV_PYTHON" ]; then
    echo "Error: The Python interpreter for sbm is not found at \$VENV_PYTHON." >&2
    echo "Please try re-running the setup script from the project root." >&2
    exit 1
fi

# Execute the command from the project's venv, passing all arguments
"\$VENV_PYTHON" -m "\$PROJECT_CLI_MODULE" "\$@"
EOF

# Make the wrapper executable
chmod +x "$WRAPPER_PATH"
log "Made the wrapper script executable."

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
echo "1. The 'sbm' command is now globally available."
echo "   You may need to restart your terminal for the PATH change to take full effect."
echo "2. Run 'sbm --help' or 'sbm doctor' to verify the installation."

touch .sbm_setup_complete
log ".sbm_setup_complete marker file created."

exit 0
