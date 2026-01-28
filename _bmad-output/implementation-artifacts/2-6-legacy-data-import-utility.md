# Story 2.6: Legacy Data Import Utility

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a User,
I want to upload my old local history to the new system,
So that the team stats reflect all previous work, not just new runs.

## Acceptance Criteria

1.  **Given** I have a `~/.sbm_migrations.json` full of history
    **When** I run `scripts/stats/migrate_to_firebase.py`
    **Then** it reads all local runs
    **And** it uploads any runs missing from Firebase
    **And** it handles duplicates (idempotency)
    **And** it provides a progress bar and final summary of "Imported X runs"

## Tasks / Subtasks

- [x] Implement `migrate_to_firebase.py` script
    - [x] Create script file in `scripts/stats/`
    - [x] Implement argument parsing (optional, but good for CLI)
    - [x] Implement reading from `~/.sbm_migrations.json`
    - [x] Initialize Firebase connection (reuse `sbm.utils.firebase_sync` or similar)
    - [x] Loop through runs and check existence in Firebase
    - [x] Upload missing runs
    - [x] Add progress bar (using `rich.progress`)
    - [x] Print final summary
- [x] Verify script functionality
    - [x] Test with existing local history
    - [x] Test idempotency (run twice, ensure 0 imports second time)

## Dev Notes

- **Architecture Patterns:**
    - Use `sbm.utils.firebase_sync` for Firebase interactions if possible, or `firebase_admin` directly if internal APIs are not exposed for bulk import.
    - Ideally, reuse the `FirebaseSync.sync_run` logic or similar to ensure consistency with how CLI syncs data.
    - `~/.sbm_migrations.json` is the source of truth for local history.
- **Source Tree Components:**
    - `scripts/stats/migrate_to_firebase.py` (New)
    - `sbm/core/migration.py` (Reference for `MigrationRun` schema)
    - `sbm/utils/firebase_sync.py` (Reference / Reuse)

### Project Structure Notes

- Scripts should reside in `scripts/` directory.
- Ensure python path is handled correctly if importing `sbm` modules from specific script location (might need `sys.path.append` or run as module).

### References

- [Epic 2](file:///Users/nathanhart/auto-sbm/_bmad-output/epics.md)
- [Sprint Status](file:///Users/nathanhart/auto-sbm/_bmad-output/sprint-status.yaml)

## Dev Agent Record

### Agent Model Used

Gemini 2.0 Flash

### Debug Log References

### Completion Notes List

- Implemented `migrate_to_firebase.py` in `scripts/stats/`
- Added comprehensive unit tests in `tests/test_migration_script.py`
- Confirmed tests pass

### File List
- scripts/stats/migrate_to_firebase.py
- tests/test_migration_script.py
### Review Follow-ups (AI)
- [x] [AI-Review][Pass] Verified implementation and tests. Script functions as expected. Dev Record present.
