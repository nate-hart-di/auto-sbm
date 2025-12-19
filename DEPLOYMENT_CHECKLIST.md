# Deployment Checklist - Week of Dec 19, 2025

## Critical Fixes Deployed

### 1. Directions Row Styles Bug (Fixed)
- **Issue**: Stellantis-specific map styles were being added to ALL dealers
- **Fix**: DefaultHandler now returns empty strings for OEM-specific styles
- **Impact**: Lexus, Honda, etc. will no longer get Stellantis `#directionsBox` styles

### 2. Duplicate Map Content (Fixed)
- **Issue**: Map SCSS content was being added twice to sb-inside.scss
- **Fix**: Added deduplication by `commontheme_absolute` path
- **Impact**: ~35% reduction in generated file size, cleaner output

### 3. SCSS Formatting (New Feature)
- **Issue**: Relied on prettier (not always installed)
- **Fix**: Built-in SCSS formatter with zero external dependencies
- **Impact**: Consistent formatting for all users, regardless of environment

## User Update Instructions

### For All Users

```bash
# 1. Navigate to auto-sbm directory
cd /path/to/auto-sbm

# 2. Pull latest changes
git pull origin master

# 3. Reinstall with latest updates
pip install -e .

# Or if using UV:
uv sync

# 4. Verify installation
sbm --version

# 5. Test with a simple migration
sbm lexusofclearwater --no-create-pr --skip-just --force-reset --yes
```

### Verification Steps

After updating, verify the fixes:

1. **Test a non-Stellantis dealer** (e.g., Lexus, Honda):
   - Run migration
   - Check `sb-inside.scss` - should NOT contain `#directionsBox` or `/* Directions Row Styles */`

2. **Test map component migration**:
   - Run migration on a dealer with map components
   - Check for duplicate "Migrated from CommonTheme" comments - should only see ONE

3. **Check formatting**:
   - All `sb-*.scss` files should have consistent 2-space indentation
   - No mixed tabs/spaces

## Breaking Changes

**None** - All changes are backwards compatible. Existing migrations won't be affected.

## Rollback Plan

If issues arise:

```bash
# Revert to previous version
cd /path/to/auto-sbm
git checkout <previous-commit-hash>
pip install -e .
```

## Communication Template

Send to team:

---

**Subject: Auto-SBM Updates - Critical Fixes & Formatting**

Hi team,

We've deployed several critical fixes to auto-sbm this week:

1. ✅ **Fixed Stellantis styles bug** - Non-Stellantis dealers no longer get wrong map styles
2. ✅ **Eliminated duplicate map content** - Cleaner output, ~35% smaller files
3. ✅ **Built-in SCSS formatter** - No more prettier dependency issues

**Action Required:**
Please update your auto-sbm installation:
```bash
cd /path/to/auto-sbm
git pull origin master
pip install -e .
```

Test with: `sbm <dealer-name> --no-create-pr --skip-just --force-reset --yes`

Questions? Ping me!

---

## Post-Deployment Monitoring

- Monitor #auto-sbm Slack channel for issues
- Check first 5-10 migrations after update
- Review any error reports in stats tracking
