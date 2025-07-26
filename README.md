# Auto-SBM: Automated Site Builder Migration Tool

🚀 **Production-ready tool for migrating DealerInspire dealer websites from legacy SCSS themes to Site Builder format.**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)

---

## ✨ Features

- **🔄 Automated SCSS Migration**: Converts legacy SCSS to Site Builder format with intelligent variable processing
- **🎨 Rich UI**: Beautiful terminal interface with progress tracking and status panels
- **🔒 Type Safety**: Full Pydantic v2 validation and mypy type checking
- **⚡ Performance**: Optimized processing with concurrent file handling
- **🛡️ Security**: Environment-based configuration with no hardcoded secrets
- **🧪 Comprehensive Testing**: 90%+ test coverage with robust validation
- **📊 Detailed Reporting**: Complete migration logs and validation reports

---

## 🚀 Quick Start

### Prerequisites

**For Fresh Mac (Zero Setup Required):**
- macOS with Terminal access
- Internet connection
- That's it! The setup script will install everything else automatically.

**What gets installed automatically:**
- **Homebrew** (macOS package manager)
- **Python 3.9+** (includes pip)
- **Git** with SSH access to GitHub
- **GitHub CLI (`gh`)** for PR automation
- **UV** (fast Python package manager)

**Manual Prerequisites (if you prefer):**
- **just** for starting dealer sites *(optional - can be installed later)*
- **DI Websites Platform** cloned to `~/di-websites-platform` *(for actual migration work)*

### Installation

```bash
# Clone and setup
git clone git@github.com:nate-hart-di/auto-sbm.git
cd auto-sbm
bash setup.sh
```

> **Note:** Setup scripts are organized in `scripts/` directory for cleaner project structure. The root `setup.sh` automatically delegates to `scripts/setup.sh`.

**What setup.sh does:**

🍺 **Automatic Tool Installation (macOS):**
- Installs Homebrew if missing
- Installs Python 3.9+, Git, and GitHub CLI automatically
- Installs UV for faster package management
- Sets up ~/.local/bin in your PATH

🐍 **Python Environment:**
- Creates isolated virtual environment (`.venv`)
- Installs all dependencies via modern `pyproject.toml`
- Includes development and testing tools

🌍 **Global Access:**
- Creates global `sbm` command available anywhere
- Smart wrapper script with environment validation
- Auto-healing setup if dependencies are missing

⚙️ **Configuration:**
- Creates `.env` from template
- Sets up GitHub CLI authentication
- Validates installation with health checks

### Environment Configuration

Copy and configure your environment:

```bash
cp .env.example .env
# Edit .env with your GitHub token and preferences
```

**Required Environment Variables:**

```bash
GITHUB_TOKEN=your_github_personal_access_token
```

---

## 🧭 Migration Workflow

### 1. **Start Migration**

```bash
sbm migrate {theme-slug}
# or the equivalent shortcuts:
sbm auto {theme-slug}
sbm {theme-slug}
```

**Example:**

```bash
sbm migrate fiatofportland
```

### 2. **Automated Processing**

The tool performs these steps automatically:

#### **🏗️ Environment Setup**

- Initializes dealer site with `just start`
- Displays local URLs and credentials
- Validates theme structure

#### **📁 File Generation**

- Creates Site Builder SCSS files:
  - `sb-inside.scss` - Interior pages styling
  - `sb-vdp.scss` - Vehicle Detail Page styling
  - `sb-vrp.scss` - Vehicle Results Page styling
- Logs file creation with line counts

#### **🔄 SCSS Transformation**

- **Variable Conversion**: Legacy SCSS variables → CSS custom properties
- **Path Processing**: Relative image paths with enforced quotes
- **Mixin Migration**: Converts mixins to CSS (with fallback handling)
- **Code Optimization**: Trims, formats, and validates output
- **Rich Progress**: Real-time progress tracking with detailed status

#### **🎨 Style Enhancement**

- Adds predetermined styles (cookie banners, directions)
- Migrates map components (if shortcodes detected)
- Applies OEM-specific customizations

### 3. **Manual Review Phase**

