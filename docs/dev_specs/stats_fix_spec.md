# Dev Spec: SBM Stats Fixes & Alignment

## 1. Overview
This specification addresses issues with the SBM Stats system, focusing on:
1.  **Firebase Access**: Ensuring all authenticated users can read/write stats (Global Sync).
2.  **Time Saved Metric**: Restoring the "Time Saved" display in all CLI views.
3.  **Slack Alignment**: Ensuring Slack app reports match CLI stats 100%.

## 2. Firebase Access (Global Janitor)
**Requirement**: "firebase database read/write/admin access for ALL USERS"
**Status**: Partially Implemented in Code, Needs Rules Validation.

*   **Code**: `sbm/utils/firebase_sync.py` now supports `fetch_all_users_raw()` via REST.
*   **Logic**: `sbm/cli.py` -> `_update_recent_pr_statuses` iterates through ALL runs to refresh PR status.
*   **Action Items**:
    *   Verify `sbm/cli.py` uses `sync.update_run` with the correct `user_id` (owner) when acting as a janitor.
    *   **Validation**: Confirm Firebase Rules (server-side) allow `auth != null` to write to `users/$uid/runs`. (User has already provided the JSON, we assume it's applied or will be).

## 3. Time Saved Metric
**Requirement**: "restore time saved box to all related sbm stats commands"
**Status**: Missing in Team/Summary Views.

*   **Current State**:
    *   `sbm stats --history`: **Present** (Column "Time Saved").
    *   `sbm stats` (Summary): **Missing** in panels.
    *   `sbm stats --team` (Global): **Missing** in panels.
*   **Fix**:
    *   Modify `sbm/cli.py`:
        *   In `stats()` function, add "Time Saved" panel to `metric_panels` (Local).
        *   Add "Time Saved" panel to `global_panels` (Global Team).
    *   Calculation: `Lines Migrated / 800`.

## 4. Slack App Alignment
**Requirement**: "Stats cli and slack app aligned 100% of the time" & "/sbm-stats [options] commands all tested and fixed"
**Status**: Likely Aligned, Verification Needed.

*   **Code**: `scripts/stats/report_slack.py` uses `sbm.utils.tracker.get_global_reporting_data`.
*   **Logic**:
    *   `sbm stats --team` uses `get_global_reporting_data`.
    *   `/sbm-stats` uses `get_global_reporting_data`.
*   **Action Items**:
    *   Verify `report_slack.py` filters align with CLI filters (e.g., `verification-ping` exclusion).
    *   Test `report_slack.py` dry-run against `sbm stats --team` output to confirm numbers match.
    *   **Fix**: If numbers differ, trace `tracker.py` filtering logic.

## 5. Implementation Plan
1.  **Modify `sbm/cli.py`**:
    *   Add "Time Saved" to summary panels.
2.  **Verify `slack_listener.py`**:
    *   Ensure it correctly handles arguments (already reviewed, looks good).
3.  **Testing**:
    *   Run `sbm stats` to verify local panel.
    *   Run `sbm stats --team` to verify global panel.
    *   Run `python3 scripts/stats/report_slack.py --dry-run` to verify Slack output matches CLI.

## 6. Validation Scripts
*   `python3 scripts/verify_live_connection.py` (Connectivity)
*   `python3 scripts/stats/report_slack.py --dry-run` (Slack Parity)
