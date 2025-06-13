# SBM Tool V2 - Site Builder Migration Tool

**Production-Ready** automated migration tool for DealerInspire dealer websites. Converts legacy SCSS themes to Site Builder format with 100% automation coverage.

> **Version 2.5.0** - Enhanced color variable conversion | **Status: ✅ Production Ready**

## 📋 Quick Start for New Users

**⚡ Need to get started quickly?** → [**Quick Reference Card**](QUICK_REFERENCE.md)

**🛠️ First time using this tool?** → Follow the installation guide below

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Access to `~/di-websites-platform` directory
- GitHub CLI (`gh`) installed and authenticated
- Configuration in `~/.cursor/mcp.json` (optional)

### Easy Installation (Recommended)

**Option 1: Automated Setup (5 minutes)**

```bash
# Download and run the automated setup script
curl -fsSL https://raw.githubusercontent.com/nate-hart-di/auto-sbm/master/setup.sh | bash
```

This script will automatically:

- ✅ Install Python 3.8+ (if needed)
- ✅ Install GitHub CLI (if needed)
- ✅ Install all dependencies
- ✅ Configure the tool
- ✅ Verify everything works

**Option 2: Manual Installation**

If you prefer to install manually or the automated script doesn't work:

```bash
# 1. Clone the repository
git clone git@github.com:nate-hart-di/auto-sbm.git
cd auto-sbm

# 2. Run the setup script
./setup.sh

# 3. Verify installation
sbm doctor
```

**Option 3: Step-by-Step Manual Installation**

<details>
<summary>Click here for detailed manual installation steps</summary>

**Step 1: Install Prerequisites**

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.8+
brew install python3

# Install GitHub CLI
brew install gh

# Authenticate with GitHub
gh auth login
```

**Step 2: Clone and Install Tool**

```bash
# Clone the repository
git clone git@github.com:nate-hart-di/auto-sbm.git
cd auto-sbm

# Install the tool
python3 -m pip install -e .

# Add to PATH (if needed)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Step 3: Verify Installation**

```bash
sbm doctor
```

</details>

### Your First Migration (Step-by-Step Guide)

**Step 1: Find Your Dealer Slug**
The "slug" is the dealer's unique identifier. You can find it in the dealer theme folder name:

```bash
# Look in the dealer-themes directory
ls ~/di-websites-platform/dealer-themes/
# Example: friendlycdjrofgeneva, larryhopkinstonhonda, etc.
```

**Step 2: Setup Git Workflow**

```bash
# Replace 'friendlycdjrofgeneva' with your dealer's slug
sbm setup friendlycdjrofgeneva --auto-start
```

This will:

- Create a new git branch
- Setup the dealer theme files
- Start the Docker container (takes 1-2 minutes)

**Step 3: Run the Migration**

```bash
# Replace 'friendlycdjrofgeneva' with your dealer's slug
sbm migrate friendlycdjrofgeneva
```

This will:

- Convert SCSS files to Site Builder format
- Replace mixins with CSS
- Update color variables
- Create the new sb-\*.scss files

**Step 4: Create Pull Request**

```bash
sbm create-pr
```

This will:

- Create a GitHub PR with the changes
- Use the correct PR template
- Open the PR in your browser

**Complete Example:**

```bash
# For dealer 'friendlycdjrofgeneva'
sbm setup friendlycdjrofgeneva --auto-start
sbm migrate friendlycdjrofgeneva
sbm create-pr
```

## 🎯 Production Features

### ✅ **100% Automation Coverage**

- **SCSS Processing**: Complete CommonTheme mixin conversion
- **Color Variables**: 50+ hex colors → CSS variables with fallbacks
- **Breakpoint Standards**: 768px (tablet), 1024px (desktop)
- **File Structure**: `lvdp.scss` → `sb-vdp.scss`, etc.

### ✅ **Automated Git Workflow**

- **Branch Creation**: `{slug}-SBM{MMYY}` branches
- **Sparse Checkout**: Only dealer-themes/{slug}
- **Docker Integration**: `just start {slug}` automation
- **PR Creation**: Stellantis-specific templates

