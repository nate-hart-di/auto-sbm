#!/bin/bash
set -e

LOGFILE="setup.log"
echo "[INFO] Auto-SBM v2.0 Setup - Logging all actions to $LOGFILE"
exec > >(tee -a "$LOGFILE") 2>&1

function log() { echo "[INFO] $1"; }
function warn() { echo "[WARN] $1"; }
function error() { echo "[ERROR] $1" >&2; }

# Cleanup function for failed installations
function cleanup_failed_installation() {
  log "Cleaning up failed installation..."
  rm -rf .venv
  rm -f ~/.local/bin/sbm
  rm -f .env
  rm -f .sbm_setup_complete
  log "Cleanup complete. You can re-run setup.sh"
}

# Set trap to run cleanup on failure
trap cleanup_failed_installation ERR

# Retry function for network operations
function retry_command() {
  local max_attempts=3
  local delay=5
  local command="$1"
  local description="$2"

  for ((i = 1; i <= max_attempts; i++)); do
    if eval "$command"; then
      return 0
    else
      if [[ $i -lt $max_attempts ]]; then
        warn "$description failed (attempt $i/$max_attempts). Retrying in ${delay}s..."
        sleep $delay
      else
        error "$description failed after $max_attempts attempts"
        return 1
      fi
    fi
  done
}

echo ""
echo "🚀 Auto-SBM v2.0 Setup Starting..."
echo "Step 1/7: Installing system dependencies..."
echo ""

# --- Install Homebrew (package manager for macOS) ---
function install_homebrew() {
  if ! command -v brew &> /dev/null; then
    log "Installing Homebrew (this may take a few minutes)..."
    retry_command '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"' "Homebrew installation"
    eval "$($(brew --prefix)/bin/brew shellenv)"
    log "✅ Homebrew installed successfully"
  else
    log "✅ Homebrew already installed"
  fi
}

# --- Install Required CLI Tools ---
function install_required_tools() {
  local tools=("git" "gh" "python3" "node")

  for tool in "${tools[@]}"; do
    if ! command -v "$tool" &> /dev/null; then
      log "Installing $tool via Homebrew..."
      retry_command "brew install $tool" "$tool installation"
      log "✅ $tool installed successfully"
    else
      log "✅ $tool already installed"
    fi
  done
}

# --- Install Node.js Dependencies ---
function install_node_dependencies() {
  if command -v node &> /dev/null; then
    log "Installing prettier for code formatting..."
    if ! command -v prettier &> /dev/null; then
      retry_command "npm install -g prettier" "prettier installation"
      log "✅ prettier installed successfully"
    else
      log "✅ prettier already installed"
    fi
  else
    warn "Node.js not found. Prettier installation skipped."
  fi
}

# --- Install UV for Fast Package Management ---
function install_uv() {
  if ! command -v uv &> /dev/null; then
    log "Installing UV for fast package management..."
    retry_command "brew install uv" "UV installation"
    log "✅ UV installed successfully"
  else
    log "✅ UV already installed"
  fi
}

# --- Setup Package Manager Detection ---
function setup_package_manager() {
  if command -v uv &> /dev/null; then
    PACKAGE_MANAGER="uv"
    log "Using UV for fast package management"
  elif command -v pip &> /dev/null; then
    PACKAGE_MANAGER="pip"
    log "Using pip for package management"
  else
    error "No package manager available after Python3 installation"
    exit 1
  fi
}

# Only run Homebrew installation on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
  install_homebrew
  install_required_tools
  install_node_dependencies
  install_uv
else
  warn "Non-macOS system detected. Please ensure git, gh, python3, node, prettier, and uv are installed manually."
fi

echo ""
echo "Step 2/7: Setting up package manager..."
setup_package_manager

# --- Docker Desktop (optional, for local platform dev) ---
if ! command -v docker &> /dev/null; then
  warn "Docker Desktop is not installed. If you need local DealerInspire platform development, install it from https://www.docker.com/products/docker-desktop/"
else
  log "✅ Docker Desktop found"
fi

echo ""
echo "Step 3/7: Setting up PATH and local bin directory..."

# --- Ensure ~/.local/bin exists and is in PATH ---
function setup_local_bin_path() {
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
      log "✅ ~/.local/bin added to PATH"
  else
      log "✅ ~/.local/bin already in PATH"
  fi
}

setup_local_bin_path

echo ""
echo "Step 4/7: Creating Python virtual environment..."

# --- Python Virtual Environment ---
function setup_virtual_environment() {
  if [ ! -d ".venv" ]; then
    log "Creating Python virtual environment (.venv)"
    python3 -m venv .venv --prompt auto-sbm
    log "✅ Virtual environment created"
  else
    log "✅ Virtual environment already exists"
  fi
  source .venv/bin/activate
}

setup_virtual_environment

echo ""
echo "Step 5/7: Installing Python dependencies (this may take 2-3 minutes)..."

# --- Install Auto-SBM Package ---
function install_auto_sbm() {
  log "Installing Python dependencies using $PACKAGE_MANAGER"
  pip install --upgrade pip

  # Install dependencies based on available package manager
  if [ "$PACKAGE_MANAGER" = "uv" ]; then
      log "Installing with UV (fast mode)"
      retry_command "uv pip install -e ." "UV package installation"
  else
      log "Installing with pip"
      retry_command "pip install -e ." "pip package installation"
  fi
  log "✅ Auto-SBM package installed successfully"
}

