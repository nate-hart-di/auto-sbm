# Auto-SBM Update Instructions

## Quick Update (Most Users)

```bash
# 1. Go to auto-sbm directory
cd /path/to/auto-sbm

# 2. Pull latest changes
git pull origin master

# 3. Reinstall
pip install -e .
```

That's it! The new formatter and fixes are now active.

## Detailed Update (If Issues Arise)

### Step 1: Check Current Installation

```bash
# See where sbm is installed
which sbm

# Check current branch
cd /path/to/auto-sbm
git branch

# Check for local changes
git status
```

### Step 2: Handle Local Changes

If you have uncommitted changes:

```bash
# Option A: Stash changes temporarily
git stash

# Option B: Commit your changes
git add .
git commit -m "Local changes before update"

# Option C: Create a backup branch
git checkout -b backup-$(date +%Y%m%d)
git add .
git commit -m "Backup before update"
git checkout master
```

### Step 3: Pull Updates

```bash
# Make sure you're on master
git checkout master

# Pull latest
git pull origin master

# If you stashed, reapply:
git stash pop
```

### Step 4: Reinstall Dependencies

```bash
# Option 1: Standard pip
pip install -e .

# Option 2: With UV (faster)
uv sync

# Option 3: Full reinstall (if issues)
pip uninstall auto-sbm
pip install -e .
```

### Step 5: Verify Installation

```bash
# Should show updated version
sbm --version

# Test migration (no PR, just verify)
sbm lexusofclearwater --no-create-pr --skip-just --force-reset --yes
```

## Troubleshooting

### "sbm command not found"

```bash
# Reinstall the entry point
cd /path/to/auto-sbm
pip install -e .

# Or add to PATH
export PATH="$HOME/.local/bin:$PATH"
```

### "Import Error: No module named sbm.scss.formatter"

```bash
# Ensure you pulled latest code
cd /path/to/auto-sbm
git pull origin master

# Force reinstall
pip install -e . --force-reinstall
```

### "Prettier not available" still showing

This is now expected and harmless - the built-in formatter runs instead.

### Formatting looks wrong

```bash
# The formatter uses 2-space indentation by default
# If you need to adjust, edit sbm/scss/formatter.py:
# SCSSFormatter(indent_size=4)  # For 4 spaces
```

## What Changed?

### Files Added
- `sbm/scss/formatter.py` - New built-in formatter

### Files Modified
- `sbm/oem/default.py` - Fixed Stellantis styles bug
- `sbm/core/maps.py` - Fixed duplicate content bug
- `sbm/core/migration.py` - Integrated formatter, removed prettier

### Files Removed
- None (backwards compatible)

## Rollback Instructions

If you need to revert:

```bash
cd /path/to/auto-sbm

# Find previous commit
git log --oneline -10

# Rollback to specific commit
git checkout <commit-hash>
pip install -e .
```

## Need Help?

- Slack: #auto-sbm channel
- GitHub: [Create an issue](https://github.com/nate-hart-di/auto-sbm/issues)
- Contact: @nate-hart-di
