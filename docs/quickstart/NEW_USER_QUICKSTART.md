# SBM Tool V2 - New User Quickstart Guide

## 🚀 Quick Setup (5 minutes)

### Prerequisites

- Python 3.8+ installed
- Access to DealerInspire platform directory
- GitHub CLI (`gh`) installed and authenticated
- Context7 API access (optional, for enhanced features)

### 1. Install the Tool

```bash
# Clone and install
git clone <repository-url>
cd sbm-v2
pip install -e .

# Install shell completion (optional but recommended)
sbm install-completion
```

### 2. Configure Your Environment

The tool auto-detects most settings, but you may need to configure:

```bash
# If your DI platform is not at ~/di-websites-platform
export DI_PLATFORM_PATH="/path/to/your/di-websites-platform"

# For Context7 integration (optional)
# Add to ~/.cursor/mcp.json:
{
  "context7ApiKey": "your-api-key-here",
  "githubToken": "your-github-token-here"
}
```

### 3. Verify Installation

```bash
sbm doctor
```

This checks your environment and reports any issues.

## 🎯 Your First Migration

### Step 1: Navigate to a Dealer Theme

```bash
cd ~/di-websites-platform/dealer-themes/your-dealer-slug
```

### Step 2: Run Migration

```bash
# Basic migration
sbm migrate

# With GitHub PR creation
sbm migrate --create-pr

# Force migration (skip validation)
sbm migrate --force
```

### Step 3: Review Results

The tool will:

- ✅ Convert legacy SCSS to Site Builder format
- ✅ Replace mixins with CSS equivalents
- ✅ Convert hex colors to CSS variables
- ✅ Create proper file structure
- ✅ Generate GitHub PR (if requested)

## 📋 Common Commands

### Migration Commands

```bash
# Standard migration
sbm migrate

# Migration with PR creation
sbm migrate --create-pr

# Force migration (skip validation)
sbm migrate --force

# Dry run (see what would be changed)
sbm migrate --dry-run
```

### Diagnostic Commands

```bash
# Check environment and dealer theme
sbm doctor

# Export diagnostic results to JSON
sbm doctor --export-log results.json

# Validate specific dealer theme
sbm validate dealer-slug
```

### Utility Commands

```bash
# Create PR for existing changes
sbm create-pr

# Install shell completion
sbm install-completion

# Get help
sbm --help
sbm migrate --help
```

## 🔧 Command Flags Reference

| Flag           | Short | Description                                       |
| -------------- | ----- | ------------------------------------------------- |
| `--force`      | `-f`  | Skip validation checks                            |
| `--create-pr`  | `-g`  | Create GitHub PR after migration                  |
| `--dry-run`    | `-n`  | Show what would be changed without making changes |
| `--export-log` | `-e`  | Export diagnostic results to JSON                 |
| `--help`       | `-h`  | Show help information                             |

## 🎨 What Gets Migrated

### File Transformations

- `lvdp.scss` → `sb-vdp.scss` (Vehicle Detail Page)
- `lvrp.scss` → `sb-vrp.scss` (Vehicle Results Page)
- `inside.scss` → `sb-inside.scss` (Interior pages)

### SCSS Conversions

- **Mixins**: `@include flexbox()` → `display: flex`
- **Colors**: `#093382` → `var(--primary, #093382)`
- **Breakpoints**: Standardized to 768px (tablet) and 1024px (desktop)
- **Variables**: Legacy variables converted to CSS custom properties

### File Structure

```
dealer-theme/
├── sb-vdp.scss      # Converted VDP styles
├── sb-vrp.scss      # Converted VRP styles
├── sb-inside.scss   # Converted interior styles
└── style.scss       # Updated imports
```

## 🚨 Troubleshooting

### Common Issues

**Permission Denied**

```bash
# Remove old aliases and reinstall
unalias sbm # if exists
pip install -e . --force-reinstall
```

**Command Not Found**

```bash
# Add Python user bin to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**GitHub CLI Not Authenticated**

```bash
gh auth login
```

**Validation Failures**

```bash
# Check what's missing
sbm doctor

# Force migration if needed
sbm migrate --force
```

### Getting Help

- Run `sbm doctor` for environment diagnostics
- Use `sbm --help` for command reference
- Check the full documentation in `docs/`

## 🎯 Next Steps

1. **Test on a simple dealer theme first**
2. **Review generated SCSS files** to understand the conversions
3. **Use `--dry-run` flag** to preview changes before applying
4. **Set up shell completion** for faster workflow
5. **Integrate with your existing workflow** using the PR creation features

## 📚 Additional Resources

- [Development Guide](../development/CHANGELOG.md)
- [K8 Compliance Analysis](../analysis/K8_COMPLIANCE_SUMMARY.md)
- [Full Documentation](../index.md)
- [Project Overview](../../PROJECT_OVERVIEW.md)

---

**Need help?** Run `sbm doctor` to diagnose issues or check the troubleshooting section above.
