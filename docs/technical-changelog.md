# SBM Technical Changelog - Stats & Sync Updates

This document lists every specific file modification, addition, and creation performed during this session.

## Core Package Changes (`sbm/`)

### [MODIFY] [cli.py](file:///Users/nathanhart/auto-sbm/sbm/cli.py)

- **Restored "Time Saved" Column:**
  - Modified the `stats` command logic to include `Time Saved` in the output table.
  - Added calculation logic (`lines_migrated / 800`) to both summary panels and history table.
- **Refactored `_update_recent_pr_statuses` (Global Sync):**
  - Changed the update strategy from "current user only" to **"Global Janitor"**.
  - Replaced `sync.fetch_user_runs()` with `sync.fetch_all_users_raw()` to scan the entire database.
  - Implemented a flattening and sorting logic to prioritize the most recent 10 runs across _all_ users for PR status refreshing.
  - Added `verification-ping` filtering to the update loop to avoid checking test runs.

### [MODIFY] [tracker.py](file:///Users/nathanhart/auto-sbm/sbm/utils/tracker.py)

- **`get_global_reporting_data` Filtering:**
  - Added an explicit check within the user data loop: `if run.get("slug") == "verification-ping": continue`.
  - This ensures any global report (including Slack and CLI team stats) excludes internal test noise at the source.

### [MODIFY] [firebase_sync.py](file:///Users/nathanhart/auto-sbm/sbm/utils/firebase_sync.py)

- **User Mode (REST) Support:**
  - Implemented `fetch_all_users_raw()` using `requests` and the Firebase REST API (for reading the entire `/users` node).
  - Implemented `update_run()` using REST `PATCH` requests to allow users without Service Account keys to update PR statuses.
  - Added `fetch_user_runs()` to support REST-based retrieval for individual users.
- **Team Stats Filtering:**
  - Added the `verification-ping` exclusion filter in `fetch_team_stats()`.

---

## Script Changes (`scripts/`)

### [MODIFY] [slack_listener.py](file:///Users/nathanhart/auto-sbm/scripts/stats/slack_listener.py)

- **Default Behavior:** Changed default period from `all` to `week` (last 7 days).
- **Fallback Logic:** Updated fallback to default to `week` instead of `all` when no period is specified.

### [NEW] [delete_verification_run.py](file:///Users/nathanhart/auto-sbm/scripts/delete_verification_run.py)

- **Purpose:** Admin utility to purge the `verification-ping` entries from the Firebase database.
- **Logic:** Authenticates as admin, searches for the slug, and deletes the specific nodes to clean up legacy test data.

### [MODIFY] [force_debug_run.py](file:///Users/nathanhart/auto-sbm/scripts/force_debug_run.py)

- **Enhancement:** Modified to allow iterating through _all_ runs matching a specific slug (e.g., `newportlexus`) instead of just the first one found. This was used to diagnose specific stale data issues.

---

## Documentation & Planning Artifacts

### [NEW] [stats-sync-full-scope.md](file:///Users/nathanhart/auto-sbm/docs/stats-sync-full-scope.md)

- Summarizes the architectural decisions (Firebase Rules, Janitor strategy, REST support).

### [MODIFY] [task.md](file:///Users/nathanhart/.gemini/antigravity/brain/c46e5091-6a77-457b-b17c-72805de5b46a/task.md)

- Updated checklist to track Global Sync, Filtering, and restoration of features.

### [MODIFY] [walkthrough.md](file:///Users/nathanhart/.gemini/antigravity/brain/c46e5091-6a77-457b-b17c-72805de5b46a/walkthrough.md)

- Added specific validation steps for Firebase Rules (`auth != null`) and proof of Slack filtering.

