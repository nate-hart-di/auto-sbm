# Story 2.4: Team Stats Aggregation

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Team Lead,
I want to see the combined statistics of the entire team,
So that I can report on overall progress.

## Acceptance Criteria

- [x] **Scenario 1: Fetching Team Stats**
  - **Given** multiple users have synced data to Firebase
  - **When** I run `sbm stats --team`
  - **Then** the CLI queries Firebase for aggregated data
  - **And** displays "Team Total Migrations"
  - **And** displays "Team Total Time Saved"
  - **And** displays a breakdown of "Top Contributors"

- [x] **Scenario 2: Graceful Degradation**
  - **Given** I am offline or Firebase is unreachable
  - **When** I run `sbm stats --team`
  - **Then** the CLI falls back to calculating stats from the local `stats/` directory (legacy git-sync)
  - **And** displays a notice that data might be stale (or "Local Data Only")

- [x] **Scenario 3: Performance**
  - **Given** a large dataset
  - **When** I query team stats
  - **Then** the operation completes in under 2 seconds (optimized query or structure)

## Tasks / Subtasks

- [x] Task 1: Update `sbm/utils/tracker.py` to fetch from Firebase
  - [x] Implement `get_firebase_team_stats() -> dict`
  - [x] Query the `users` node (or a dedicated `stats` node if we built one, but accessing `users` root is acceptable for this scale)
  - [x] Aggregate: Total Migrations (unique slugs), Total Time Saved, Total Runs
  - [x] Aggregate: Per-user counts for "Top Contributors"

- [x] Task 2: Implement Fallback Logic
  - [x] Update `get_migration_stats` logic
  - [x] If `--team` is requested:
    - [x] Try `get_firebase_team_stats()`
    - [x] If fails/offline, use existing `_aggregate_global_stats()` (local files)
  - [x] Return source indication ("cloud" vs "local-disk")

- [x] Task 3: Update CLI `stats` command
  - [x] Add `--team` flag to `stats` command
  - [x] If `--team` is present, display a separate "Team Status" table/panel
  - [x] Show total migrations, time saved, and top 3 contributors

- [x] Task 4: Testing
  - [x] Unit test: Mock Firebase response and verify aggregation math
  - [x] Integration test: Mock offline and verify fallback to local stats

## Dev Notes

- Firebase Data Structure: `users/{user_id}/runs/{run_id}`.
- Aggregation Strategy: Fetching all `users` might be heavy if history grows.
  - *Optimization*: For now, we can fetch all. In future, we might want cloud functions to update a `/stats` root node.
  - *Constraint*: We don't have Cloud Functions in this scope. We must compute client-side.
  - *Mitigation*: Use `shallow=True` if possible to just get keys, but we need content. Or just limit to last N runs per user if possible.
  - *Decision*: Fetch everything for now (assuming < 1MB data total for the team). If it gets slow, we'll need a better structure.
### Review Follow-ups (AI Code Review - 2026-01-11)

**Issues Fixed:**
- [x] [AI-Review][Low] Test file tests/test_team_stats.py added to git (was untracked)

**Verified Complete - All ACs Met:**
- [x] [AI-Review][AC1] --team flag added to stats command (cli.py:1520)
- [x] [AI-Review][AC1] fetch_team_stats() delegates to FirebaseSync.fetch_team_stats() (tracker.py:631-637)
- [x] [AI-Review][AC1] Team stats display with totals, time saved, top contributors (cli.py:1549-1576)
- [x] [AI-Review][AC2] Fallback to local stats when Firebase unavailable (tracker.py:310-329)
- [x] [AI-Review][AC2] Source indication shows "firebase" or "local-disk"
- [x] [AI-Review][AC3] Performance: Single Firebase query to /users node
- [x] [AI-Review] FirebaseSync.fetch_team_stats() aggregates from users node (firebase_sync.py:217-271)
- [x] [AI-Review] Aggregation includes unique slugs, time saved, automation time, top contributors
- [x] [AI-Review] Unit tests in tests/test_team_stats.py verify aggregation math
- [x] [AI-Review] Scalability concern noted (client-side aggregation) but acceptable for current team size
## Dev Agent Record

### Agent Model Used
- Antigravity

### Debug Log References
- Tests passed: `tests/test_team_stats.py`

### Completion Notes List
- Implemented `fetch_team_stats` in `FirebaseSync` class (refactored).
- Updated CLI `stats` command to support `--team` flag.
- Verified fallback logic when Firebase is offline.

### File List

**Modified Files**:
- `sbm/cli.py`
- `sbm/utils/tracker.py`
- `sbm/utils/firebase_sync.py`
- `tests/test_team_stats.py`
