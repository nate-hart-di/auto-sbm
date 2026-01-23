#!/bin/bash
set -e

LOGFILE="setup.log"
# Read version from pyproject.toml (single source of truth)
SBM_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/' 2>/dev/null || echo "dev")
echo "[INFO] Auto-SBM v$SBM_VERSION Setup - Logging all actions to $LOGFILE"
exec > >(tee -a "$LOGFILE") 2>&1

function log() { echo "[INFO] $1"; }
function warn() { echo "[WARN] $1"; }
function error() { echo "[ERROR] $1" >&2; }

# Cleanup function for failed installations
function cleanup_failed_installation() {
  log "Cleaning up failed installation..."
  # Keep wrapper and .env to avoid breaking existing installs when optional steps fail.
  rm -rf .venv
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

# Ensure Homebrew is discoverable in non-interactive shells
if [ -d "/opt/homebrew/bin" ]; then
  export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"
elif [ -d "/usr/local/bin" ]; then
  export PATH="/usr/local/bin:/usr/local/sbin:$PATH"
fi

# --- Pull Latest Changes from Git ---
function pull_latest_changes() {
  log "Pulling latest changes from Git..."

  # Check if we're in a git repository
  if [ ! -d ".git" ]; then
    warn "Not a git repository. Skipping git pull."
    return 0
  fi

  # Fetch the latest changes
  if ! git fetch origin; then
    warn "Failed to fetch from origin. Continuing with existing code..."
    return 0
  fi

  # Determine the default branch (master or main)
  local default_branch
  if git show-ref --verify --quiet refs/remotes/origin/master; then
    default_branch="master"
  elif git show-ref --verify --quiet refs/remotes/origin/main; then
    default_branch="main"
  else
    warn "Could not determine default branch. Continuing with existing code..."
    return 0
  fi

  # Check if there's a rebase in progress - abort it
  if [ -d ".git/rebase-merge" ] || [ -d ".git/rebase-apply" ]; then
    warn "Git rebase in progress. Aborting rebase..."
    git rebase --abort 2>/dev/null || true
  fi

  # Check if there's a merge in progress - abort it
  if [ -f ".git/MERGE_HEAD" ]; then
    warn "Git merge in progress. Aborting merge..."
    git merge --abort 2>/dev/null || true
  fi

  # Discard any local changes - users shouldn't be modifying this repo
  # First, try a clean pull
  if git pull --rebase origin "$default_branch" 2>/dev/null; then
    log "✅ Successfully pulled latest changes"
    return 0
  fi

  # If that fails, try without rebase
  if git pull origin "$default_branch" 2>/dev/null; then
    log "✅ Successfully pulled latest changes (merge)"
    return 0
  fi

  # If normal pull fails, force reset to remote - prefer remote changes always
  warn "Normal pull failed. Force resetting to origin/$default_branch..."
  warn "⚠️  Discarding any local changes (users should not modify this repo)"

  # Reset to the remote branch, discarding all local changes
  git reset --hard "origin/$default_branch" 2>/dev/null
  git clean -fd -e .env -e .venv -e data/ 2>/dev/null  # Keep local env and venv

  if [ $? -eq 0 ]; then
    log "✅ Force reset to origin/$default_branch complete"
  else
    error "Failed to reset to remote. Please manually run: git reset --hard origin/$default_branch"
    return 1
  fi
}

echo ""
echo "🚀 Auto-SBM v${SBM_VERSION} Setup Starting..."
echo "Step 0/10: Pulling latest changes..."
pull_latest_changes

echo ""
echo "Step 1/10: Installing system dependencies..."
echo ""

# --- Ensure Devtools CLI is available ---
function ensure_devtools_cli() {
  local devtools_dir="$HOME/code/dealerinspire/feature-dev-shared-scripts/devtools-cli"
  local devtools_script="$devtools_dir/devtools"

  if [ -f "$devtools_script" ]; then
    log "✅ Devtools CLI already available"
    return 0
  fi

  warn "Devtools CLI not found. Skipping install (optional)."
  warn "If needed, install manually: git clone git@bitbucket.org:dealerinspire/feature-dev-shared-scripts.git \$HOME/code/dealerinspire/feature-dev-shared-scripts"
  return 0
}

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
    if npm install -g prettier --strict-ssl=false 2> /dev/null; then
      log "✅ prettier installed with relaxed SSL"
    # Second try: use different registry
    elif npm install -g prettier --registry http://registry.npmjs.org/ 2> /dev/null; then
      log "✅ prettier installed using HTTP registry"
    # Third try: update certificates and retry
    elif npm config set cafile "" && npm install -g prettier 2> /dev/null; then
      log "✅ prettier installed after clearing certificate config"
    # Fourth try: use Homebrew as fallback
    elif command -v brew &> /dev/null && brew install prettier 2> /dev/null; then
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
      PRETTIER_VERSION=$(prettier --version 2> /dev/null || echo "unknown")
      log "✅ prettier installed successfully (version $PRETTIER_VERSION)"
    else
      warn "prettier installation verification failed"
    fi
  else
    PRETTIER_VERSION=$(prettier --version 2> /dev/null || echo "unknown")
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
  ensure_devtools_cli
  install_uv
  install_node_dependencies # Moved after required tools installation
else
  warn "Non-macOS system detected. Please ensure git, gh, python3, node 18+, prettier, and uv are installed manually."
fi

echo ""
echo "Step 2/10: Setting up package manager (after virtual environment)..."
# Package manager setup moved to after venv creation

# --- Docker Desktop (optional, for local platform dev) ---
if ! command -v docker &> /dev/null; then
  warn "Docker Desktop is not installed. If you need local DealerInspire platform development, install it from https://www.docker.com/products/docker-desktop/"
else
  log "✅ Docker Desktop found"
fi

echo ""
echo "Step 3/10: Setting up PATH and local bin directory..."

# --- Ensure ~/.local/bin exists and is in PATH ---
function setup_local_bin_path() {
  LOCAL_BIN_DIR="$HOME/.local/bin"
  ZSHRC_FILE="$HOME/.zshrc"
  ZPROFILE_FILE="$HOME/.zprofile"

  # Create the directory if it doesn't exist
  mkdir -p "$LOCAL_BIN_DIR"

  # Add to .zshrc and .zprofile so login shells also inherit PATH
  for shell_file in "$ZSHRC_FILE" "$ZPROFILE_FILE"; do
    if [ ! -f "$shell_file" ]; then
      touch "$shell_file"
    fi
    if ! grep -q "export PATH=\"\$HOME/.local/bin:\$PATH\"" "$shell_file"; then
      log "Adding ~/.local/bin to PATH in $shell_file"
      printf '\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$shell_file"
      log "✅ ~/.local/bin added to PATH in $shell_file"
    else
      log "✅ ~/.local/bin already in PATH in $shell_file"
    fi
  done
  # Export it for the current session as well
  export PATH="$LOCAL_BIN_DIR:$PATH"

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

  # Add NVM configuration if not already present and NVM is available
  if ! grep -q "##### NVM CONFIGURATION #####" "$ZSHRC_FILE"; then
    if [ -s "$HOME/.nvm/nvm.sh" ] || command -v nvm &> /dev/null; then
      log "Adding NVM configuration to $ZSHRC_FILE"
      cat >> "$ZSHRC_FILE" << 'ZSHRC_EOF'

##### NVM CONFIGURATION #####
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/nvm.sh.d/bash_completion" ] && \. "$NVM_DIR/nvm.sh.d/bash_completion"  # This loads nvm bash_completion

# Auto-switch Node versions based on .nvmrc file
autoload -U add-zsh-hook
load-nvmrc() {
  if ! command -v nvm > /dev/null; then
    return
  fi
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
      log "✅ NVM not installed; skipping NVM configuration"
    fi
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

  # Add essential development aliases - only if not already present
  # This check ensures we don't duplicate the entire block on re-runs
  if ! grep -q "##### AUTO-SBM DEVELOPMENT ALIASES #####" "$ZSHRC_FILE"; then
    log "Adding development aliases to $ZSHRC_FILE"
    # Use current directory as project root for aliases
    local PROJECT_ROOT=$(pwd)

    # Add aliases conditionally - won't override user's existing aliases
    cat >> "$ZSHRC_FILE" << 'ZSHRC_EOF'

##### AUTO-SBM DEVELOPMENT ALIASES #####
# Git shortcuts - only set if not already defined by user
if ! alias gs &>/dev/null; then alias gs='git status'; fi
if ! alias ga &>/dev/null; then alias ga='git add'; fi
if ! alias gp &>/dev/null; then alias gp='git push --set-upstream origin HEAD'; fi
if ! alias gb &>/dev/null; then alias gb='git branch'; fi
if ! alias gpl &>/dev/null; then alias gpl='git pull'; fi
if ! alias gr &>/dev/null; then alias gr='git restore'; fi
if ! alias gco &>/dev/null; then alias gco='git checkout'; fi

# Git commit function - only if not already defined
if ! type gc &>/dev/null; then
  gc() {
    git commit -m "$*"
  }
fi
ZSHRC_EOF

    # Add sbm-specific aliases with dynamic PROJECT_ROOT
    cat >> "$ZSHRC_FILE" << ZSHRC_EOF

# Auto-SBM development helpers
if ! alias sbm-dev &>/dev/null; then
  alias sbm-dev="cd $PROJECT_ROOT && source .venv/bin/activate"
fi
if ! alias sbm-test &>/dev/null; then
  alias sbm-test="cd $PROJECT_ROOT && source .venv/bin/activate && python -m pytest tests/ -v"
fi
ZSHRC_EOF

    log "✅ Development aliases added (respecting existing aliases)"
  else
    log "✅ Development aliases already present (skipping)"
  fi
}

setup_local_bin_path

echo ""
echo "Step 4/10: Creating Python virtual environment..."

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
echo "Step 5/10: Installing Python dependencies (this may take 2-3 minutes)..."

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

# --- Verify rich-click is installed ---
function ensure_rich_click() {
  log "Verifying rich-click dependency..."

  # Make sure we're in the virtual environment
  source .venv/bin/activate

  if ! python -c "import rich_click" &>/dev/null; then
    warn "rich-click not found; installing..."
    if [ "$PACKAGE_MANAGER" = "uv" ]; then
      retry_command "uv pip install rich-click" "rich-click installation"
    else
      retry_command "python -m pip install rich-click" "rich-click installation"
    fi
  fi
}

ensure_rich_click

echo ""
echo "Step 5.5/8: Installing pre-commit hooks..."

# --- Install Pre-commit Hooks ---
function install_precommit_hooks() {
  log "Installing pre-commit hooks for code quality..."

  # Make sure we're in the virtual environment
  source .venv/bin/activate

  # Install pre-commit hooks
  if command -v pre-commit &> /dev/null; then
    pre-commit install --hook-type pre-commit --hook-type pre-push
    if [ $? -eq 0 ]; then
      log "✅ Pre-commit hooks installed successfully"
    else
      warn "⚠️  Failed to install pre-commit hooks"
    fi
  else
    warn "⚠️  pre-commit not found in virtual environment"
    warn "    This is expected if pre-commit is not in dev dependencies"
  fi
}

install_precommit_hooks

echo ""
echo "Step 6/10: Creating global wrapper script..."

# --- Environment Configuration ---
function setup_environment_config() {
  if [ ! -f ".env" ]; then
    log "Creating .env from template"
    cp .env.example .env
    log "✅ .env file created from template"
  else
    log "✅ .env file already exists"
  fi

  # Ensure FIREBASE__DATABASE_URL is set to the real default (not placeholder)
  local DEFAULT_DB_URL="https://auto-sbm-default-rtdb.firebaseio.com"
  if [ -f ".env" ]; then
    local ENV_DB_URL
    ENV_DB_URL=$(grep -E "^FIREBASE__DATABASE_URL=" .env | tail -n 1 | cut -d'=' -f2- | tr -d '"' | tr -d "'")
    if [ -z "$ENV_DB_URL" ] || [ "$ENV_DB_URL" = "https://your-project-id-default-rtdb.firebaseio.com" ]; then
      sed -i.bak "/^FIREBASE__DATABASE_URL=/d" .env
      rm -f .env.bak
      echo "FIREBASE__DATABASE_URL=$DEFAULT_DB_URL" >> .env
      export FIREBASE__DATABASE_URL="$DEFAULT_DB_URL"
      log "✅ FIREBASE__DATABASE_URL set to default"
    else
      export FIREBASE__DATABASE_URL="$ENV_DB_URL"
    fi
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
if ! PYTHONPATH="$PROJECT_ROOT" "$VENV_PYTHON" -c "import pydantic, click, rich, colorama, rich_click, sbm.cli" &>/dev/null; then
    IMPORT_ERROR=\$(PYTHONPATH="$PROJECT_ROOT" "$VENV_PYTHON" -c "import pydantic, click, rich, colorama, rich_click, sbm.cli" 2>&1)
    echo "WARNING  Environment health check failed: \$IMPORT_ERROR" >&2
    echo "WARNING  Re-running setup.sh to fix missing dependencies..." >&2
    cd "$PROJECT_ROOT" && bash setup.sh

    # Re-check after setup
    if ! PYTHONPATH="$PROJECT_ROOT" "$VENV_PYTHON" -c "import pydantic, click, rich, colorama, rich_click, sbm.cli" &>/dev/null; then
        IMPORT_ERROR_2=\$(PYTHONPATH="$PROJECT_ROOT" "$VENV_PYTHON" -c "import pydantic, click, rich, colorama, rich_click, sbm.cli" 2>&1)
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
unset PYTHONHOME
unset PYTHONPATH

# Remove any other venv's bin directory from PATH and add auto-sbm's venv
export PATH="\$PROJECT_ROOT/.venv/bin:\$(echo \$PATH | tr ':' '\n' | grep -v '/\.venv/bin' | tr '\n' ':' | sed 's/:$//')"
export PYTHONPATH="\$PROJECT_ROOT"

# Execute the command from the project's venv, passing all arguments
"\$VENV_PYTHON" -m "\$PROJECT_CLI_MODULE" "\$@"
EOF

  # Make the wrapper executable
  chmod +x "$WRAPPER_PATH"
  log "✅ Global 'sbm' command created successfully"
}

create_global_wrapper

echo ""
echo "Step 7/10: Setting up GitHub authentication..."

# --- GitHub CLI Authentication ---
function setup_github_auth() {
  if ! gh auth status &> /dev/null; then
    warn "GitHub CLI is not authenticated. Launching 'gh auth login'..."
    gh auth login
    log "✅ GitHub CLI authenticated successfully"
  else
    log "✅ GitHub CLI already authenticated"
  fi

  # Ensure required scopes for workflow dispatch and artifact download
  log "Ensuring GitHub auth scopes include workflow and repo..."
  gh auth refresh -s workflow,repo &> /dev/null || true
}

# --- Ensure GitHub auth scopes + repo permissions are correct ---
function ensure_github_auth_ready() {
  local repo="nate-hart-di/auto-sbm"
  local required_scopes="repo workflow"
  local scopes=""
  local permission=""

  log "Validating GitHub auth scopes and repo access..."

  # Ensure active auth exists
  if ! gh auth status --active --hostname github.com &> /dev/null; then
    warn "GitHub auth status not healthy. Re-authenticating..."
    gh auth login -h github.com -s workflow,repo
  fi

  # Check scopes on active account
  scopes=$(gh auth status --json hosts --jq '.hosts["github.com"][] | select(.active==true) | .scopes' 2>/dev/null || true)
  if [[ -z "$scopes" ]] || ! echo "$scopes" | grep -q "workflow" || ! echo "$scopes" | grep -q "repo"; then
    warn "Missing required GitHub scopes (need: $required_scopes). Refreshing..."
    gh auth refresh -s workflow,repo &> /dev/null || true
    scopes=$(gh auth status --json hosts --jq '.hosts["github.com"][] | select(.active==true) | .scopes' 2>/dev/null || true)
    if [[ -z "$scopes" ]] || ! echo "$scopes" | grep -q "workflow" || ! echo "$scopes" | grep -q "repo"; then
      warn "Scopes still missing. Forcing re-login with required scopes..."
      gh auth logout -h github.com &> /dev/null || true
      gh auth login -h github.com -s workflow,repo
    fi
  fi

  # Verify repo access and permission level
  if ! permission=$(gh repo view "$repo" --json viewerPermission -q '.viewerPermission' 2>/dev/null); then
    warn "❌ GitHub repo access check failed for $repo"
    warn "   You may be logged into the wrong GitHub account or missing repo access."
    return 1
  fi

  case "$permission" in
    ADMIN|MAINTAIN|WRITE)
      log "✅ Repo access confirmed ($permission)"
      ;;
    *)
      warn "❌ Insufficient repo permission ($permission) for workflow dispatch."
      warn "   Ask for write/maintain/admin access to $repo."
      return 1
      ;;
  esac

  return 0
}

