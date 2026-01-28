# Story 2.3: Resilience & Offline Queue

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Mobile User,
I want my stats to be saved even when I'm offline,
So that I don't lose data or get blocked by connection errors.

## Acceptance Criteria

- [x] **Scenario 1: Offline Execution**
  - **Given** I am offline or Firebase is down
  - **When** I complete a migration
  - **Then** the CLI does NOT hang or crash
  - **And** the run is marked as "pending_sync" in the local JSON

- [x] **Scenario 2: Background Sync**
  - **Given** I have runs marked as "pending_sync"
  - **When** the application starts or finishes a run (and connectivity is restored)
  - **Then** a background process attempts to sync all pending items
  - **And** successfully synced items are updated to "synced" status locally

- [x] **Scenario 3: Retry Logic**
  - **Given** a sync attempt fails
  - **When** the background process runs
  - **Then** it retries the upload
  - **And** logs errors gracefully without determining the user experience

## Tasks / Subtasks

- [x] Task 1: Update `sbm/utils/tracker.py` Data Structure
  - [x] Add `sync_status` field to `run_entry` (enums: 'synced', 'pending_sync', 'failed')
  - [x] Default new runs to 'pending_sync' before attempting upload
  - [x] Update `record_run` to save this status

- [x] Task 2: Implement Sync Queue Logic
  - [x] Create `process_pending_syncs()` function in `tracker.py`
  - [x] Iterate through `runs` where `sync_status` is 'pending_sync' or 'failed'
  - [x] Attempt `_sync_to_firebase` for each
  - [x] Update local status to 'synced' on success
  - [x] Persist changes to `~/.sbm_migrations.json`

- [x] Task 3: Integrate with Background Process
  - [x] Ensure `trigger_background_stats_update` calls `process_pending_syncs()`
  - [x] Verify `internal-refresh-stats` command invokes this logic

- [x] Task 4: Testing & Verification
  - [x] Unit test: Mock offline state, verify run saved as 'pending_sync'
  - [x] Integration test: Mock network failure then success, verify eventual sync
  - [x] Verify no CLI blocking during outages

## Dev Notes

- Leverage the existing `internal-refresh-stats` command if possible.
- Ensure we don't overwrite `last_updated` timestamps during sync if they reflect migration time.
- Be careful with concurrency if multiple CLIs are running (file locking might be needed for the JSON, but `tracker.py` already uses some basic read/write, simpler is better for now).
### Review Follow-ups (AI Code Review - 2026-01-11)

**Issues Fixed:**
- [x] [AI-Review][Low] Test file tests/test_tracker_resilience.py added to git (was untracked)

**Verified Complete - All ACs Met:**
- [x] [AI-Review][AC1] sync_status field added to run_entry (tracker.py:190)
- [x] [AI-Review][AC1] Offline execution doesn't crash - error handling wraps Firebase calls
- [x] [AI-Review][AC2] process_pending_syncs() implemented (tracker.py:599-628)
- [x] [AI-Review][AC2] Successfully synced items marked as "synced" (tracker.py:619)
- [x] [AI-Review][AC3] Retry logic for failed syncs (tracker.py:615-625)
- [x] [AI-Review][AC3] Errors logged without crashing (debug logging throughout)
- [x] [AI-Review] internal-refresh-stats command calls process_pending_syncs (cli.py:1826)
- [x] [AI-Review] trigger_background_stats_update invokes internal-refresh-stats (tracker.py:580)
- [x] [AI-Review] Local JSON persists sync_status changes (tracker.py:628)
## Dev Agent Record

### Agent Model Used
- Antigravity

### Debug Log References
- Tests passed: `tests/test_tracker_resilience.py`

### Completion Notes List
- Verified implementation handles offline/online transitions correctly.
- Added tests for `record_run` offline and `process_pending_syncs` resilience.

### File List

**Modified Files**:
- `sbm/utils/tracker.py`
- `tests/test_tracker_resilience.py`
