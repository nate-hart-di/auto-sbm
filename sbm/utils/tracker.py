"""
Simple migration tracking for SBM.

Persists a list of migrated slugs in the user's home directory to avoid
double-counting reruns. Provides helpers to record completions and read stats.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from .processes import run_background_task
from .firebase_sync import is_firebase_available, FirebaseSync

from .logger import logger

# Local tracker file (legacy/individual)
TRACKER_FILE = Path.home() / ".sbm_migrations.json"

# Repository root for reference
REPO_ROOT = Path(__file__).parent.parent.parent.resolve()


def _get_user_id() -> str:
    """Generate a unique ID for the user based on GitHub username, git config, or hostname."""
    # 1. Try to get GitHub username (most preferred)
    try:
        result = subprocess.run(
            ["gh", "api", "user", "-q", ".login"],
            capture_output=True,
            text=True,
            check=False,
        )
        username = result.stdout.strip()
        if username:
            return username
    except Exception as e:
        logger.debug(f"Could not get GitHub username via gh cli: {e}")

    # 2. Try to get git email (fallback)
    try:
        result = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(REPO_ROOT),
        )
        email = result.stdout.strip()
        if email:
            return email.replace("@", "_").replace(".", "_")
    except Exception as e:
        logger.debug(f"Could not get git email: {e}")

    # 3. Fallback to hostname + username
    try:
        return f"{socket.gethostname()}_{os.getlogin()}"
    except Exception:
        return "unknown_user"


def _read_tracker() -> dict:
    """Read tracker data from disk, returning a default structure on failure."""
    if not TRACKER_FILE.exists():
        return {"migrations": [], "runs": [], "last_updated": None}

    try:
        with TRACKER_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            migrations = data.get("migrations", [])
            runs = data.get("runs", [])
            if not isinstance(migrations, list):
                migrations = []
            if not isinstance(runs, list):
                runs = []
            return {
                "migrations": migrations,
                "runs": runs,
                "last_updated": data.get("last_updated"),
            }
    except Exception as e:
        logger.warning(f"Could not read migration tracker; resetting. Error: {e}")
        return {"migrations": [], "runs": [], "last_updated": None}


def _write_tracker(data: dict) -> None:
    """Persist tracker data to local disk only (offline queue cache)."""
    # Write to local home directory
    try:
        temp_path = TRACKER_FILE.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        temp_path.replace(TRACKER_FILE)
    except Exception as e:
        logger.warning(f"Failed to write local migration tracker to {TRACKER_FILE}: {e}")


def record_migration(slug: str) -> tuple[bool, int]:
    """
    Record a completed migration. Returns (added, total_count).

    Args:
        slug: Dealer theme slug that completed migration
    """
    slug = (slug or "").strip()
    if not slug:
        return False, 0

    data = _read_tracker()
    migrations = set(data.get("migrations", []))

    added = slug not in migrations
    migrations.add(slug)

    data["migrations"] = sorted(migrations)
    data["last_updated"] = datetime.now(timezone.utc).isoformat() + "Z"

    _write_tracker(data)
    return added, len(migrations)


def record_run(
    slug: str,
    command: str,
    status: str,
    duration: float,
    automation_time: float,
    lines_migrated: int = 0,
    files_created_count: int = 0,
    scss_line_count: int = 0,
    manual_estimate_minutes: int = 240,
    report_path: str | None = None,
) -> None:
    """
    Record a detailed migration run.

    Args:
        slug: Dealer theme slug
        command: SBM command executed (e.g., 'auto', 'migrate')
        status: Result status ('success', 'failed', 'interrupted')
        duration: Total wall-clock duration in seconds
        automation_time: Time spent in automation in seconds
        lines_migrated: Number of lines in generated Site Builder files
        files_created_count: Number of Site Builder files created
        scss_line_count: Total lines in source SCSS files
        manual_estimate_minutes: Estimated manual effort in minutes (default 4 hours)
        report_path: Path to generated markdown report (optional)
    """
    data = _read_tracker()
    runs = data.get("runs", [])

    run_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "slug": slug,
        "command": command,
        "status": status,
        "duration_seconds": round(duration, 2),
        "automation_seconds": round(automation_time, 2),
        "lines_migrated": lines_migrated,
        "files_created_count": files_created_count,
        "scss_line_count": scss_line_count,
        "manual_estimate_seconds": manual_estimate_minutes * 60,
        "report_path": report_path,
        "sync_status": "pending_sync",  # Default to pending
    }

    # Keep only the last 500 runs to prevent file bloat
    runs.append(run_entry)
    data["runs"] = runs[-500:]
    data["last_updated"] = run_entry["timestamp"]

    _write_tracker(data)

    # Trigger silent background stats refresh if this was a successful run
    if status == "success":
        # Try immediate sync if online
        if _sync_to_firebase(run_entry):
            # If successful, mark as synced immediately to prevent background process from sending duplicate
            run_entry["sync_status"] = "synced"
            # Update the latest entry in the list and save
            runs[-1] = run_entry
            data["runs"] = runs
            _write_tracker(data)

        # Always trigger background update to handle any other pending items
        trigger_background_stats_update()


def filter_runs(
    runs: list[dict],
    limit: int | None = None,
    since: str | None = None,
    until: str | None = None,
    user: str | None = None,
) -> list[dict]:
    """
    Filter migration runs based on provided criteria.

    Args:
        runs: List of run dictionaries from tracker
        limit: Maximum number of runs to return (most recent)
        since: ISO date string (YYYY-MM-DD) - include runs from this date onwards
        until: ISO date string (YYYY-MM-DD) - include runs up to this date
        user: User ID to filter by

    Returns:
        Filtered list of runs
    """
    filtered = runs.copy()

    # Parse since date
    since_date = None
    if since:
        try:
            since_date = datetime.fromisoformat(since).replace(tzinfo=timezone.utc)
        except ValueError:
            logger.warning(f"Invalid 'since' date format: {since}. Use YYYY-MM-DD.")

    # Parse until date (end of day)
    until_date = None
    if until:
        try:
            until_date = datetime.fromisoformat(until).replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
        except ValueError:
            logger.warning(f"Invalid 'until' date format: {until}. Use YYYY-MM-DD.")

    # Apply date filtering
    if since_date or until_date:
        date_filtered = []
        for run in filtered:
            timestamp_str = run.get("timestamp", "")
            if not timestamp_str:
                continue
            try:
                # Parse ISO8601 timestamp with Z suffix
                run_ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                if since_date and run_ts < since_date:
                    continue
                if until_date and run_ts > until_date:
                    continue
                date_filtered.append(run)
            except ValueError:
                # Skip runs with unparseable timestamps
                continue
        filtered = date_filtered

    # Apply user filtering
    if user:
        user_lower = user.lower()
        user_filtered = []
        for run in filtered:
            run_user = run.get("_user") or run.get("user_id", "")
            if run_user and user_lower in run_user.lower():
                user_filtered.append(run)
        filtered = user_filtered

    # Sort by timestamp (most recent first) before applying limit
    def get_timestamp(run: dict) -> str:
        return run.get("timestamp", "")

    filtered.sort(key=get_timestamp, reverse=True)

    # Apply limit (take first N after sorting)
    if limit is not None and limit > 0:
        filtered = filtered[:limit]

    return filtered


def get_migration_stats(
    limit: int | None = None,
    since: str | None = None,
    until: str | None = None,
    user: str | None = None,
    team: bool = False,
) -> dict:
    """Return tracker stats with local and global aggregated metrics.

    Args:
        limit: Optional limit on number of runs to return
        since: Optional ISO date string (YYYY-MM-DD) - filter runs from this date onwards
        until: Optional ISO date string (YYYY-MM-DD) - filter runs up to this date
        user: Optional user ID to filter by
        team: If True, attempt to fetch aggregated stats from Firebase

    Returns:
        Dictionary with migration stats, optionally filtered
    """
    # If team stats requested, try to get them from Firebase first
    if team:
        team_stats = fetch_team_stats()
        if team_stats:
            # If successful, return these (wrapped to match expected structure if needed,
            # or just as 'global_metrics' override)

            # For the CLI, if --team is passed, it likely wants the global view.
            # We'll attach it to a standard response structure
            return {
                "team_stats": team_stats,
                "source": "firebase",
                # Include local data for context
                "user_id": _get_user_id(),
            }

    # Standard Flow: Personal stats from Firebase (or offline message)
    # Note: Local JSON is only for offline queue, not for stats display

    # Try to get all runs from Firebase
    all_firebase_runs, user_migrations = get_global_reporting_data()
    if not all_firebase_runs and not is_firebase_available():
        return {
            "error": "Stats unavailable (offline mode)",
            "message": "Firebase connection required for stats. Local tracking continues offline.",
            "user_id": _get_user_id(),
        }

    # Extract personal stats from Firebase data
    current_user_id = _get_user_id()

    # Filter to current user's runs from Firebase
    my_runs = [r for r in all_firebase_runs if r.get("_user") == current_user_id]
    my_migrations = user_migrations.get(current_user_id, set())

    # Apply additional filters if provided
    has_filters = any([limit, since, until, user])
    if has_filters:
        # If user filter is specified, filter all runs not just current user's
        runs_to_filter = all_firebase_runs if user else my_runs
        filtered_runs = filter_runs(
            runs_to_filter, limit=limit, since=since, until=until, user=user
        )
    else:
        filtered_runs = my_runs

    # Calculate metrics from Firebase data (not local)
    firebase_stats = _calculate_metrics({"runs": my_runs})

    return {
        "count": len(my_migrations),
        "migrations": sorted(my_migrations),
        "runs": filtered_runs,  # Return filtered runs from Firebase
        "metrics": firebase_stats,
        "last_updated": max((r.get("timestamp", "") for r in my_runs), default=None),
        "path": str(TRACKER_FILE),  # Keep for compatibility
        "user_id": current_user_id,
        "source": "firebase",
    }


def get_global_reporting_data() -> tuple[list[dict], dict[str, set]]:
    """
    Return all runs and user migrations from Firebase.

    Replaces git-based stats aggregation with Firebase query.
    Returns empty data if Firebase unavailable (offline mode).
    """
    all_runs: list[dict] = []
    user_migrations: dict[str, set] = {}

    # Try to fetch from Firebase
    if not is_firebase_available():
        logger.debug("Firebase unavailable - returning empty reporting data")
        return all_runs, user_migrations

    try:
        from .firebase_sync import FirebaseSync

        sync = FirebaseSync()

        # Get Firebase database reference
        from firebase_admin import db

        users_ref = db.reference("/users")
        users_data = users_ref.get()

        if not users_data:
            return all_runs, user_migrations

        # Process all users' data from Firebase
        for user_id, user_data in users_data.items():
            runs = user_data.get("runs", {})
            migrations_set = set()

            for run_id, run in runs.items():
                run["_user"] = user_id
                all_runs.append(run)

                # Track unique migrations per user
                slug = run.get("slug")
                if slug and run.get("status") == "success":
                    migrations_set.add(slug)

            user_migrations[user_id] = migrations_set

        return all_runs, user_migrations

    except Exception as e:
        logger.debug(f"Error fetching global reporting data from Firebase: {e}")
        return all_runs, user_migrations


def _calculate_metrics(data: dict) -> dict:
    """Helper to calculate metrics from tracker data structure."""
    runs = data.get("runs", [])
    total_runs = len(runs)
    successful_runs = [r for r in runs if r.get("status") == "success"]
    success_count = len(successful_runs)

    # Calculate time saved
    total_automation_seconds = sum(r.get("automation_seconds", 0) for r in successful_runs)
    total_lines_migrated = sum(r.get("lines_migrated", 0) for r in successful_runs)

    # Mathematical time saved: 1 hour per 800 lines migrated
    time_saved_hours = total_lines_migrated / 800.0

    return {
        "total_runs": total_runs,
        "success_count": success_count,
        "total_lines_migrated": total_lines_migrated,
        "total_automation_time_h": round(total_automation_seconds / 3600, 2),
        "total_time_saved_h": round(time_saved_hours, 1),
    }


# Git-based stats system removed in Story 2.7
# Firebase is now the single source of truth for team stats


def trigger_background_stats_update() -> None:
    """
    Trigger a silent background refresh of statistics.
    Uses the sbm cli to run the backfill script and sync global stats.
    """
    try:
        # Trigger command in background
        # Trigger internal refresh stats command
        # This command is responsible for calling process_pending_syncs among other things
        # We need to make sure sbm.cli exposes a command that calls process_pending_syncs
        # For now, let's assume 'internal-refresh-stats' does or will do that.
        run_background_task([os.sys.executable, "-m", "sbm.cli", "internal-refresh-stats"])

    except Exception as e:
        logger.debug(f"Failed to trigger background stats update: {e}")


def _sync_to_firebase(run_entry: dict) -> bool:
    """delegate to FirebaseSync class."""
    if not is_firebase_available():
        return False

    try:
        sync = FirebaseSync()
        return sync.push_run(_get_user_id(), run_entry)
    except Exception as e:
        logger.debug(f"Firebase sync unavailable: {e}")
        return False


def process_pending_syncs() -> None:
    """
    Check for runs with 'pending_sync' status and attempt to upload them.
    Updates the local tracker file with new statuses.
    """
    data = _read_tracker()
    runs = data.get("runs", [])
    updated = False

    # Check for pending items
    for run in runs:
        # Check if it's a success run that hasn't been synced (or marked as failed/pending)
        # We primarily care about runs where status='success' and sync_status != 'synced'
        if run.get("status") == "success":
            sync_status = run.get("sync_status", "pending_sync")  # Default to pending if missing

            if sync_status != "synced":
                # Attempt sync
                success = _sync_to_firebase(run)
                if success:
                    run["sync_status"] = "synced"
                    updated = True
                else:
                    # If it failed, ensure it is marked as pending/failed (keep as pending for retry)
                    if sync_status != "pending_sync":
                        run["sync_status"] = "pending_sync"
                        updated = True

    if updated:
        _write_tracker(data)


def fetch_team_stats() -> dict | None:
    """Fetch aggregated team statistics from Firebase (delegated)."""
    if not is_firebase_available():
        return None
    try:
        sync = FirebaseSync()
        return sync.fetch_team_stats()
    except Exception:
        return None


def get_all_migrated_slugs() -> dict[str, str]:
    """Fetch migrated slugs mapping (delegated)."""
    if not is_firebase_available():
        return {}
    try:
        sync = FirebaseSync()
        return sync.get_all_migrated_slugs()
    except Exception:
        return {}