# --- Fetch Firebase API Key via GitHub Actions artifact ---
function fetch_firebase_api_key_from_github_actions() {
  local workflow_file="fetch-firebase-api-key.yml"
  local artifact_name="firebase-api-key"
  local download_dir="/tmp/auto-sbm-firebase-key"
  local key_file="$download_dir/firebase_api_key.txt"
  FIREBASE_FETCH_OK=0

  log "Fetching Firebase API key via GitHub Actions..."

  if ! command -v gh &> /dev/null; then
    warn "❌ GitHub CLI not found"
    return 0
  fi

  if ! gh workflow list --json path -q '.[].path' | grep -q "$workflow_file"; then
    warn "❌ GitHub Actions workflow not found: $workflow_file"
    return 0
  fi

  local start_time
  start_time=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  # Trigger workflow run
  if ! gh workflow run "$workflow_file" &> /dev/null; then
    warn "❌ Failed to trigger GitHub Actions workflow: $workflow_file"
    warn "Attempting to refresh GitHub auth scopes (workflow, repo) and retry..."
    gh auth refresh -s workflow,repo &> /dev/null || true
    if ! gh workflow run "$workflow_file" &> /dev/null; then
      warn "❌ Retry failed to trigger GitHub Actions workflow: $workflow_file"
      warn "Attempting to use latest successful workflow run artifact (if available)..."
      # Fall back to latest successful run artifact without triggering a new run
      local latest_success_id
      latest_success_id=$(gh run list --workflow "$workflow_file" --limit 10 --json databaseId,conclusion -q 'map(select(.conclusion=="success")) | .[0].databaseId')
      if [ -z "$latest_success_id" ]; then
        warn "❌ No successful workflow runs found to download artifact from"
        return 0
      fi
      run_id="$latest_success_id"
      # Skip the polling loop and jump to download
      rm -rf "$download_dir"
      mkdir -p "$download_dir"
      if ! gh run download "$run_id" -n "$artifact_name" -D "$download_dir" &> /dev/null; then
        warn "❌ Failed to download artifact from latest successful run"
        return 0
      fi
      if [ ! -f "$key_file" ]; then
        warn "❌ Firebase API key file missing in artifact"
        return 0
      fi
      local firebase_key
      firebase_key="$(cat "$key_file" | tr -d '\r\n')"
      if [ -z "$firebase_key" ]; then
        warn "❌ Firebase API key file is empty"
        return 0
      fi
      log "✅ Firebase API key fetched from latest successful workflow run"
      if [ -f .env ]; then
        sed -i.bak "/^FIREBASE__API_KEY=/d" .env
        rm -f .env.bak
      fi
      echo "FIREBASE__API_KEY=$firebase_key" >> .env
      export FIREBASE__API_KEY="$firebase_key"
      FIREBASE_FETCH_OK=1
      return 0
    fi
  fi

  # Wait for latest run to complete
  local run_id=""
  for _ in {1..30}; do
    run_id=$(gh run list --workflow "$workflow_file" --limit 5 --json databaseId,createdAt -q 'map(select(.createdAt > "'"$start_time"'")) | .[0].databaseId')
    if [ -n "$run_id" ]; then
      run_status=$(gh run view "$run_id" --json status -q '.status')
      run_conclusion=$(gh run view "$run_id" --json conclusion -q '.conclusion')
      if [ "$run_status" = "completed" ]; then
        if [ "$run_conclusion" != "success" ]; then
          warn "❌ GitHub Actions run failed (conclusion: $run_conclusion)"
          return 1
        fi
        break
      fi
    fi
    sleep 2
  done

  if [ -z "$run_id" ]; then
    warn "❌ Could not find a completed GitHub Actions run"
    return 0
  fi

  rm -rf "$download_dir"
  mkdir -p "$download_dir"

  if ! gh run download "$run_id" -n "$artifact_name" -D "$download_dir" &> /dev/null; then
    warn "❌ Failed to download artifact: $artifact_name"
    return 0
  fi

  if [ ! -f "$key_file" ]; then
    warn "❌ Firebase API key file missing in artifact"
    return 0
  fi

  local firebase_key
  firebase_key="$(cat "$key_file" | tr -d '\r\n')"

  if [ -z "$firebase_key" ]; then
    warn "❌ Firebase API key file is empty"
    return 0
  fi

  log "✅ Firebase API key fetched from GitHub Actions"
  # Remove any existing FIREBASE__API_KEY lines, then write a single clean entry
  if [ -f .env ]; then
    sed -i.bak "/^FIREBASE__API_KEY=/d" .env
    rm -f .env.bak
  fi
  echo "FIREBASE__API_KEY=$firebase_key" >> .env
  export FIREBASE__API_KEY="$firebase_key"
  FIREBASE_FETCH_OK=1
  return 0
}

