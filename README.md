# Auto-SBM: Automated Site Builder Migration Tool

🚀 **Production-ready tool for migrating DealerInspire dealer websites from legacy SCSS themes to Site Builder format.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
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
- **💻 Code Formatting**: Integrated prettier for consistent code formatting

---

## 🚀 Quick Start

### Prerequisites

**For Fresh Mac (Zero Setup Required):**

- macOS with Terminal access
- Internet connection
- That's it! The setup script will install everything else automatically.

**What gets installed automatically:**

- **Homebrew** (macOS package manager)
- **Python 3.8+** (includes pip)
- **Git** with SSH access to GitHub
- **GitHub CLI (`gh`)** for PR automation
- **UV** (fast Python package manager)
- **Node.js** and **prettier** for code formatting

**Manual Prerequisites (if you prefer):**

- **DI Websites Platform** cloned to `~/di-websites-platform` _(for actual migration work)_
- **Docker Desktop** _(optional - for local platform development)_

### Installation

```bash
# Clone and setup
git clone git@github.com:nate-hart-di/auto-sbm.git
cd auto-sbm
bash setup.sh
```

**What setup.sh does:**

🍺 **Automatic Tool Installation (macOS):**

- Installs Homebrew if missing
- Installs Python 3.8+, Git, and GitHub CLI automatically
- Installs Node.js and prettier for code formatting
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

The setup script creates a `.env` file automatically. GitHub authentication is handled via `gh auth login` (browser-based) - no tokens needed in `.env` files.

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

The tool performs these steps automatically with Rich UI progress tracking:

#### **🔧 Git Operations** (Step 1/6)
- Creates feature branch: `feature/{theme-slug}-sbm{date}`
- Sets up clean working environment
- Validates repository state

#### **🐳 Docker Startup** (Step 2/6)
- Monitors Docker container status
- Validates DI platform environment
- Displays container health information

#### **📁 File Creation** (Step 3/6)
- Creates Site Builder SCSS files:
  - `sb-inside.scss` - Interior pages styling
  - `sb-vdp.scss` - Vehicle Detail Page styling
  - `sb-vrp.scss` - Vehicle Results Page styling
- Logs file creation with line counts

#### **🔄 SCSS Migration** (Step 4/6)
- **Variable Conversion**: Legacy SCSS variables → CSS custom properties
- **Path Processing**: Relative image paths with enforced quotes
- **Mixin Migration**: Converts 50+ CommonTheme mixins to CSS
- **Code Optimization**: Trims, formats, and validates output
- **Rich Progress**: Real-time progress tracking with detailed status

#### **🎨 Predetermined Styles** (Step 5/6)
- Adds predetermined styles (cookie banners, directions)
- Applies OEM-specific customizations (Stellantis, etc.)
- Integrates theme-specific enhancements

#### **🗺️ Map Components** (Step 6/6)
- Migrates map components (if shortcodes detected)
- Handles MapBox integration
- Processes location-based features

### 3. **Manual Review Phase**

The tool pauses for your review with a structured status panel:

```
📋 Migration Complete - fiatofportland
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📂 Generated Files:
✅ sb-inside.scss (245 lines)
✅ sb-vdp.scss (189 lines)  
✅ sb-vrp.scss (203 lines)

📍 Location: ~/di-websites-platform/themes/fiatofportland/
⏱️ Duration: 0:02:34

🔍 Please review the generated files and make any needed adjustments.
Continue with Git operations? [y/N]
```

**During review:**
- Examine generated SCSS files in your editor
- Make manual adjustments as needed
- Run `prettier` for consistent formatting
- Verify variable conversions and mixin handling

### 4. **Git Operations & PR Creation**

After confirmation, the tool handles:

- **File Staging**: Adds all modified files
- **Commit Creation**: Creates commit with migration summary
- **Branch Push**: Pushes to feature branch
- **PR Creation**: Creates pull request with comprehensive details

---

## 🛠️ Advanced Usage

### **Individual Commands**

```bash
# Validate theme structure and SCSS
sbm validate {theme-slug}

# Run post-migration cleanup and optimization
sbm post-migrate {theme-slug}

# Display version information
sbm version
```

### **Command Options**

```bash
# Skip Docker initialization
sbm migrate {theme-slug} --skip-docker

# Dry run (preview changes without applying)
sbm migrate {theme-slug} --dry-run

# Verbose output for debugging
sbm migrate {theme-slug} --verbose

# Disable Rich UI (for CI/automation)
sbm migrate {theme-slug} --no-rich
```

---

## 🏗️ Architecture

Auto-SBM v2.0 uses a modern **vertical slice architecture** organized by business capability:

