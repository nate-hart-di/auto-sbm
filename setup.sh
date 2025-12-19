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
  log "Checking Node.js version and installing prettier..."
  
  # Function to install NVM if not present
  function install_nvm_if_needed() {
    if [ ! -s "$HOME/.nvm/nvm.sh" ] && ! command -v nvm &> /dev/null; then
      log "Installing NVM (Node Version Manager)..."
      if command -v brew &> /dev/null; then
        retry_command "brew install nvm" "NVM installation via Homebrew"
        # Create NVM directory if it doesn't exist
        mkdir -p "$HOME/.nvm"
        log "✅ NVM installed via Homebrew"
      else
        # Install via curl if Homebrew not available
        retry_command 'curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash' "NVM installation via curl"
        log "✅ NVM installed via curl"
      fi
      # Source NVM for current session
      export NVM_DIR="$HOME/.nvm"
      [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    fi
  }

  # Function to install Node.js 18 via nvm if available
  function install_node_via_nvm() {
    install_nvm_if_needed
    
    if [ -s "$HOME/.nvm/nvm.sh" ]; then
      log "NVM detected. Installing Node.js 18..."
      source "$HOME/.nvm/nvm.sh"
      retry_command "nvm install 18" "Node.js 18 installation via nvm"
      retry_command "nvm use 18" "Switching to Node.js 18"
      retry_command "nvm alias default 18" "Setting Node.js 18 as default"
      return 0
    elif command -v nvm &> /dev/null; then
      log "NVM command available. Installing Node.js 18..."
      retry_command "nvm install 18" "Node.js 18 installation via nvm"
      retry_command "nvm use 18" "Switching to Node.js 18"
      retry_command "nvm alias default 18" "Setting Node.js 18 as default"
      return 0
    fi
    return 1
  }
  
  # Check if Node.js exists and get version
  if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version | sed 's/v//')
    MAJOR_VERSION=$(echo $NODE_VERSION | cut -d. -f1)
    log "Found Node.js version $NODE_VERSION"
  else
    log "Node.js not found, will attempt installation..."
    MAJOR_VERSION=0
  fi
  
  # If Node.js version is < 18, try to install/upgrade
  if [ "$MAJOR_VERSION" -lt 18 ]; then
    if [ "$MAJOR_VERSION" -gt 0 ]; then
      warn "Node.js version $NODE_VERSION detected. Prettier requires Node.js 18+."
    fi
    
    # Try different installation methods in order of preference
    if brew list node &> /dev/null; then
      log "Upgrading Node.js via Homebrew..."
      retry_command "brew upgrade node" "Node.js upgrade"
    elif install_node_via_nvm; then
      log "✅ Node.js 18 installed via nvm"
    elif command -v brew &> /dev/null; then
      log "Installing Node.js 18 via Homebrew..."
      retry_command "brew install node" "Node.js installation"
    else
      error "Cannot install Node.js automatically. Please install manually:"
      error "  1. Install Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
      error "  2. Install Node.js: brew install node"
      error "  3. Or install nvm and run: nvm install 18 && nvm use 18"
      error "  4. Or download from https://nodejs.org/"
      return 1
    fi
    
    # Verify installation worked
    if command -v node &> /dev/null; then
      NEW_NODE_VERSION=$(node --version | sed 's/v//')
      NEW_MAJOR_VERSION=$(echo $NEW_NODE_VERSION | cut -d. -f1)
      if [ "$NEW_MAJOR_VERSION" -lt 18 ]; then
        error "Node.js installation/upgrade failed. Version is still $NEW_NODE_VERSION (need 18+)"
        return 1
      fi
      log "✅ Node.js version $NEW_NODE_VERSION is now available"
    else
      error "Node.js installation failed - command not found after installation"
      return 1
    fi
  else
    log "✅ Node.js version $NODE_VERSION is compatible (18+ required)"
  fi
  
  # Install prettier globally
  log "Installing prettier for code formatting..."
  if ! command -v prettier &> /dev/null; then
    # Ensure npm/node paths are available
    export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
    
    # Try multiple approaches to handle certificate issues
    log "Attempting prettier installation with certificate handling..."
    
    # First try: disable strict SSL (corporate networks often need this)
    if npm install -g prettier --strict-ssl=false 2>/dev/null; then
      log "✅ prettier installed with relaxed SSL"
    # Second try: use different registry
    elif npm install -g prettier --registry http://registry.npmjs.org/ 2>/dev/null; then
      log "✅ prettier installed using HTTP registry"
    # Third try: update certificates and retry
    elif npm config set cafile "" && npm install -g prettier 2>/dev/null; then
      log "✅ prettier installed after clearing certificate config"
    # Fourth try: use Homebrew as fallback
    elif command -v brew &> /dev/null && brew install prettier 2>/dev/null; then
      log "✅ prettier installed via Homebrew"
    else
      warn "prettier installation failed due to certificate issues"
      warn "Manual solutions:"
      warn "  1. Corporate network: npm config set strict-ssl false"
      warn "  2. Certificate update: npm config set registry http://registry.npmjs.org/"
      warn "  3. Or install via Homebrew: brew install prettier"
      return 1
    fi
    
    # Verify installation worked
    if command -v prettier &> /dev/null; then
      PRETTIER_VERSION=$(prettier --version 2>/dev/null || echo "unknown")
      log "✅ prettier installed successfully (version $PRETTIER_VERSION)"
    else
      warn "prettier installation verification failed"
    fi
  else
    PRETTIER_VERSION=$(prettier --version 2>/dev/null || echo "unknown")
    log "✅ prettier already installed (version $PRETTIER_VERSION)"
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
  # Check if UV is available globally
  if command -v uv &> /dev/null; then
    PACKAGE_MANAGER="uv"
    log "Using UV for fast package management"
  else
    # Virtual environment should have been created, just assume pip works
    # Modern Python venv always includes pip, so don't overthink it
    PACKAGE_MANAGER="pip"
    log "Using pip for package management (from virtual environment)"
  fi
}

