# SBM Tool V2 - AI Assistant Quickstart Guide

## 🤖 Project Context Summary

**SBM Tool V2** is a Site Builder Migration tool for DealerInspire dealer websites. It automates the conversion of legacy SCSS themes to Site Builder-compliant format.

### Core Purpose

- **Migrate** legacy dealer themes to Site Builder standards
- **Convert** SCSS mixins to CSS equivalents
- **Standardize** breakpoints and color variables
- **Automate** GitHub PR creation for migrations

### Technology Stack

- **Language**: Python 3.8+
- **CLI Framework**: Click
- **SCSS Processing**: Custom regex-based processor
- **Git Integration**: GitHub CLI (`gh`)
- **Package Management**: pip/setuptools

## 🏗️ Architecture Overview

### Project Structure

```
sbm-v2/
├── sbm/                    # Main package
│   ├── cli.py             # Click-based CLI interface
│   ├── config.py          # Configuration management
│   ├── core/              # Core functionality
│   │   ├── validation.py  # Theme validation logic
│   │   ├── workflow.py    # Migration orchestration
│   │   └── git_operations.py # GitHub integration
│   ├── scss/              # SCSS processing
│   │   └── processor.py   # Main SCSS conversion engine
│   ├── oem/               # OEM-specific logic
│   └── utils/             # Utility functions
├── docs/                  # Documentation
├── tests/                 # Test suite
└── scripts/               # Helper scripts
```

### Key Components

1. **CLI Interface** (`sbm/cli.py`)

   - Commands: `migrate`, `doctor`, `validate`, `create-pr`
   - Flags: `--force`, `--create-pr`, `--dry-run`, `--export-log`
   - Shell completion support

2. **SCSS Processor** (`sbm/scss/processor.py`)

   - Mixin replacement engine
   - Color variable conversion
   - Breakpoint standardization
   - File tracking and aggregation

3. **Validation Engine** (`sbm/core/validation.py`)

   - File structure checks
   - Required file detection
   - Environment validation

4. **Git Operations** (`sbm/core/git_operations.py`)
   - GitHub PR creation
   - Stellantis-specific PR templates
   - Auto-reviewer assignment

## 🎯 Key Transformations

### File Mappings

- `lvdp.scss` → `sb-vdp.scss` (Vehicle Detail Page)
- `lvrp.scss` → `sb-vrp.scss` (Vehicle Results Page)
- `inside.scss` → `sb-inside.scss` (Interior pages)

### SCSS Conversions

```scss
// Mixin Replacements
@include flexbox() → display: flex
@include absolute(10px, 20px) → position: absolute; top: 10px; right: 20px
@include border-radius(5px) → border-radius: 5px

// Color Variables
#093382 → var(--primary, #093382)
#fff → var(--white, #fff)

// Breakpoint Standardization
920px → 768px (tablet)
1200px → 1024px (desktop)
```

### Configuration Auto-Detection

- **DI Platform**: `~/di-websites-platform` (auto-detected)
- **GitHub Token**: Read from `~/.cursor/mcp.json`
- **Context7 API**: Read from `~/.cursor/mcp.json`

## 🔧 Development Patterns

### Code Style

- **Type Hints**: Used throughout for better IDE support
- **Error Handling**: Comprehensive try/catch with user-friendly messages
- **Logging**: Structured logging with different levels
- **Testing**: Pytest-based with real-world test cases

### Key Design Decisions

1. **Regex-based SCSS processing** (not AST) for flexibility
2. **Auto-detection over configuration** for user experience
3. **GitHub CLI integration** over API for simplicity
4. **Modular architecture** for extensibility

### Memory-Critical Information

- **Breakpoints**: Use 768px and 1024px, NOT 920px
- **Color Variables**: Always wrap hex values in CSS variables
- **Mixin Replacement**: Complete automation, no manual intervention
- **PR Templates**: Stellantis-specific with dynamic content
- **File Tracking**: Aggregate all created/modified files for PR descriptions

## 🚨 Common Issues & Solutions

### Installation Issues

- **Permission denied**: Remove old aliases, reinstall with `pip install -e .`
- **Command not found**: Add `~/.local/bin` to PATH
- **GitHub auth**: Ensure `gh auth login` is completed

### Migration Issues

- **Validation failures**: Use `sbm doctor` to diagnose
- **Missing files**: Check for `style.scss`, `style.css`, `di-acf-json/`
- **SCSS errors**: Review processor logic for edge cases

### PR Creation Issues

- **GitHub CLI not found**: Install and authenticate `gh`
- **Repository detection**: Ensure working in git repository
- **Template errors**: Check Stellantis template logic

## 📋 CLI Command Reference

### Primary Commands

```bash
sbm migrate [--force] [--create-pr] [--dry-run]
sbm doctor [--export-log FILE]
sbm validate [DEALER_SLUG]
sbm create-pr
sbm install-completion
```

### Flag Aliases

- `-f` = `--force`
- `-g` = `--create-pr`
- `-n` = `--dry-run`
- `-e` = `--export-log`
- `-h` = `--help`

## 🎭 AI Assistant Guidelines

### When Helping Users

1. **Always run `sbm doctor`** first to diagnose issues
2. **Check file structure** before suggesting fixes
3. **Use `--dry-run`** to preview changes safely
4. **Reference existing patterns** in the codebase
5. **Test on simple themes** before complex ones

### Code Modification Principles

1. **Follow existing patterns** in the codebase
2. **Maintain backward compatibility** where possible
3. **Add comprehensive error handling**
4. **Update tests** for any logic changes
5. **Document breaking changes** in CHANGELOG.md

### Debugging Approach

1. **Start with environment validation** (`sbm doctor`)
2. **Check file permissions** and paths
3. **Verify GitHub CLI authentication**
4. **Test SCSS processor** with simple inputs
5. **Review git repository state**

## 🔄 Recent Major Changes

### Version 2.0 Features

- **Enhanced validation** with detailed file structure checks
- **Comprehensive mixin replacement** covering all CommonTheme mixins
- **Color variable conversion** for hex values
- **GitHub PR integration** with Stellantis templates
- **Shell completion** support
- **Auto-detection** of configuration settings

### Breaking Changes

- Removed dependency on environment variables
- Changed default breakpoints from 920px to 768px
- Updated PR template structure

## 📚 Key Files to Reference

### Core Logic

- `sbm/scss/processor.py` - Main SCSS conversion logic
- `sbm/core/workflow.py` - Migration orchestration
- `sbm/core/validation.py` - Validation rules

### Configuration

- `sbm/config.py` - Auto-detection and settings
- `pyproject.toml` - Package configuration
- `requirements.txt` - Dependencies

### Documentation

- `docs/index.md` - Main documentation hub
- `docs/development/CHANGELOG.md` - Recent changes
- `docs/analysis/K8_COMPLIANCE_SUMMARY.md` - Standards compliance

### Testing

- `test_real_world.py` - Real dealer theme tests
- `tests/` - Unit test suite

---

**Quick Start for AI Assistants**: Run `sbm doctor` to understand the current environment, then review the SCSS processor logic in `sbm/scss/processor.py` to understand the core transformations. The tool is designed to be self-diagnosing and user-friendly.