setup_github_auth
ensure_github_auth_ready || true

echo ""
echo "Step 8/10: Fetching Firebase API key from GitHub Actions..."
fetch_firebase_api_key_from_github_actions

echo ""
echo "Step 9/10: Validating Firebase auth..."

# --- Firebase API Key Check (required for stats) ---
function validate_firebase_api_key() {
  local DEFAULT_DB_URL="https://auto-sbm-default-rtdb.firebaseio.com"
  if [ -z "${FIREBASE__API_KEY:-}" ]; then
    # Try reading from .env if present
    if [ -f ".env" ]; then
      ENV_KEY=$(grep -E "^FIREBASE__API_KEY=" .env | tail -n 1 | cut -d'=' -f2- | tr -d '"' | tr -d "'")
      if [ -n "$ENV_KEY" ] && [ "$ENV_KEY" != "your-firebase-web-api-key" ]; then
        export FIREBASE__API_KEY="$ENV_KEY"
      fi
    fi
  fi

  # Ensure database URL is set to the real default if placeholder is present
  if [ -f ".env" ]; then
    ENV_DB_URL=$(grep -E "^FIREBASE__DATABASE_URL=" .env | tail -n 1 | cut -d'=' -f2- | tr -d '"' | tr -d "'")
    if [ -z "$ENV_DB_URL" ] || [ "$ENV_DB_URL" = "https://your-project-id-default-rtdb.firebaseio.com" ]; then
      sed -i.bak "/^FIREBASE__DATABASE_URL=/d" .env
      rm -f .env.bak
      echo "FIREBASE__DATABASE_URL=$DEFAULT_DB_URL" >> .env
      export FIREBASE__DATABASE_URL="$DEFAULT_DB_URL"
    else
      export FIREBASE__DATABASE_URL="$ENV_DB_URL"
    fi
  fi

  if [ -z "${FIREBASE__API_KEY:-}" ] || [ "${FIREBASE__API_KEY}" = "your-firebase-web-api-key" ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠️  Firebase API Key Required"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Auto-SBM requires a Firebase API key for stats tracking."
    echo "The key could not be fetched automatically."
    echo ""
    echo "If you have a custom key, enter it now."
    echo ""
    if [ -t 0 ] && [ -t 1 ]; then
      read -p "Enter Firebase API key (or press Enter to skip for now): " USER_KEY
    else
      USER_KEY=""
    fi

    if [ -z "$USER_KEY" ]; then
      warn "Setup will continue without Firebase API key. Stats will be unavailable."
      return 0
    fi

    # Write user-provided key to .env (dedupe existing entries)
    if [ -f .env ]; then
      sed -i.bak "/^FIREBASE__API_KEY=/d" .env
      rm -f .env.bak
    fi
    echo "FIREBASE__API_KEY=$USER_KEY" >> .env

    export FIREBASE__API_KEY="$USER_KEY"
    log "✅ Firebase API key stored in .env"
  else
    log "✅ FIREBASE__API_KEY detected"
  fi
  return 0
}

validate_firebase_api_key

echo ""
echo "Step 10/10: Validating installation..."

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
zsh -c "source ~/.zprofile; source ~/.zshrc"
echo ""
echo " 🚀 Auto-SBM Setup Complete!"
echo ""
echo "   🛠 Current build: v$SBM_VERSION"
echo "   ✅ Auto-SBM CLI globally available"
echo "   ✅ Run your first migration with: sbm [slug]"
echo ""

touch .sbm_setup_complete
log ".sbm_setup_complete marker file created."

exit 0