# Only run Homebrew installation on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
  install_homebrew
  install_required_tools
  install_uv
  install_node_dependencies  # Moved after required tools installation
else
  warn "Non-macOS system detected. Please ensure git, gh, python3, node 18+, prettier, and uv are installed manually."
fi

echo ""
echo "Step 2/7: Setting up package manager (after virtual environment)..."
# Package manager setup moved to after venv creation

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
  
  # Add prettier/node wrapper functions if not already present
  if ! grep -q "##### PRETTIER/NODE WRAPPER #####" "$ZSHRC_FILE"; then
      log "Adding prettier/node wrapper functions to $ZSHRC_FILE"
      cat >> "$ZSHRC_FILE" << 'ZSHRC_EOF'

##### PRETTIER/NODE WRAPPER #####
prettier() {
  if ! command -v nvm > /dev/null; then
    echo "NVM not available. Running with current Node version."
    command prettier "$@"
    return $?
  fi
  local CURRENT_NODE=$(nvm current)
  nvm use 22 > /dev/null 2>&1 || echo "Failed to switch to Node 22"
  command prettier "$@"
  local EXIT_CODE=$?
  nvm use "$CURRENT_NODE" > /dev/null 2>&1 || echo "Failed to revert to $CURRENT_NODE"
  return $EXIT_CODE
}

npx() {
  if [ "$1" = "prettier" ]; then
    shift
    prettier "$@"
  else
    command npx "$@" || echo "npx command failed"
  fi
}
ZSHRC_EOF
      log "✅ prettier/node wrapper functions added"
  else
      log "✅ prettier/node wrapper functions already present"
  fi
  
  # Add NVM configuration if not already present
  if ! grep -q "##### NVM CONFIGURATION #####" "$ZSHRC_FILE"; then
      log "Adding NVM configuration to $ZSHRC_FILE"
      cat >> "$ZSHRC_FILE" << 'ZSHRC_EOF'