install_auto_sbm

echo ""
echo "Step 6/7: Creating global wrapper script..."

# --- Environment Configuration ---
function setup_environment_config() {
  if [ ! -f ".env" ]; then
      log "Creating .env from template"
      cp .env.example .env
      log "✅ .env file created from template"
  else
      log "✅ .env file already exists"
  fi
}

setup_environment_config

# --- Create the sbm wrapper script ---
function create_global_wrapper() {
  PROJECT_ROOT=$(pwd)
  VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
  WRAPPER_PATH="$LOCAL_BIN_DIR/sbm"

  log "Creating wrapper script at $WRAPPER_PATH"

# Using a heredoc for clarity
cat > "$WRAPPER_PATH" << EOF
#!/bin/bash
# Enhanced wrapper script for auto-sbm v2.0
# Auto-generated by setup.sh with validation

VENV_PYTHON="$VENV_PYTHON"
PROJECT_ROOT="$PROJECT_ROOT"
PROJECT_CLI_MODULE="sbm.cli"

# Check if the venv python exists
if [ ! -f "\$VENV_PYTHON" ]; then
    echo "❌ Auto-SBM virtual environment not found at \$PROJECT_ROOT" >&2
    echo "🔧 Please run: cd \$PROJECT_ROOT && bash setup.sh" >&2
    exit 1
fi

# Check if project root exists
if [ ! -d "\$PROJECT_ROOT" ]; then
    echo "❌ Auto-SBM project directory not found at \$PROJECT_ROOT" >&2
    echo "🔧 Please clone the repository or run setup.sh from the correct directory" >&2
    exit 1
fi

# Validate critical modules are available (quick check for common issues)
if ! "\$VENV_PYTHON" -c "import pydantic, click, rich, colorama, sbm.cli" 2> /dev/null; then
    echo "WARNING  Required Python package missing: colorama" >&2
    echo "WARNING  Environment health check failed. Setup will be re-run to fix issues." >&2
    echo "INFO     Running setup.sh..." >&2
    echo "🔄 Re-running setup.sh to fix missing dependencies..." >&2
    cd "\$PROJECT_ROOT" && bash setup.sh
    
    # Re-check after setup
    if ! "\$VENV_PYTHON" -c "import pydantic, click, rich, colorama, sbm.cli" 2> /dev/null; then
        echo "❌ Setup failed. Please check the error messages above." >&2
        exit 1
    fi
    echo "INFO     Setup complete. Continuing with SBM command..." >&2
fi

# GitHub authentication is handled via 'gh auth login' - no token needed in .env

# Change to project directory to ensure proper imports
cd "\$PROJECT_ROOT" || {
    echo "❌ Failed to change to project directory \$PROJECT_ROOT" >&2
    exit 1
}

# Execute the command from the project's venv, passing all arguments
"\$VENV_PYTHON" -m "\$PROJECT_CLI_MODULE" "\$@"
EOF

  # Make the wrapper executable
  chmod +x "$WRAPPER_PATH"
  log "✅ Global 'sbm' command created successfully"
}

create_global_wrapper

echo ""
echo "Step 7/7: Setting up GitHub authentication..."

# --- GitHub CLI Authentication ---
function setup_github_auth() {
  if ! gh auth status &> /dev/null; then
    warn "GitHub CLI is not authenticated. Launching 'gh auth login'..."
    gh auth login
    log "✅ GitHub CLI authenticated successfully"
  else
    log "✅ GitHub CLI already authenticated"
  fi
}

setup_github_auth

echo ""
echo "Step 8/8: Validating installation..."

# --- Validation Function ---
function validate_installation() {
  log "Validating installation..."
  
  # Test that sbm command exists and is executable
  if [ -x "$LOCAL_BIN_DIR/sbm" ]; then
    log "✅ SBM wrapper script is executable"
  else
    error "❌ SBM wrapper script not found or not executable"
    return 1
  fi
  
  # Test that the virtual environment exists
  if [ -f ".venv/bin/python" ]; then
    log "✅ Virtual environment is properly configured"
  else
    error "❌ Virtual environment not found"
    return 1
  fi
  
  # Test that configuration loads without JSON parsing errors
  if .venv/bin/python -c "from sbm.config import get_config; get_config()" 2> /dev/null; then
    log "✅ Configuration loads successfully"
  else
    error "❌ Configuration has parsing errors. Check your .env file format"
    error "    Ensure JSON arrays use proper format: GIT__DEFAULT_LABELS=[\"fe-dev\"]"
    return 1
  fi
  
  log "✅ Installation validated successfully"
}

validate_installation

echo ""
echo "🎉 Auto-SBM v2.0 Setup Complete!"
echo ""
echo "✅ All 7 steps completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. GitHub authentication is handled via 'gh auth login' (no .env editing needed)"
echo ""
echo "2. The 'sbm' command is now globally available."
echo "   You may need to restart your terminal or run: source ~/.zshrc"
echo ""
echo "3. Verify installation:"
echo "   sbm --help"
echo ""
echo "4. Run your first migration:"
echo "   sbm migrate your-theme-name"
echo ""
echo "📚 Documentation: README.md"
echo "🔧 Development: CLAUDE.md"
echo "⏱️  Setup completed in: $(date)"

touch .sbm_setup_complete
log ".sbm_setup_complete marker file created."

exit 0