diff --git a/sbm/cli.py b/sbm/cli.py
index d80e028..74f62af 100644
--- a/sbm/cli.py
+++ b/sbm/cli.py
@@ -2128,6 +2128,7 @@ def stats(
table.add_column("User", style="magenta")
table.add_column("Lines", justify="right", style="cyan")
table.add_column("PR", style="blue")

-            table.add_column("Time Saved", style="green")

               for run in runs:
                   # Determine PR completion state

  @@ -2153,11 +2154,46 @@ def stats(
  lines_migrated = run.get("lines_migrated", 0)
  report_path = run.get("report_path", "")

-                # Calculate Time Saved
-                manual_seconds = run.get("manual_estimate_seconds", 0)
-                time_saved_str = "N/A"
-                if manual_seconds:
-                    hours = int(manual_seconds // 3600)
-                    minutes = int((manual_seconds % 3600) // 60)
-                    time_saved_str = f"{hours}h {minutes}m"
-                 # Format values
                  lines_str = f"{lines_migrated:,}" if lines_migrated else "N/A"
                  report_str = report_path if report_path else "N/A"

                  # PR Link logic

-                pr_url = run.get("pr_url")
-                pr_state = run.get("pr_state", "UNKNOWN")
-
-                if pr_url:
-                    pr_display = f"[link={pr_url}]{pr_state}[/link]"
-                else:
-                    pr_display = pr_state
-
-                # Use PR Author if available, else User ID
-                user_display = run.get("pr_author")
-                if not user_display:
-                    user_display = run.get("user_id", "Unknown")
-
-                # Format user display (e.g. @username)
-                if user_display and not user_display.startswith("@"):
-                    user_display = f"@{user_display}"
-
-                table.add_row(
-                    _format_timestamp(run.get("timestamp")),
-                    run.get("slug", "unknown"),
-                    status_display,
-                    user_display,
-                    lines_str,
-                    pr_display,
-                    time_saved_str,
-                )
-                  pr_link = "N/A"
                   if run.get("pr_url"):
                       url = run.get("pr_url")
  @@ -2288,19 +2324,31 @@ def \_update_recent_pr_statuses(max_to_check: int | None = 10) -> None:
           sync = FirebaseSync()

*        # In User Mode (and generally for scalability), we only update the CURRENT user's runs.
*        # This allows everyone to maintain their own stats without needing Admin privileges
*        # to write to other users' nodes.
*        my_runs = sync.fetch_user_runs()  # Defaults to current user

-        # GLOBAL UPDATE STRATEGY
-        # We fetch ALL data so we can update ANY stale run, regardless of who owns it.
-        # This relies on Firebase Rules being set to allow global writes (auth != null).
-        all_data = sync.fetch_all_users_raw()

*        if not my_runs:

-        if not all_data:
             return

-        # Flatten all runs into a list of (user_id, run_id, run_data)
-        all_runs_flat = []
-        for u_id, u_data in all_data.items():
-            if not isinstance(u_data, dict):
-                continue
-            runs = u_data.get("runs", {})
-            for r_id, r_data in runs.items():
-                # Filter out verification-ping here too so we don't waste time checking it
-                if r_data.get("slug") == "verification-ping":
-                    continue
-                all_runs_flat.append((u_id, r_id, r_data))
-         checked = 0

*        # Sort runs by timestamp desc to check most recent first
*        sorted_runs = sorted(my_runs.items(), key=lambda x: x[1].get("timestamp", ""), reverse=True)

-        # Sort runs by timestamp desc to check most recent first (GLOBAL priority)
-        sorted_runs = sorted(all_runs_flat, key=lambda x: x[2].get("timestamp", ""), reverse=True)

*        for run_id, run_data in sorted_runs:

-        for user_id, run_id, run_data in sorted_runs:
             if max_to_check is not None and checked >= max_to_check:
                 break

@@ -2324,7 +2372,8 @@ def \_update_recent_pr_statuses(max_to_check: int | None = 10) -> None:
update_data = {k: v for k, v in update_data.items() if v is not None}

                 if update_data:

-                    sync.update_run(user_id=None, run_key=run_id, updates=update_data)

*                    # Pass the specific user_id of the run owner
*                    sync.update_run(user_id=user_id, run_key=run_id, updates=update_data)

                 checked += 1

diff --git a/sbm/utils/firebase*sync.py b/sbm/utils/firebase_sync.py
index 4479159..4148879 100644
--- a/sbm/utils/firebase_sync.py
+++ b/sbm/utils/firebase_sync.py
@@ -491,7 +491,7 @@ class FirebaseSync:
for *, run in runs_node.items():
if is_complete_run(run):
slug = run.get("slug")

-                        if not slug:

*                        if not slug or slug == "verification-ping":
                               continue
                           existing = unique_complete_by_slug.get(slug)
                           if not existing or _run_sort_key(run) > _run_sort_key(existing):

  @@ -668,6 +668,48 @@ class FirebaseSync:
  logger.debug(f"Failed to fetch user runs: {e}")
  return {}

* def fetch_all_users_raw(self) -> dict:
*        """
*        Fetch ALL users and their runs.
*
*        Used for global stats update (scanning everyone's runs for PR status changes).
*        """
*        if not is_firebase_available():
*            return {}
*
*        try:
*            settings = get_settings()
*
*            if settings.firebase.is_admin_mode():
*                db = get_firebase_db()
*                ref = db.reference("users")
*                data = ref.get()
*                return data if isinstance(data, dict) else {}
*
*            # User Mode: REST
*            import requests
*
*            # We need an identity to read, even if rules are public,
*            # but usually 'users' is readable by auth users.
*            identity = _get_user_mode_identity()
*            token = identity[1] if identity else None
*
*            url = f"{settings.firebase.database_url}/users.json"
*            if token:
*                url += f"?auth={token}"
*
*            resp = requests.get(url, timeout=15)
*            if resp.ok:
*                data = resp.json()
*                return data if isinstance(data, dict) else {}
*            else:
*                logger.debug(f"Global REST fetch failed: {resp.status_code}")
*                return {}
*
*        except Exception as e:
*            logger.debug(f"Failed to fetch all users: {e}")
*            return {}
*      def update_run(self, user_id: str | None, run_key: str, updates: dict) -> bool:
           """
           Update specific fields of a run.
  @@ -732,6 +774,8 @@ class FirebaseSync:
  logger.debug(f"Failed to update run: {e}")
  return False
* +def get_firebase_app() -> App | None:
  """
  Get the initialized Firebase app instance.

diff --git a/sbm/utils/tracker.py b/sbm/utils/tracker.py
index f1ddf01..3cb68c2 100644
--- a/sbm/utils/tracker.py
+++ b/sbm/utils/tracker.py
@@ -809,6 +809,8 @@ def get_global_reporting_data() -> tuple[list[dict], dict[str, set]]:
for \_run_id, run in runs.items():
if run.get("status") == "invalid":
continue

-                if run.get("slug") == "verification-ping":
-                    continue
                 run_author = _get_run_author(run)
                 run["_user"] = run_author
                 all_runs.append(run)
