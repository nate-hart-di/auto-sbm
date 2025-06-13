#!/bin/bash

# SBM Tool V2 - Automated Setup Script
# This script installs all prerequisites and sets up the SBM tool

set -e # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
  echo -e "\n${BLUE}================================${NC}"
  echo -e "${BLUE}$1${NC}"
  echo -e "${BLUE}================================${NC}\n"
}

# Check if running on macOS
check_macos() {
  if [[ "$OSTYPE" != "darwin"* ]]; then
    print_error "This setup script is designed for macOS only."
    print_status "For other operating systems, please follow the manual installation instructions."
    exit 1
  fi
}

# Check Python version
check_python() {
  print_status "Checking Python installation..."

  if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed."
    print_status "Installing Python 3 via Homebrew..."
    install_homebrew_if_needed
    brew install python3
  fi

  python_version=$(python3 --version | cut -d' ' -f2)
  required_version="3.8.0"

  if [[ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]]; then
    print_error "Python 3.8+ is required. Found: $python_version"
    print_status "Please upgrade Python and re-run this script."
    exit 1
  fi

  print_success "Python $python_version is installed"
}

# Install Homebrew if needed
install_homebrew_if_needed() {
  if ! command -v brew &> /dev/null; then
    print_status "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add Homebrew to PATH for Apple Silicon Macs
    if [[ -d "/opt/homebrew" ]]; then
      echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
      eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
  fi
}

# Install GitHub CLI
install_github_cli() {
  print_status "Checking GitHub CLI installation..."

  if ! command -v gh &> /dev/null; then
    print_status "Installing GitHub CLI..."
    install_homebrew_if_needed
    brew install gh
    print_success "GitHub CLI installed"
  else
    print_success "GitHub CLI is already installed"
  fi

  # Check if authenticated
  if ! gh auth status &> /dev/null; then
    print_warning "GitHub CLI is not authenticated."
    print_status "Please authenticate with GitHub:"
    gh auth login
  else
    print_success "GitHub CLI is authenticated"
  fi
}

# Check for DI platform directory
check_di_platform() {
  print_status "Checking for DealerInspire platform directory..."

  local di_path="$HOME/di-websites-platform"
  if [[ -d "$di_path" ]]; then
    print_success "Found DI platform at: $di_path"
  else
    print_warning "DI platform directory not found at: $di_path"
    print_status "This is required for the tool to work properly."
    print_status "Make sure you have access to the di-websites-platform repository."
  fi
}

# Install pip if needed
install_pip() {
  print_status "Checking pip installation..."

  if ! python3 -m pip --version &> /dev/null; then
    print_status "Installing pip..."
    python3 -m ensurepip --upgrade
  fi

  print_success "pip is available"
}

# Install the SBM tool
install_sbm_tool() {
  print_status "Installing SBM Tool V2..."

  # Upgrade pip first
  python3 -m pip install --upgrade pip

  # Install the tool in editable mode
  python3 -m pip install -e .

  # Add ~/.local/bin to PATH if not already there
  local shell_rc=""
  if [[ "$SHELL" == *"zsh"* ]]; then
    shell_rc="$HOME/.zshrc"
  elif [[ "$SHELL" == *"bash"* ]]; then
    shell_rc="$HOME/.bashrc"
  fi

  if [[ -n "$shell_rc" ]]; then
    if ! grep -q 'export PATH="$HOME/.local/bin:$PATH"' "$shell_rc"; then
      echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$shell_rc"
      print_status "Added ~/.local/bin to PATH in $shell_rc"
    fi
  fi

  print_success "SBM Tool V2 installed successfully"
}

# Create configuration directory and example file
setup_configuration() {
  print_status "Setting up configuration..."

  local config_dir="$HOME/.cursor"
  local config_file="$config_dir/mcp.json"

  mkdir -p "$config_dir"

  if [[ ! -f "$config_file" ]]; then
    cat > "$config_file" << 'EOF'
{
  "diPlatformPath": "~/di-websites-platform",
  "githubToken": "",
  "context7ApiKey": ""
}
EOF
    print_success "Created configuration file at: $config_file"
    print_status "You can customize settings in this file if needed."
  else
    print_success "Configuration file already exists"
  fi
}

# Verify installation
verify_installation() {
  print_status "Verifying installation..."

  # Source the shell to pick up PATH changes
  export PATH="$HOME/.local/bin:$PATH"

  if command -v sbm &> /dev/null; then
    print_success "SBM command is available"

    # Run doctor command
    print_status "Running system diagnostics..."
    if sbm doctor; then
      print_success "System diagnostics passed"
    else
      print_warning "Some diagnostics failed - check output above"
    fi
  else
    print_error "SBM command not found"
    print_status "Try running: source ~/.zshrc (or ~/.bashrc)"
    print_status "Then run: sbm doctor"
  fi
}

# Main installation function
main() {
  print_header "SBM Tool V2 - Automated Setup"
  print_status "This script will install all prerequisites and set up the SBM tool."
  print_status "Press Ctrl+C to cancel, or Enter to continue..."
  read -r

  check_macos
  check_python
  install_pip
  install_github_cli
  check_di_platform
  install_sbm_tool
  setup_configuration
  verify_installation

  print_header "Setup Complete!"
  print_success "SBM Tool V2 has been installed successfully."
  print_status ""
  print_status "Next steps:"
  print_status "1. Restart your terminal or run: source ~/.zshrc"
  print_status "2. Run 'sbm doctor' to verify everything is working"
  print_status "3. Try your first migration: sbm setup <dealer-slug> --auto-start"
  print_status ""
  print_status "For help and documentation, visit:"
  print_status "https://github.com/nate-hart-di/auto-sbm"
}

# Run main function
main "$@"