The tool pauses for your review:

```
📋 Generated Files:
✅ sb-inside.scss (245 lines)
✅ sb-vdp.scss (189 lines)
✅ sb-vrp.scss (203 lines)

📂 Location: ~/di-websites-platform/themes/fiatofportland/

🔍 Please review the generated files and make any needed adjustments.
Continue with migration? [y/N]
```

**During review:**

- Examine generated SCSS files in your editor
- Make manual adjustments as needed
- Verify variable conversions and mixin handling
- Check for any compilation warnings

### 4. **Validation & Quality Checks**

After review confirmation:

- **SCSS Validation**: Syntax and structure verification
- **Compilation Test**: Ensures files compile without errors
- **Performance Check**: Analyzes file sizes and complexity
- **Security Scan**: Validates no sensitive data in output

### 5. **Git Operations**

```
🔧 Git Operations:
📝 Add files to staging
💾 Commit with migration summary
🚀 Push to feature branch: feature/sb-migration-fiatofportland
Continue with Git operations? [y/N]
```

### 6. **Pull Request Creation**

```
📋 Create Pull Request:
🎯 Title: "Site Builder Migration: fiatofportland"
👥 Reviewers: fe-dev team
🏷️ Labels: fe-dev, site-builder-migration
Create PR? [Y/n]
```

**PR includes:**

- Migration summary with file statistics
- Before/after comparisons
- Validation results
- Manual review checklist

---

## 🛠️ Advanced Usage

### **Individual Commands**

```bash
# Validate theme structure and SCSS
sbm validate {theme-slug}

# Run post-migration cleanup and optimization
sbm post-migrate {theme-slug}

# Generate validation report
sbm report {theme-slug}
```

### **Command Options**

```bash
# Skip site initialization
sbm migrate {theme-slug} --skip-just

# Dry run (preview changes without applying)
sbm migrate {theme-slug} --dry-run

# Verbose output for debugging
sbm migrate {theme-slug} --verbose

# Disable Rich UI (for CI/automation)
sbm migrate {theme-slug} --no-rich
```

### **Batch Operations**

```bash
# Migrate multiple themes
sbm batch-migrate theme1 theme2 theme3

# Validate multiple themes
sbm batch-validate theme1 theme2 theme3
```

---

## 🏗️ Architecture

Auto-SBM v2.0 uses a modern **vertical slice architecture** for maintainability and type safety:

```
auto-sbm/
├── src/auto_sbm/           # Main package (src layout)
│   ├── config.py          # Pydantic settings & env validation
│   ├── models/            # Shared Pydantic models
│   │   ├── theme.py       # Theme data structures
│   │   ├── migration.py   # Migration state models
│   │   └── scss.py        # SCSS processing models
│   │
│   ├── features/          # Business capabilities (vertical slices)
│   │   ├── migration/     # Migration orchestration
│   │   ├── scss_processing/ # SCSS transformation logic
│   │   ├── git_operations/  # Git workflow automation
│   │   └── oem_handling/    # OEM-specific customizations
│   │
│   └── shared/            # Cross-cutting concerns
│       ├── ui/            # Rich UI components
│       ├── validation/    # Validation utilities
│       └── utils/         # Common utilities
│
├── tests/                 # Comprehensive test suite
├── pyproject.toml         # Modern Python packaging
├── .env.example          # Environment template
└── CLAUDE.md             # AI assistant context
```

### **Key Architectural Principles**

- **🎯 Vertical Slices**: Features organized by business capability
- **🛡️ Type Safety**: Pydantic v2 models for all data validation
- **🧪 Test Coverage**: Co-located tests with 90%+ coverage
- **🔒 Security**: Environment-based configuration
- **⚡ Performance**: Async processing where beneficial
- **🎨 Rich UI**: Professional terminal interface with fallbacks

---

## 🆘 Troubleshooting

### **Common Issues**

**❌ "command not found: sbm"**

```bash
# Restart terminal for PATH changes to take effect
# Or manually add to your shell profile:
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**❌ "GitHub authentication failed"**

```bash
# Ensure GitHub CLI is authenticated
gh auth login

