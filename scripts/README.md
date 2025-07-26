# Scripts Directory

This directory contains setup and utility scripts for auto-sbm development and deployment.

## Setup Scripts

### `setup.sh` - Main Setup Script
The primary setup script for auto-sbm. Handles fresh Mac installations by automatically installing:
- Homebrew (macOS package manager)
- Required CLI tools (git, gh, python3, uv)
- Python virtual environment
- Auto-sbm dependencies
- Global `sbm` command

**Usage:**
```bash
# From project root:
bash scripts/setup.sh

# Or use the root delegator:
bash setup.sh
```

**Features:**
- ✅ Automatic tool installation (no early exit on missing tools)
- ✅ Network retry logic for reliability
- ✅ 7-step progress indicators
- ✅ Error recovery and cleanup
- ✅ Installation validation
- ✅ Enhanced wrapper script with self-healing

### `setup-dev.sh` - Development Setup
Alternative setup script focused on development environment preparation.

## Design Decisions

### Why scripts/ Directory?
- **Clean project root**: Reduces clutter in the main directory
- **Organized maintenance**: All setup logic in one place  
- **Easy discovery**: Clear naming convention for utility scripts
- **Backward compatibility**: Root `setup.sh` delegates to `scripts/setup.sh`

### File Tracking Strategy
- **`scripts/setup.sh`** - Tracked in Git (core functionality)
- **`scripts/setup-dev.sh`** - Tracked in Git (development tool)
- **`setup.sh`** (root) - Tracked in Git (delegator for compatibility)

## Adding New Scripts

When adding new utility scripts:

1. Place them in this `scripts/` directory
2. Use descriptive names (`setup-*`, `deploy-*`, `test-*`)
3. Make them executable: `chmod +x scripts/new-script.sh`
4. Add documentation to this README
5. Update references in main documentation

## Related Files

- **`.pre-commit-config.yaml`** - Pre-commit hooks configuration (tracked in Git)
- **`uv.lock`** - UV dependency lockfile (tracked for reproducible builds)
- **`.gitignore`** - Properly configured to track necessary files