##### NVM CONFIGURATION #####
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/nvm.sh.d/bash_completion" ] && \. "$NVM_DIR/nvm.sh.d/bash_completion"  # This loads nvm bash_completion

# Auto-switch Node versions based on .nvmrc file
autoload -U add-zsh-hook
load-nvmrc() {
  local node_version="$(nvm version)"
  local nvmrc_path="$(nvm_find_nvmrc)"

  if [ -n "$nvmrc_path" ]; then
    local nvmrc_node_version=$(nvm version "$(cat "${nvmrc_path}")")

    if [ "$nvmrc_node_version" = "N/A" ]; then
      nvm install
    elif [ "$nvmrc_node_version" != "$node_version" ]; then
      nvm use
    fi
  elif [ "$node_version" != "$(nvm version default)" ]; then
    echo "Reverting to nvm default version"
    nvm use default
  fi
}
add-zsh-hook chpwd load-nvmrc
load-nvmrc
ZSHRC_EOF
      log "✅ NVM configuration added"
  else
      log "✅ NVM configuration already present"
  fi
  
  # Add Homebrew paths for M1/M2/M3 Macs if not already present
  if ! grep -q "##### HOMEBREW CONFIGURATION #####" "$ZSHRC_FILE"; then
      log "Adding Homebrew configuration to $ZSHRC_FILE"
      cat >> "$ZSHRC_FILE" << 'ZSHRC_EOF'

##### HOMEBREW CONFIGURATION #####
# Add Homebrew to PATH (supports both Intel and Apple Silicon Macs)
if [[ -d "/opt/homebrew" ]]; then
    export PATH="/opt/homebrew/bin:$PATH"
    export PATH="/opt/homebrew/sbin:$PATH"
elif [[ -d "/usr/local/Homebrew" ]]; then
    export PATH="/usr/local/bin:$PATH"
    export PATH="/usr/local/sbin:$PATH"
fi
ZSHRC_EOF
      log "✅ Homebrew configuration added"
  else
      log "✅ Homebrew configuration already present"
  fi
  
  # Add essential development aliases if not already present
  if ! grep -q "##### AUTO-SBM DEVELOPMENT ALIASES #####" "$ZSHRC_FILE"; then
      log "Adding development aliases to $ZSHRC_FILE"
      # Use current directory as project root for aliases
      local PROJECT_ROOT=$(pwd)
      cat >> "$ZSHRC_FILE" << ZSHRC_EOF

##### ADDED BY AUTO-SBM #####
alias gs='git status'
alias ga='git addall'
alias gp='git push --set-upstream origin HEAD'
alias gpo='git push --set-upstream origin HEAD'
alias gb='git branch'
alias gpl='git pull'
alias gr='git restore'
alias grh='git reset --hard'
alias gco='git checkout'

# Auto-SBM specific (using actual installation directory)
alias sbm-dev="cd $PROJECT_ROOT && source .venv/bin/activate"
alias sbm-test="cd $PROJECT_ROOT && source .venv/bin/activate && python -m pytest tests/ -v"
ZSHRC_EOF
      log "✅ Development aliases added"
  else
      log "✅ Development aliases already present"
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

# Now detect package manager after venv is created
setup_package_manager

echo ""
echo "Step 5/7: Installing Python dependencies (this may take 2-3 minutes)..."

