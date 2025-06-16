# Dealer Theme Setup Workflow - CRITICAL PROCESS

## 🚨 REQUIRED PRE-MIGRATION STEPS

**IMPORTANT**: Dealer theme directories do NOT exist until you create them through this workflow. You CANNOT run SBM migrations on non-existent themes.

### Complete Workflow Steps

#### 1. Switch to Main and Pull Latest Changes

```bash
cd /path/to/di-websites-platform
git checkout main
git pull
```

#### 2. Create SBM Branch with Correct Naming Format

```bash
git checkout -b [DEALER_SLUG]-sbm[MMYY]
```

**CRITICAL**: Branch naming format is `{slug}-sbm{MMYY}` where:

- `MMYY` = Current month (MM) + Current year (YY)
- Example: June 2025 = `0625` (NOT 1224 or any other format)
- Example: `roncartercdjrinalvin-sbm0625`

#### 3. Start Dealer Theme (Creates Directory Structure)

```bash
# CRITICAL: Must be run from di-websites-platform directory
cd /path/to/di-websites-platform
just start [DEALER_SLUG]
```

**CRITICAL**: The `just start` command MUST be run from inside the `di-websites-platform` directory where the `justfile` exists.

This command:

- Creates the dealer theme directory structure
- Builds Docker containers
- Sets up the development environment
- **Takes several minutes to complete**

#### 4. Wait for Docker Container Build

- Monitor the terminal output
- Wait for "Container build complete" or similar message
- Ensure all services are running properly

#### 5. Run SBM Migration

```bash
# Navigate back to SBM tool directory
cd /path/to/sbm-v2
sbm migrate [DEALER_SLUG]
```

#### 6. Post-Migration Steps

```bash
# Create PR
sbm create-pr

# Or manual PR creation if needed
cd /path/to/di-websites-platform
git add .
git commit -m "SBM migration for [DEALER_SLUG]"
git push origin [DEALER_SLUG]-sbm[MMYY]
```

### Common Issues

#### Branch Naming Errors

- ❌ **WRONG**: `roncartercdjrinalvin-sbm1224` (using wrong month/year)
- ✅ **CORRECT**: `roncartercdjrinalvin-sbm0625` (current month/year)

#### Directory Not Found

- **Cause**: Trying to run SBM before `just start` creates the directory
- **Solution**: Always run `just start [slug]` first

#### Docker Container Issues

- **Cause**: Containers not fully built before running migration
- **Solution**: Wait for complete build process before proceeding

#### Wrong Directory for just start

- ❌ **WRONG**: Running `just start` from `sbm-v2` directory
- ✅ **CORRECT**: Running `just start` from `di-websites-platform` directory
- **Error**: `error: Recipe optimized-up has unknown dependency health`
- **Solution**: Always `cd` to `di-websites-platform` before running `just start`

### Integration with SBM Tool

The SBM tool expects:

1. Dealer theme directory to exist (created by `just start`)
2. Proper git branch setup
3. Docker containers running
4. All theme files properly structured

### Documentation Update Required

This workflow was NOT properly documented in previous versions. All AI assistants and users must follow this complete process for successful SBM migrations.
