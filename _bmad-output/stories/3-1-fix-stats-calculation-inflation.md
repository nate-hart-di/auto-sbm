# Story 3.1: Fix Stats Calculation Inflation

Status: ready-for-dev

## Story

As a User,
I want the CLI stats to accurately reflect my actual migration work without inflated estimates,
So that I can trust the numbers shown in `sbm stats` and they match the real data in Firebase.

## Acceptance Criteria

**Given** I have 164 unique migrations in Firebase with varying data completeness
**When** I run `sbm stats`
**Then** the displayed line count reflects ONLY actual merged PR data from Firebase
**And** migrations without PR data are NOT inflated with 500-line estimates
**And** duplicate runs for the same slug are handled correctly
**And** the "Sites Migrated" count shows unique migrations (164)
**And** the "Lines Migrated" count shows actual sum from `lines_migrated` field

**Given** I have MERGED PRs with `lines_migrated = 0` in Firebase
**When** the backfill script runs
**Then** it populates these runs with actual GitHub PR line counts
**And** duplicate runs for the same slug get deduplicated (LATEST run keeps lines, older runs set to 0)
**And** all MERGED PRs have accurate line counts after backfill

## Tasks / Subtasks

### Task 1: Analyze Current Stats Calculation Logic (AC: Understand the problem)
- [x] Review `sbm/utils/tracker.py:370-383` estimation fallback logic
- [x] Identify why 109 migrations are being estimated at 500 lines each
- [x] Check Firebase data for missing `lines_migrated` fields
- [x] Verify: 40 MERGED PRs have `lines_migrated = 0`
- [x] Verify: 91 success runs but only 55 unique slugs (36 duplicates)

**Findings:**
```
Total unique migrations in Firebase: 164
Migrations with actual SUCCESS run data: 55
Migrations WITHOUT run data: 109

Lines from actual runs: 21,974
Estimated lines (109 × 500): 54,500
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL SHOWN IN CLI: 76,474 ⚠️ INFLATED BY 54,500
```

### Task 2: Remove Estimation Fallback from CLI Stats (AC: No fake data shown)
- [ ] Remove or disable estimation logic at `sbm/utils/tracker.py:378-383`
- [ ] Update `get_migration_stats()` to return ONLY actual data from Firebase
- [ ] Add flag/setting if estimation is needed for specific use cases (disabled by default)
- [ ] Update tests to reflect new behavior (no estimation in stats display)

**Code to Remove/Modify:**
```python
# REMOVE THIS ESTIMATION LOGIC (lines 378-383)
if migrations_without_runs:
    # Add estimate: 500 lines per migration for those without run data
    estimated_lines = len(migrations_without_runs) * 500
    run_metrics["total_lines_migrated"] += estimated_lines
    run_metrics["total_time_saved_h"] = round(run_metrics["total_lines_migrated"] / 800.0, 1)
    run_metrics["estimated"] = True  # Flag to indicate some values are estimated
```

### Task 3: Run Firebase Backfill to Populate Missing Data (AC: All MERGED PRs have line counts)
- [ ] Run `python scripts/backfill_firebase_runs.py --dry-run` to preview changes
- [ ] Verify it will populate the 40 MERGED PRs with `lines_migrated = 0`
- [ ] Run `python scripts/backfill_firebase_runs.py --force` to apply changes
- [ ] Verify all MERGED PRs now have accurate `lines_migrated` from GitHub
- [ ] Document any PRs that still have 0 lines (invalid/closed PRs)

**Expected Outcome:**
- 40 MERGED PRs get populated with actual GitHub line counts
- Duplicate runs handled: LATEST run keeps lines, older runs set to 0

### Task 4: Clean Up Duplicate Runs (AC: No duplicate slugs in success runs)
- [ ] Run `python scripts/cleanup_firebase_garbage.py` to identify duplicates
- [ ] Review duplicate runs (same slug, multiple success entries)
- [ ] Determine if duplicates should be:
  - Deduplicated (keep only latest run)
  - OR Marked as non-success for older runs
  - OR Left as-is with only latest having lines_migrated > 0
- [ ] Document decision and implement cleanup if needed

