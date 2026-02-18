# Tech Spec: Fix `lines_migrated` to Match GitHub PR Additions

**Date:** 2026-02-13
**Scope:** Bug fix — 3 files, focused change
**Execution Mode:** Quick Dev (Direct)

---

## Problem

`lines_migrated` is wrong for virtually every PR. The Slack app and `sbm stats` commands report incorrect counts because:

1. **Wrong source of truth:** [migrate_styles()](file:///Users/nathanhart/auto-sbm/sbm/core/migration.py#L473-L565) counts output SCSS file lines, not GitHub PR additions
2. **Unreliable override:** [fetch_pr_additions()](file:///Users/nathanhart/auto-sbm/sbm/utils/github_pr.py#L134-L175) runs immediately after PR creation (before GitHub computes diff stats), often returning `None` → falls back to wrong local count
3. **Broken backfill:** [daily_firebase_sync.py](file:///Users/nathanhart/auto-sbm/scripts/daily_firebase_sync.py#L181) only corrects `lines_migrated` when existing value is `0`, never fixing wrong non-zero values

## Requirement

**`lines_migrated` MUST always match the GitHub PR additions count** — total lines added across ALL files in the PR.

---

## Tasks

### Task 1: Make `fetch_pr_additions()` more reliable

**File:** `sbm/utils/github_pr.py`

| Change                  | Before  | After      |
| ----------------------- | ------- | ---------- |
| `max_retries` default   | 2       | 3          |
| Delay backoff           | 2s, 4s  | 2s, 4s, 8s |
| Final failure log level | `debug` | `warning`  |

### Task 2: Fix daily sync to always correct wrong values

**File:** `scripts/daily_firebase_sync.py` (~line 181)

```diff
-if pr_data["lines"] > 0 and run.get("lines_migrated", 0) == 0:
+if pr_data["lines"] > 0 and run.get("lines_migrated", 0) != pr_data["lines"]:
     updates["lines_migrated"] = pr_data["lines"]
```

This ensures the daily sync corrects **any** mismatch, not just zero-values.

### Task 3: Add `github_additions` to `fetch_pr_additions()` return for merged PRs in daily sync

**File:** `scripts/daily_firebase_sync.py`

The script already fetches `additions` from `gh pr list --json additions`. Just need to remove the `== 0` guard. Task 2 covers this.

---

## Files to Modify

| File                                                                                       | Change                          | Risk |
| ------------------------------------------------------------------------------------------ | ------------------------------- | ---- |
| [github_pr.py](file:///Users/nathanhart/auto-sbm/sbm/utils/github_pr.py)                   | Increase retries + log level    | Low  |
| [daily_firebase_sync.py](file:///Users/nathanhart/auto-sbm/scripts/daily_firebase_sync.py) | Remove `== 0` guard on backfill | Low  |

> **Note:** No changes needed to `migration.py` or `cli.py` — the override plumbing at [line 1145-1150](file:///Users/nathanhart/auto-sbm/sbm/core/migration.py#L1142-L1150) already works correctly when `fetch_pr_additions()` succeeds.

## Files NOT Modified (and why)

| File                    | Reason                                                                |
| ----------------------- | --------------------------------------------------------------------- |
| `sbm/core/migration.py` | Override logic at L1145-1150 already correct                          |
| `sbm/cli.py`            | Auto/post-migrate paths already use `github_additions` when available |
| `sbm/utils/tracker.py`  | Just stores whatever `lines_migrated` it receives — no logic to fix   |

---

## Acceptance Criteria

- [ ] `fetch_pr_additions()` retries 3 times with 2/4/8s delays
- [ ] `fetch_pr_additions()` logs a warning (not debug) on final failure
- [ ] Daily sync updates `lines_migrated` for **any** mismatch with GitHub, not just when value is 0
- [ ] Existing tests pass: `pytest tests/test_stats_git_resilience.py -v`
- [ ] Unit test added for new retry behavior

---

## Verification

```bash
# Run existing tests
source .venv/bin/activate && python -m pytest tests/test_stats_git_resilience.py tests/test_migration_stats_fix.py -v

# Manual: run daily sync and verify a known-incorrect PR gets corrected
python scripts/daily_firebase_sync.py
```
