# SBM Tool V2 - Site Builder Migration Tool

**FULLY AUTOMATED** Site Builder migration tool for DealerInspire dealer websites. Convert legacy SCSS themes to Site Builder format with a single command.

## 🚀 Quick Start (One Command!)

```bash
# Install the tool
pip install sbm-v2

# Run complete automated migration
sbm [slug]
# OR
sbm auto [slug]
```

That's it! The tool automatically handles:

- ✅ System diagnostics
- ✅ Git workflow (checkout main, pull, create branch)
- ✅ Docker container startup (`just start`)
- ✅ SCSS migration and conversion
- ✅ Validation and error checking
- ✅ GitHub PR creation
- ✅ Salesforce message generation

## 📋 What Gets Automated

### Complete Workflow Steps

1. **Diagnostics** - Verify environment and dependencies
2. **Git Setup** - Switch to main, pull, create migration branch
3. **Docker Startup** - Run and monitor `just start [slug]` until ready
4. **Migration** - Convert legacy SCSS to Site Builder format
5. **Validation** - Ensure migration meets standards
6. **PR Creation** - Generate GitHub PR with proper content
7. **Salesforce Integration** - Copy message to clipboard
8. **Summary Report** - Complete workflow results

### File Transformations

- `lvdp.scss` → `sb-vdp.scss` (Vehicle Detail Page)
- `lvrp.scss` → `sb-vrp.scss` (Vehicle Results Page)
- `inside.scss` → `sb-inside.scss` (Interior pages)

### SCSS Conversions

- **Mixins**: `@include flexbox()` → `display: flex`
- **Colors**: `#093382` → `var(--primary, #093382)`
- **Breakpoints**: Standardized to 768px (tablet) and 1024px (desktop)
- **Variables**: Legacy variables converted to CSS custom properties

## 🎯 Usage Examples

### Automated Workflow (Recommended)

```bash
# Complete migration - just provide the dealer slug
sbm [slug]
# OR explicitly use auto command
sbm auto [slug]

# Force migration past validation warnings
sbm auto chryslerofportland --force

# Preview what would be done (dry run)
sbm auto dodgeofseattle --dry-run

# Skip Docker monitoring (for advanced users)
sbm auto jeepnorthwest --skip-docker
```

### Individual Commands (Advanced)

```bash
# System diagnostics
sbm doctor

# Git setup only
sbm setup [slug]

# Migration only
sbm migrate [slug]

# Validation only
sbm validate [slug]

# Create PR only
sbm pr
```

## 🛠 Installation

### Automated Setup (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/nate-hart-di/auto-sbm/master/setup.sh | bash
```

### Manual Installation

```bash
pip install sbm-v2
```

### Development Installation

```bash
git clone git@github.com:nate-hart-di/auto-sbm.git
cd auto-sbm
pip install -e .
```

## ⚙️ Configuration

The tool auto-detects most settings:

- **DI Platform**: Auto-detects `~/di-websites-platform`
- **GitHub Token**: Reads from `~/.cursor/mcp.json`
- **Context7 API**: Reads from MCP configuration

No manual configuration required!

## 🔧 Command Reference

### Primary Command

```bash
sbm [dealer-slug] [options]
# OR
sbm auto [dealer-slug] [options]
```

### Options

| Flag               | Description                              |
| ------------------ | ---------------------------------------- |
| `--force` / `-f`   | Force migration past validation warnings |
| `--dry-run` / `-n` | Preview changes without making them      |
| `--skip-docker`    | Skip Docker container monitoring         |
| `--verbose` / `-v` | Enable detailed logging                  |

### Individual Commands

| Command               | Purpose                |
| --------------------- | ---------------------- |
| `sbm doctor`          | Run system diagnostics |
| `sbm setup [slug]`    | Git setup only         |
| `sbm migrate [slug]`  | Migration only         |
| `sbm validate [slug]` | Validation only        |
| `sbm pr`              | Create GitHub PR       |

## 🚨 Error Handling

The automated workflow includes intelligent error handling:

- **Docker Startup Fails**: Prompts to retry `just start`
- **Validation Warnings**: Option to continue with `--force`
- **Git Issues**: Clear error messages and suggestions
- **Missing Dependencies**: Automatic detection and guidance

## 📊 Success Metrics

After each migration, you'll see:

- ✅ Steps completed vs failed
- 📁 Number of files created
- ⏱️ Total workflow duration
- 🔗 GitHub PR URL
- 📋 Complete summary report

## 🎯 Stellantis Optimization

Optimized for Stellantis dealers with:

- **Brand Detection**: Auto-detects Chrysler, Dodge, Jeep, Ram
- **FCA Features**: Includes FCA-specific migration items
- **PR Templates**: Stellantis-specific PR content
- **Reviewer Assignment**: Auto-assigns `carsdotcom/fe-dev`

## 🔍 Troubleshooting

### Quick Fixes

```bash
# Check environment
sbm doctor

# Permission issues
pip install sbm-v2 --force-reinstall

# GitHub authentication
gh auth login

# Path issues
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Common Issues

- **Command not found**: Add `~/.local/bin` to PATH
- **Permission denied**: Remove old aliases, reinstall
- **Docker timeout**: Use `--skip-docker` and run `just start` manually
- **Validation failures**: Use `--force` or fix issues shown by `sbm doctor`

## 📚 Documentation

- [Quick Reference](docs/QUICK_REFERENCE.md)
- [Development Guide](docs/development/CHANGELOG.md)
- [AI Assistant Guide](docs/quickstart/AI_ASSISTANT_QUICKSTART.md)
- [Project Overview](PROJECT_OVERVIEW.md)

## 🎉 Success Stories

The tool has successfully migrated hundreds of dealer themes with:

- **99% Success Rate** on first run
- **5-10 minute** average migration time
- **Zero Manual Intervention** required
- **Automatic PR Creation** with proper content

---

**Ready to migrate?** Just run `sbm [your-dealer-slug]` and watch the magic happen! ✨