### Task 5: Verify Accurate Stats Display (AC: CLI shows correct numbers)
- [ ] Run `sbm stats` and verify numbers match actual Firebase data
- [ ] Verify "Sites Migrated" = 164 (unique migrations)
- [ ] Verify "Lines Migrated" = sum of actual `lines_migrated` from MERGED PRs
- [ ] Verify "Time Saved" = Lines Migrated / 800 hours
- [ ] Compare with `python -c "from sbm.utils.tracker import get_migration_stats; print(get_migration_stats())"`
- [ ] Document baseline stats for future comparison

## Dev Notes

### Critical Context

**Branch:** `fix/slack-command-issues` (or create new branch `fix/stats-inflation`)

**Root Cause:**
The estimation fallback logic in `tracker.py` was designed to fill in missing data for migrations that don't have run records. However, it's inflating stats because:
1. 40 MERGED PRs have `lines_migrated = 0` (backfill didn't populate them)
2. 109 migrations appear in the `/migrations` node but don't have corresponding success runs
3. These 109 migrations get estimated at 500 lines each = 54,500 fake lines

**Files to Modify:**
1. `sbm/utils/tracker.py` - Remove/disable estimation logic
2. Firebase database - Run backfill script to populate missing data
3. Tests - Update to reflect no-estimation behavior

### Issue Details

#### Problem 1: Estimation Inflates Stats by 54,500 Lines

**Location:** `sbm/utils/tracker.py:378-383`

**Current Behavior:**
```python
migrations_without_runs = my_migrations - slugs_with_runs
# 164 total - 55 with runs = 109 without runs

if migrations_without_runs:
    estimated_lines = len(migrations_without_runs) * 500
    # 109 × 500 = 54,500 FAKE LINES
    run_metrics["total_lines_migrated"] += estimated_lines
```

**Expected Behavior:**
- Stats should show ONLY actual data from Firebase
- No estimation/inflation
- If data is missing, show what we have (not fake numbers)

#### Problem 2: 40 MERGED PRs Missing Line Counts

**Evidence:**
```bash
$ python3 -c "from sbm.utils.tracker import get_global_reporting_data, _get_reporting_user_id
all_runs, _ = get_global_reporting_data()
current_user_id = _get_reporting_user_id()
my_runs = [r for r in all_runs if r.get('_user') == current_user_id]
success_runs = [r for r in my_runs if r.get('status') == 'success']
merged_no_lines = [r for r in success_runs if r.get('pr_state') == 'MERGED' and r.get('lines_migrated', 0) == 0]
print(f'MERGED PRs with lines_migrated = 0: {len(merged_no_lines)}')"

# Output: MERGED PRs with lines_migrated = 0: 40
```

**Root Cause:**
- Backfill script exists (`scripts/backfill_firebase_runs.py`)
- But it hasn't been run recently OR it failed to populate these specific PRs
- Need to re-run backfill with `--force` flag

#### Problem 3: Duplicate Runs (91 runs → 55 unique slugs)

**Evidence:**
```
My total runs: 100
My success runs: 91
Unique slugs with SUCCESS runs: 55
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Duplicate runs: 36 (91 - 55)
```

**Examples:**
- `loufuszcdjrvincennes` PR#20370 appears 2x
- `loufuszchryslerjeepdodgeramfiat` PR#20390 appears 3x

**Impact:**
- Inflates run count (but not migration count)
- May cause incorrect time calculations
- Should be deduplicated OR only latest should have lines_migrated > 0

### Decision Needed

**Question for User:**
Should the estimation fallback be:
1. **Completely removed** (recommended) - Show only actual data
2. **Disabled by default with flag** - `--include-estimates` to enable
3. **Kept but fixed** - Only estimate for migrations with NO run data at all (not for runs with 0 lines)

**Recommendation:** Option 1 (completely remove) - Stats should be accurate, not estimated.

### References

- Firebase Data Investigation: 2026-01-14
- Code Review: Story 2-8 (completed)
- Backfill Script: `scripts/backfill_firebase_runs.py`
- Cleanup Script: `scripts/cleanup_firebase_garbage.py`
- Verify Script: `scripts/verify_firebase_data.py`

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### File List

- `sbm/utils/tracker.py` - Remove estimation fallback (lines 378-383)
- Firebase Database - Run backfill to populate missing `lines_migrated`
- Tests - Update expectations to reflect no estimation

### Completion Notes

*To be filled when story is completed*

### Change Log

- 2026-01-14: Story 3-1 created - Fix stats calculation inflation issue identified during code review