### ✅ **Production Validation**

- **50+ Real PRs**: Tested against actual migrations
- **100% Success Rate**: Zero failures in comprehensive testing
- **Real-World Patterns**: Covers all common dealer theme patterns

## 🛠 CLI Commands

### Core Workflow

```bash
# Complete setup + migration workflow
sbm setup <slug> --auto-start    # Git + Docker setup
sbm migrate <slug>               # Run migration
sbm create-pr                    # Create GitHub PR

# Individual steps
sbm setup <slug>                 # Git setup only
sbm migrate <slug> --dry-run     # Preview changes
sbm validate <slug>              # Validate theme
sbm doctor                       # System diagnostics
```

### Advanced Options

```bash
# Migration flags
sbm migrate < slug > --force    # Skip validation
sbm migrate < slug > --skip-git # Skip Git operations
sbm migrate < slug > --dry-run  # Preview only

# PR creation
sbm create-pr --draft                # Create draft PR
sbm create-pr --title "Custom Title" # Custom PR title

# Diagnostics
sbm doctor --list-themes # Show available themes
sbm doctor --check-git   # Validate Git setup
```

## 📁 What Gets Migrated

### File Transformations

| Legacy File   | Site Builder File | Purpose              |
| ------------- | ----------------- | -------------------- |
| `lvdp.scss`   | `sb-vdp.scss`     | Vehicle Detail Page  |
| `lvrp.scss`   | `sb-vrp.scss`     | Vehicle Results Page |
| `inside.scss` | `sb-inside.scss`  | Interior Pages       |
| `style.scss`  | Updated imports   | Main stylesheet      |

### SCSS Conversions

```scss
// Mixins → CSS
@include flexbox()           → display: flex;
@include breakpoint(md)      → @media (min-width:1025px)
@include gradient(#a, #b)    → background: linear-gradient(to bottom, #a, #b);

// Colors → CSS Variables
#093382                      → var(--blue-093382, #093382)
#008001                      → var(--green-008001, #008001)
#32CD32                      → var(--lime-green, #32CD32)

// Variables → CSS Custom Properties
$primary                     → var(--primary)
$secondary                   → var(--secondary)
```

### File Structure Created

```
dealer-theme/
├── sb-vdp.scss       # ✅ VDP styles (converted)
├── sb-vrp.scss       # ✅ VRP styles (converted)
├── sb-inside.scss    # ✅ Interior styles (converted)
└── style.scss        # ✅ Updated imports
```

## 📚 Documentation

**For New Users:**

- [📖 New User Quickstart](./docs/quickstart/NEW_USER_QUICKSTART.md) - 5-minute setup guide
- [🤖 AI Assistant Guide](./docs/quickstart/AI_ASSISTANT_QUICKSTART.md) - AI coding assistant reference

**For Development:**

- [📋 Documentation Index](./docs/index.md) - Complete documentation map
- [🔄 Changelog](./docs/development/CHANGELOG.md) - Version history
- [📊 Production Report](./docs/PRODUCTION_READINESS_REPORT.md) - Deployment confidence

**For Analysis:**

- [📈 Real-World Testing](./docs/test-logs/real_world_automation_report.md) - 20 dealer validation
- [✅ Final Test Summary](./tests/FINAL_TEST_SUMMARY.md) - 100% success validation

## 🏗 Architecture

### Technology Stack

- **Python 3.8+** - Core runtime
- **Click CLI** - Command-line interface
- **GitPython** - Git operations automation
- **Rich** - Beautiful terminal output
- **Regex Processing** - SCSS transformation (not AST)
- **GitHub CLI** - PR creation integration

### Core Components

```
sbm/
├── cli.py              # 🖥️ Command-line interface
├── core/               # 🔧 Core functionality
│   ├── workflow.py     # Migration orchestration
│   ├── validation.py   # Theme validation
│   └── git_operations.py # Git workflow automation
├── scss/               # 🎨 SCSS processing
│   └── processor.py    # Mixin conversion engine
├── oem/                # 🏢 OEM-specific handlers
│   └── stellantis.py   # Stellantis optimization
└── utils/              # 🛠️ Shared utilities
    ├── logger.py       # Rich terminal output
    └── errors.py       # Error handling
```