```
auto-sbm/
├── sbm/                      # Main package
│   ├── __init__.py          # Package initialization
│   ├── main.py              # CLI entry point
│   ├── config.py            # Configuration management
│   │
│   ├── core/                # Core business logic
│   │   ├── migration.py     # Migration orchestration
│   │   ├── git.py           # Git operations
│   │   ├── maps.py          # Map component migration
│   │   └── validation.py    # Post-migration validation
│   │
│   ├── scss/                # SCSS processing engine
│   │   ├── processor.py     # Core SCSS transformation
│   │   ├── mixin_parser.py  # CommonTheme mixin conversion
│   │   └── validator.py     # SCSS validation
│   │
│   ├── ui/                  # Rich UI components
│   │   ├── console.py       # Console management
│   │   ├── progress.py      # Progress tracking
│   │   ├── panels.py        # Status panels
│   │   └── prompts.py       # Interactive prompts
│   │
│   ├── oem/                 # OEM-specific handling
│   │   ├── stellantis.py    # Stellantis customizations
│   │   ├── factory.py       # OEM handler factory
│   │   └── base.py          # Base OEM handler
│   │
│   └── utils/               # Utilities and helpers
│       ├── logger.py        # Rich-enhanced logging
│       ├── path.py          # Path utilities
│       └── command.py       # Command execution
│
├── tests/                   # 🚨 ALL TESTS GO HERE 🚨
│   ├── test_*.py           # Unit tests
│   ├── integration/        # Integration tests
│   └── fixtures/           # Test data
│
├── PRPs/                   # 🚨 ALL PRP DOCUMENTS GO HERE 🚨
│   ├── *.md               # Project requirements and planning
│   └── code_reviews/      # Code quality analysis
│
├── pyproject.toml         # Modern Python packaging
├── .env.example          # Environment template
├── setup.sh              # Development setup script
└── CLAUDE.md             # AI assistant context
```

### **Key Architectural Principles**

- **🎯 Vertical Slices**: Features organized by business capability, not technical layers
- **🛡️ Type Safety**: Comprehensive type hints and validation
- **🧪 Test Coverage**: Co-located tests with 90%+ coverage
- **🔒 Security**: Environment-based configuration with no hardcoded secrets
- **⚡ Performance**: Optimized SCSS processing and file operations
- **🎨 Rich UI**: Professional terminal interface with CI/automation fallbacks

---

## 🆘 Troubleshooting

### **Common Issues**

**❌ "command not found: sbm"**

```bash
# Restart terminal for PATH changes to take effect
# Or manually source your shell profile:
source ~/.zshrc
```

**❌ "GitHub authentication failed"**

```bash
# Ensure GitHub CLI is authenticated
gh auth login

# Verify authentication status
gh auth status
```

**❌ "Python/dependency errors"**

```bash
# Reinstall dependencies
cd auto-sbm
rm -rf .venv
bash setup.sh
```

**❌ "prettier: command not found"**

This should not happen after running `setup.sh`, but if it does:

```bash
# Install prettier globally
npm install -g prettier

# Verify installation
prettier --version
```

**❌ "Rich UI not displaying correctly"**

```bash
# For CI/automation environments:
sbm migrate theme --no-rich

# Check terminal compatibility:
echo $TERM
```

### **Environment Issues**

**❌ "Docker containers not running"**

```bash
# Start Docker Desktop
# Or skip Docker validation:
sbm migrate theme --skip-docker
```

**❌ "Permission denied errors"**

```bash
# Fix file permissions
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
# Logs are written to current directory
ls -la *.log
```

**Run tests:**

```bash
# Full test suite
source .venv/bin/activate && python -m pytest tests/ -v

# With coverage
source .venv/bin/activate && python -m pytest tests/ --cov=sbm --cov-report=html
```

---

## 🔧 Development

### **Setup Development Environment**

```bash
# Clone and setup (handles everything automatically)
git clone git@github.com:nate-hart-di/auto-sbm.git
cd auto-sbm
bash setup.sh
```

### **Code Quality**

```bash
# Linting and formatting (Python)
ruff check . --fix
ruff format .

# Code formatting (other files)
prettier --write "**/*.{js,json,md,yml,yaml}"

# Type checking
mypy sbm/

# Run all quality checks
source .venv/bin/activate && python -m pytest tests/ --cov=sbm
```

### **Testing**

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all tests
python -m pytest tests/ -v

# Run tests with coverage
python -m pytest tests/ --cov=sbm --cov-report=html

# Run specific test files
python -m pytest tests/test_migration.py -v
```

### **Contributing**

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Run quality checks**: `ruff check && mypy sbm/ && pytest tests/`
4. **Commit changes**: `git commit -m 'Add amazing feature'`
5. **Push to branch**: `git push origin feature/amazing-feature`
6. **Open Pull Request**

---

## 📚 Additional Resources

- **[CLAUDE.md](./CLAUDE.md)** - AI assistant context and development guide
- **[Code Reviews](./PRPs/code_reviews/)** - Quality analysis and improvements
- **[Architecture Docs](./PRPs/)** - Detailed technical documentation
- **GitHub Issues** - Bug reports and feature requests
- **Team Chat** - Real-time support and discussions

---

## 📝 Version History

- **v2.0.0** - Complete architectural refactor with Rich UI, vertical slice architecture
- **v1.x** - Legacy monolithic structure (deprecated)

For detailed changes, see commit history and PRPs documentation.