# --- Install Auto-SBM Package ---
function install_auto_sbm() {
  log "Installing Python dependencies using $PACKAGE_MANAGER"
  
  # Make sure we're in the virtual environment
  source .venv/bin/activate
  
  if [ "$PACKAGE_MANAGER" = "uv" ]; then
      log "Installing with UV (fast mode)"
      retry_command "uv pip install -e ." "UV package installation"
  else
      log "Installing with pip from virtual environment"
      # Try pip first, fallback to pip3, use python -m pip as last resort
      if command -v pip &> /dev/null; then
          retry_command "pip install --upgrade pip" "pip upgrade"
          retry_command "pip install -e ." "pip package installation"
      elif command -v pip3 &> /dev/null; then
          retry_command "pip3 install --upgrade pip" "pip3 upgrade"
          retry_command "pip3 install -e ." "pip3 package installation"
      else
          retry_command "python -m pip install --upgrade pip" "python -m pip upgrade"
          retry_command "python -m pip install -e ." "python -m pip package installation"
      fi
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
# We use exit code instead of string matching to allow for warnings during import
if ! "$VENV_PYTHON" -c "import pydantic, click, rich, colorama, sbm.cli" &>/dev/null; then
    IMPORT_ERROR=\$("$VENV_PYTHON" -c "import pydantic, click, rich, colorama, sbm.cli" 2>&1)
    echo "WARNING  Environment health check failed: \$IMPORT_ERROR" >&2
    echo "WARNING  Re-running setup.sh to fix missing dependencies..." >&2
    cd "$PROJECT_ROOT" && bash setup.sh
    
    # Re-check after setup
    if ! "$VENV_PYTHON" -c "import pydantic, click, rich, colorama, sbm.cli" &>/dev/null; then
        IMPORT_ERROR_2=\$("$VENV_PYTHON" -c "import pydantic, click, rich, colorama, sbm.cli" 2>&1)
        echo "❌ Setup failed after retry: \$IMPORT_ERROR_2" >&2
        echo "Please run manually: cd $PROJECT_ROOT && (.venv/bin/pip install -e . || .venv/bin/pip3 install -e .)" >&2
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

# Clean environment from any active venv to prevent conflicts
# This ensures auto-sbm runs in isolation even when called from another venv
unset VIRTUAL_ENV
unset PYTHONPATH
unset PYTHONHOME

# Remove any other venv's bin directory from PATH and add auto-sbm's venv
export PATH="\$PROJECT_ROOT/.venv/bin:\$(echo \$PATH | tr ':' '\n' | grep -v '/\.venv/bin' | tr '\n' ':' | sed 's/:$//')"

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
  if .venv/bin/python -c "from sbm.config import get_config; get_config()"; then
    log "✅ Configuration loads successfully"
  else
    error "❌ Configuration has parsing errors. See traceback above for details."
    error "    Ensure JSON arrays use proper format: GIT__DEFAULT_LABELS=[\"fe-dev\"]"
    return 1
  fi
  
  log "✅ Installation validated successfully"
}

validate_installation

echo ""
echo "🎉 Auto-SBM v2.0 Setup Complete!"
echo ""
echo "✅ All 8 steps completed successfully!"
echo ""
echo "🔄 IMPORTANT: Restart your terminal or run:"
echo "   source ~/.zshrc"
echo ""
echo "📋 Next steps:"
echo ""
echo "2. Run your first migration:"
echo "   sbm your-theme-name"
echo ""
echo "3. Development shortcuts now available:"
echo "   sbm-dev     # Quick access to auto-sbm development"
echo "   sbm-test    # Run auto-sbm tests"
echo "   gs, ga, gc  # Git shortcuts"
echo ""
echo "🔧 What was configured:"
echo "   ✅ Auto-SBM CLI globally available"
echo "   ✅ Node.js 18+ and prettier installed"
echo "   ✅ NVM configuration with auto-switching"
echo "   ✅ Homebrew paths for M1/M2/M3 Macs"
echo "   ✅ Development aliases and shortcuts"
echo "   ✅ GitHub CLI authentication"
echo ""
echo "📚 Documentation: README.md"
echo "🔧 Development: CLAUDE.md"
echo "⏱️  Setup completed in: $(date)"

touch .sbm_setup_complete
log ".sbm_setup_complete marker file created."

exit 0
