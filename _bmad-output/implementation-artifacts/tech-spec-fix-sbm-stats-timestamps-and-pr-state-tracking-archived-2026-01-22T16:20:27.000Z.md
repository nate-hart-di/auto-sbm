# Story 1.1: Fix SBM Stats Timestamps and PR State Tracking

Status: done
Created: 2026-01-20

## Story

As an SBM maintainer,
I want migration stats to reflect accurate PR timestamps and states,
so that historical metrics and in-progress work are tracked correctly.

## Acceptance Criteria

1. Firebase run records include `created_at`, `merged_at`, `closed_at`, and `pr_state` when available from GitHub.
2. Public stats count only merged PRs as complete; open/closed PRs are excluded from completion metrics.
3. CLI `sbm stats --history` displays PR state categories with clear status labels and a state-appropriate date column.
4. Date filtering and sorting use PR state-aware timestamps (merged/created/closed) instead of only `timestamp`.
5. Backfill/migration scripts fetch all three timestamps with validation, rate limiting, and retries.
6. Team stats obey the same merged-only completion rule as personal stats.

## Tasks / Subtasks

- [x] Capture PR timestamps on runs and backfills (AC: 1, 5)
  - [x] Include `created_at`, `merged_at`, `closed_at` in tracker records and PR metadata fetches
- [x] Update stats classification and filtering to use PR state (AC: 2, 4)
  - [x] Add and use PR completion classification in metrics and filters
- [x] Update CLI history rendering to show PR state and correct date (AC: 3)
- [x] Enforce merged-only logic in team stats (AC: 6)
- [x] Add tests for PR state filtering and team stats behavior (AC: 2, 4, 6)

### Review Follow-ups (AI)

- [x] [AI-Review][High] Add proper Story/AC/Tasks sections; "completed" status without ACs is invalid. `_bmad-output/implementation-artifacts/tech-spec-wip.md:1`
- [x] [AI-Review][High] Treat runs with `closed_at` but missing `pr_state` as closed to avoid false "in review". `sbm/utils/tracker.py:574`
- [x] [AI-Review][High] Team stats must count only merged PRs as complete. `sbm/utils/firebase_sync.py:389`
- [x] [AI-Review][Medium] Date filtering must use PR state-aware timestamps. `sbm/utils/tracker.py:253`
- [x] [AI-Review][Medium] Story file list must match actual git changes. `_bmad-output/implementation-artifacts/tech-spec-wip.md:1`
- [x] [AI-Review][Low] Add tests for new PR state logic and filtering. `tests/test_history_filtering.py:1`

## Dev Notes

- PR state priority: merged → open → closed (closed only when not open) → created → unknown.
- Backwards compatibility: runs without PR timestamps should be treated as `unknown` and excluded from completion metrics.
- CLI history should show a warning panel when PR timestamp data is missing.

## Dev Agent Record

### Agent Model Used

GPT-5 (Codex CLI)

### Debug Log References

- None

### Completion Notes List

- Added PR state-aware date selection for filtering/sorting and fixed closed PR classification.
- Updated team stats aggregation to include only merged PRs.
- Refined tests to cover PR state-based filtering and team stats behavior.
- Story reformatted to proper story structure and synced with actual changes.

### File List

- _bmad-output/implementation-artifacts/tech-spec-wip.md
- sbm/utils/tracker.py
- sbm/utils/firebase_sync.py
- tests/test_history_filtering.py
- tests/test_team_stats.py