# Verify your token has required permissions:
# - repo (full control)
# - workflow (if using GitHub Actions)
```

**❌ "Python/dependency errors"**

```bash
# Reinstall dependencies
cd auto-sbm
rm -rf .venv
bash setup.sh

# For development setup:
pip install -e .[dev]
```

**❌ "Type checking errors"**

```bash
# Run type checking
mypy src/auto_sbm/

# Install missing type stubs
mypy --install-types
```

**❌ "Rich UI not displaying correctly"**

```bash
# For CI/automation environments:
sbm migrate theme --no-rich

# Check terminal compatibility:
echo $TERM
```

### **Fresh Mac Setup Issues**

**❌ "Homebrew installation failed"**

```bash
# Check your internet connection and try again
# Or install Homebrew manually first:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**❌ "Command Line Tools needed"**

```bash
# macOS will prompt to install Xcode Command Line Tools
# Click "Install" and wait for completion, then re-run setup.sh
```

**❌ "GitHub CLI authentication"**

```bash
# The setup script will prompt for GitHub authentication
# Follow the prompts to authenticate via web browser
# Required for creating pull requests
```

**❌ "Permission denied: /usr/local/bin"**

```bash
# Modern Homebrew uses /opt/homebrew on Apple Silicon
# The setup script handles this automatically
# If issues persist, restart terminal and try again
```

### **Environment Issues**

**Missing .env configuration:**

```bash
cp .env.example .env
# Edit .env with your settings
```

**Permission denied errors:**

```bash
# Ensure proper file permissions
chmod +x setup.sh
chmod +x ~/.local/bin/sbm
```

### **Development & Debugging**

**Run with verbose output:**

```bash
sbm migrate theme --verbose --dry-run
```

**Check logs:**

```bash
# Logs are written to logs/ directory
tail -f logs/sbm_$(date +%Y%m%d)_*.log
```

**Run tests:**

```bash
# Full test suite
pytest src/ --cov=auto_sbm

# Specific feature tests
pytest src/auto_sbm/features/migration/tests/
```

### **Performance Issues**

**Large theme processing:**

```bash
# Increase processing limits in .env
MAX_CONCURRENT_FILES=20
CHUNK_SIZE=10000
```

**Memory usage:**

```bash
# Monitor during migration
sbm migrate theme --monitor-memory
```

---

## 🔧 Development

### **Setup Development Environment**

```bash
# Fresh Mac (automatic setup):
git clone git@github.com:nate-hart-di/auto-sbm.git
cd auto-sbm
bash setup.sh  # Installs everything automatically

# Existing development machine:
git clone git@github.com:nate-hart-di/auto-sbm.git
cd auto-sbm
bash setup.sh  # Uses existing tools where available

# Manual development setup (if preferred):
pip install -e .[dev]
pre-commit install
```

### ✅ Verify Installation

After setup completes, verify everything works:

```bash
# Check global command
sbm --help

# Check version
sbm version

# Test GitHub authentication
gh auth status
```

### **Code Quality**

```bash
# Linting and formatting
ruff check src/ --fix
ruff format src/

# Type checking
mypy src/auto_sbm/

# Run all quality checks
tox
```

### **Testing**

```bash
# Run tests with coverage
pytest src/ --cov=auto_sbm --cov-report=html

# Run specific test categories
pytest src/ -m "unit"
pytest src/ -m "integration"

# Performance benchmarks
pytest src/ -m "benchmark"
```

### **Contributing**

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Run quality checks**: `ruff check && mypy src/ && pytest`
4. **Commit changes**: `git commit -m 'Add amazing feature'`
5. **Push to branch**: `git push origin feature/amazing-feature`
6. **Open Pull Request**

---

## 📚 Additional Resources

- **[CLAUDE.md](./CLAUDE.md)** - AI assistant context and development guide
- **[Code Reviews](./PRPs/code_reviews/)** - Quality analysis and improvements
- **[Architecture Docs](./PRPs/ai_docs/)** - Detailed technical documentation
- **GitHub Issues** - Bug reports and feature requests
- **Team Chat** - Real-time support and discussions