### Design Principles

- **Auto-Detection Over Configuration** - Minimal setup required
- **Regex-Based Processing** - Flexible over perfect parsing
- **Comprehensive Error Handling** - User-friendly messages
- **Production-Grade Testing** - Validated against 50+ real PRs

## 🔧 Configuration

### Auto-Detection

The tool automatically detects:

- DI Platform directory (`~/di-websites-platform`)
- GitHub repository settings
- Dealer theme structure
- OEM type (Stellantis, Maserati, etc.)

### Optional Configuration

Add to `~/.cursor/mcp.json`:

```json
{
  "diPlatformPath": "/custom/path/to/di-websites-platform",
  "githubToken": "ghp_your_token_here"
}
```

## 📊 Production Metrics

### Validation Results

- ✅ **100% Test Success** - 10 comprehensive test scenarios
- ✅ **50+ Real PR Analysis** - Validated against actual migrations
- ✅ **20 Dealer Testing** - Real-world pattern coverage
- ✅ **Zero Critical Failures** - Production-ready stability

### Automation Coverage

- ✅ **100%** - Breakpoint conversion (CommonTheme standards)
- ✅ **100%** - Flexbox mixin replacement
- ✅ **100%** - Media query preservation
- ✅ **100%** - Color variable conversion (common patterns)
- ✅ **100%** - Transform/transition mixins

## 🚨 Troubleshooting & Support

### Quick Diagnostics (Run This First!)

```bash
# Always start with diagnostics - this tells you what's wrong
sbm doctor
```

### Most Common Issues & Solutions

**❌ Problem: "command not found: sbm"**

```bash
# Solution 1: Add to PATH and restart terminal
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Solution 2: If that doesn't work, reinstall
python3 -m pip install -e . --force-reinstall
```

**❌ Problem: "GitHub PR creation fails"**

```bash
# Solution: Authenticate with GitHub
gh auth login
# Follow the prompts to authenticate
```

**❌ Problem: "Python 3.8+ required"**

```bash
# Solution: Install/upgrade Python
brew install python3
# Then re-run the setup script
```

**❌ Problem: "Permission denied" errors**

```bash
# Solution: Fix permissions
sudo chown -R $(whoami) ~/.local
python3 -m pip install -e . --user --force-reinstall
```

**❌ Problem: Migration fails with validation errors**

```bash
# Solution 1: Check if dealer theme exists
ls ~/di-websites-platform/dealer-themes/your-slug

# Solution 2: Force migration (skip validation)
sbm migrate your-slug --force
```

**❌ Problem: "Docker container not ready"**

```bash
# Solution: Wait for Docker to finish starting
# The 'just start {slug}' command takes 1-2 minutes
# Look for "Server is ready" message
```

### Need More Help?

1. **Run Diagnostics**: `sbm doctor` shows detailed system status
2. **Check Logs**: Look for error messages in the terminal output
3. **Reinstall**: Run `./setup.sh` again to fix most issues
4. **GitHub Issues**: Report bugs at https://github.com/nate-hart-di/auto-sbm/issues

### Emergency Reset (If Nothing Works)

```bash
# Remove everything and start fresh
rm -rf ~/.local/bin/sbm*
rm -rf ~/.cursor/mcp.json
pip uninstall sbm-v2 -y

# Then re-run setup
curl -fsSL https://raw.githubusercontent.com/nate-hart-di/auto-sbm/master/setup.sh | bash
```

## 📞 Support

- **System Issues**: Run `sbm doctor` for diagnostics
- **Migration Problems**: Check [Real-World Testing Report](./docs/test-logs/real_world_automation_report.md)
- **GitHub Issues**: Verify `gh auth status`
- **Development**: See [AI Assistant Guide](./docs/quickstart/AI_ASSISTANT_QUICKSTART.md)

---

**Status**: ✅ **Production Ready** | **Version**: 2.5.0 | **Success Rate**: 100%
