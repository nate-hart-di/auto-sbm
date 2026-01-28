# Story 2.5: Bulk Migration Duplicate Prevention

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a User performing bulk operations,
I want to be warned if I'm about to run a migration that my teammate has already done,
So that I don't waste time or create duplicate PRs.

## Acceptance Criteria

- [x] **Scenario 1: Bulk Input with Duplicates**
  - **Given** I run `sbm auto @list.txt` (or similar) where `list.txt` contains `site-a`, `site-b`
  - **And** `site-a` has already been migrated by "teammate-1" (recorded in Firebase)
  - **And** I am online
  - **When** the CLI parses the input
  - **Then** it pauses and displays a warning:
    > "⚠️ The following slugs have already been migrated:"
    > " - site-a (migrated by teammate-1)"
  - **And** it asks: "Skip duplicates? [Y/n]"

- [x] **Scenario 2: Skipping Duplicates**
  - **Given** the warning above is displayed
  - **When** I answer "Y" (or default)
  - **Then** `site-a` is removed from the execution list
  - **And** the migration proceeds only for `site-b`

- [x] **Scenario 3: Forcing Duplicates**
  - **Given** the warning above is displayed
  - **When** I answer "n"
  - **Then** the migration proceeds for BOTH `site-a` and `site-b`

- [x] **Scenario 4: Offline / Firebase Unreachable**
  - **Given** I am offline
  - **When** I run the bulk command
  - **Then** it prints a warning: "⚠️ Cannot check global history (Offline). Proceeding with local checks only."
  - **And** it proceeds without blocking (standard behavior)

## Tasks / Subtasks

- [x] Task 1: Update `sbm/utils/tracker.py`
  - [x] Implement `get_all_migrated_slugs() -> dict[str, str]` (slug -> user_id)
  - [x] Fetch all users' runs from Firebase (optimize payload if possible, e.g. shallow=True or specific fields if structure allows)
  - [x] Return dictionary of migrated slugs

- [x] Task 2: Update `sbm/cli.py` (Command Processing)
  - [x] Identify where `_expand_theme_names` is used (likely `auto` or `migrate` command)
  - [x] After expansion, call `tracker.get_all_migrated_slugs()`
  - [x] Compare input slugs against global history
  - [x] If duplicates found, render warning using Rich table
  - [x] Prompt user using `click.confirm("Skip duplicates?", default=True)`
  - [x] Filter list based on response

- [x] Task 3: Testing
  - [x] Unit test: `tracker.get_all_migrated_slugs` with mock Firebase data
  - [x] Integration test: CLI with mocked duplicates, verifying prompt and list filtering

## Dev Notes

- **Firebase Structure**: `users/{uid}/runs/{push_id}/slug`. We need to iterate all of this.
- **Performance**: This might be slow if there are thousands of runs.
  - *Optimization*: Store a global `/migrations/{slug}` index in Firebase?
  - *Constraint*: We agreed to `users/{uid}/runs`.
  - *Mitigation*: Client-side optimization. Fetch distinct users first, then parallel fetch? Or just one big fetch. For <10k runs it's fine.
- **CLI Location**: Need to find exactly where `theme_names` are processed in `cli.py`.

### Review Follow-ups (AI Code Review - 2026-01-11)

**Issues Fixed:**
- [x] [AI-Review][Low] Test file tests/test_duplicate_prevention.py added to git (was untracked)
- [x] [AI-Review] All tasks now marked complete [x]

**Verified Complete - All ACs Met:**
- [x] [AI-Review][AC1] Bulk input parsed and checked against Firebase (cli.py:1115-1121)
- [x] [AI-Review][AC1] Warning table displayed with duplicates (cli.py:1124-1136)
- [x] [AI-Review][AC1] Prompt asks "Skip duplicates?" via InteractivePrompts (cli.py:1139)
- [x] [AI-Review][AC2] Answer "Y" filters out duplicates (cli.py:1141-1146)
- [x] [AI-Review][AC3] Answer "n" proceeds with all sites (cli.py:1148)
- [x] [AI-Review][AC4] Offline handled gracefully - returns empty dict, proceeds (tracker.py:644)
- [x] [AI-Review] get_all_migrated_slugs() implemented in tracker & firebase_sync (tracker.py:642, firebase_sync.py:273)
- [x] [AI-Review] InteractivePrompts.confirm_duplicate_migration() implemented (prompts.py:479)
- [x] [AI-Review] Duplicate detection integrated into auto command pre-flight (cli.py:1111-1164)
- [x] [AI-Review] Non-interactive mode (--yes) logs warning but proceeds (cli.py:1158-1160)
- [x] [AI-Review] Unit tests cover online/offline scenarios and skip/force prompts

## Dev Agent Record

- **Outcome**: Successfully implemented bulk duplicate prevention.
- **Details**:
  - Implemented `get_all_migrated_slugs` in `sbm/utils/tracker.py` to fetch runs from all users in Firebase.
  - Updated `sbm/cli.py` `auto` command to perform pre-flight duplicate check against global history.
  - Implemented logic to handle bulk execution: capturing duplicate prompts unless user explicitly requested non-interactive mode.
  - Resolved regression where `sbm auto` forced `yes=True` for bulk lists, enabling safety prompts by default.
- **Testing**: Added `tests/test_duplicate_prevention.py` covering success/offline scenarios for tracker and skip/force scenarios for CLI interactively.

## File List

- sbm/cli.py
- sbm/utils/tracker.py
- sbm/ui/prompts.py
- tests/test_duplicate_prevention.py
