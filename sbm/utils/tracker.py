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
import fcntl
from datetime import datetime, timezone
from pathlib import Path
from .processes import run_background_task

from .logger import logger

# Local tracker file (legacy/individual)
TRACKER_FILE = Path.home() / ".sbm_migrations.json"

# Global stats directory in the repo
REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
GLOBAL_STATS_DIR = REPO_ROOT / "stats"


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
    """Persist tracker data to disk and global stats directory."""
    # Write to local home directory
    try:
        with TRACKER_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to write local migration tracker to {TRACKER_FILE}: {e}")

    # Write to global stats directory in repo
    try:
        if not GLOBAL_STATS_DIR.exists():
            GLOBAL_STATS_DIR.mkdir(parents=True, exist_ok=True)

        user_id = _get_user_id()
        global_file = GLOBAL_STATS_DIR / f"{user_id}.json"

        # Only include essentials for global tracking to save space/bandwidth
        global_data = {
            "user": user_id,
            "migrations": data.get("migrations", []),
            "runs": data.get("runs", [])[-100:],  # Only keep last 100 runs globally
            "last_updated": data.get("last_updated"),
        }

        with global_file.open("w", encoding="utf-8") as f:
            json.dump(global_data, f, indent=2)

    except Exception as e:
        logger.debug(f"Failed to write global stats file: {e}")


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
    manual_estimate_minutes: int = 240,
) -> None:
    """
    Record a detailed migration run.

    Args:
        slug: Dealer theme slug
        command: SBM command executed (e.g., 'auto', 'migrate')
        status: Result status ('success', 'failed', 'interrupted')
        duration: Total wall-clock duration in seconds
        automation_time: Time spent in automation in seconds
        manual_estimate_minutes: Estimated manual effort in minutes (default 4 hours)
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
        "manual_estimate_seconds": manual_estimate_minutes * 60,
    }

    # Keep only the last 500 runs to prevent file bloat
    runs.append(run_entry)
    data["runs"] = runs[-500:]
    data["last_updated"] = run_entry["timestamp"]

    _write_tracker(data)

    # Trigger silent background stats refresh if this was a successful run
    if status == "success":
        trigger_background_stats_update()


def get_migration_stats() -> dict:
    """Return tracker stats with local and global aggregated metrics."""
    local_data = _read_tracker()

    # Calculate local metrics
    local_stats = _calculate_metrics(local_data)

    # Calculate global metrics from all users
    global_stats = _aggregate_global_stats()

    return {
        "count": len(local_data.get("migrations", [])),
        "migrations": local_data.get("migrations", []),
        "runs": local_data.get("runs", []),
        "metrics": local_stats,
        "global_metrics": global_stats,
        "last_updated": local_data.get("last_updated"),
        "path": str(TRACKER_FILE),
        "user_id": _get_user_id(),
    }


def get_global_reporting_data() -> tuple[list[dict], dict[str, set]]:
    """
    Return all runs and user migrations using the same data sources as CLI stats.

    Includes the current user's full local tracker data plus global stats files
    for other users (which may contain truncated run history).
    """
    local_data = _read_tracker()
    current_user_id = _get_user_id()

    all_runs: list[dict] = []
    user_migrations: dict[str, set] = {}

    local_migrations = set(local_data.get("migrations", []))
    user_migrations[current_user_id] = local_migrations
    for run in local_data.get("runs", []):
        run["_user"] = current_user_id
        all_runs.append(run)

    if not GLOBAL_STATS_DIR.exists():
        return all_runs, user_migrations

    for stats_file in GLOBAL_STATS_DIR.glob("*.json"):
        if stats_file.name.startswith("."):
            continue

        user_id = stats_file.stem
        if user_id == current_user_id:
            continue

        try:
            with stats_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                migrations = set(data.get("migrations", []))
                user_migrations[user_id] = migrations

                runs = data.get("runs", [])
                for run in runs:
                    run["_user"] = user_id
                    all_runs.append(run)
        except Exception as e:
            logger.debug(f"Error processing global stats file {stats_file}: {e}")
            continue

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


def _aggregate_global_stats() -> dict:
    """Aggregate stats from all users in the stats/ directory."""
    if not GLOBAL_STATS_DIR.exists():
        return {}

    local_data = _read_tracker()
    local_runs = local_data.get("runs", [])
    local_migrations = set(local_data.get("migrations", []))
    current_user_id = _get_user_id()

    all_migrations = set(local_migrations)
    total_runs = len(local_runs)
    total_success = 0
    total_automation_seconds = 0.0
    total_lines_migrated = 0
    user_count = 1  # Start with the current user

    # Process local successes
    for run in local_runs:
        if run.get("status") == "success":
            total_success += 1
            total_automation_seconds += run.get("automation_seconds", 0)
            total_lines_migrated += run.get("lines_migrated", 0)

    user_counts = {current_user_id: len(local_migrations)}

    for stats_file in GLOBAL_STATS_DIR.glob("*.json"):
        if stats_file.name.startswith("."):
            continue

        user_id = stats_file.stem
        if user_id == current_user_id:
            continue  # Already processed local live data

        try:
            with stats_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                user_count += 1

                user_migrations = data.get("migrations", [])
                user_counts[user_id] = len(user_migrations)

                # Combined unique migrations
                all_migrations.update(user_migrations)

                # Sum metrics
                runs = data.get("runs", [])
                total_runs += len(runs)

                for run in runs:
                    if run.get("status") == "success":
                        total_success += 1
                        total_automation_seconds += run.get("automation_seconds", 0)
                        total_lines_migrated += run.get("lines_migrated", 0)
        except Exception as e:
            logger.debug(f"Error processing global stats file {stats_file}: {e}")
            continue

    # Mathematical time saved: 1 hour per 800 lines migrated
    time_saved_hours = total_lines_migrated / 800.0

    # Top contributors (top 3)
    top_contributors = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:3]

    return {
        "total_users": user_count,
        "total_migrations": len(all_migrations),
        "total_runs": total_runs,
        "total_success": total_success,
        "total_lines_migrated": total_lines_migrated,
        "total_time_saved_h": round(time_saved_hours, 1),
        "total_automation_time_h": round(total_automation_seconds / 3600, 2),
        "top_contributors": top_contributors,
    }


def sync_global_stats() -> None:
    """Background sync: Commit and push the current user's stats file with file locking."""
    lock_file = GLOBAL_STATS_DIR / ".sync.lock"

    try:
        # Create lock file if it doesn't exist
        lock_file.touch(exist_ok=True)

        with lock_file.open("w") as lock_f:
            try:
                # Exclusive non-blocking lock
                fcntl.flock(lock_f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError:
                # Another process is syncing, skip
                return

            try:
                user_id = _get_user_id()
                stats_file = GLOBAL_STATS_DIR / f"{user_id}.json"

                if not stats_file.exists():
                    return

                # Check if we have uncommitted changes in the stats file
                rel_path = f"stats/{user_id}.json"

                # Add the file
                subprocess.run(
                    ["git", "add", rel_path], check=False, cwd=str(REPO_ROOT), capture_output=True
                )

                # Check commit status
                status_check = subprocess.run(
                    ["git", "status", "--porcelain", rel_path],
                    capture_output=True,
                    text=True,
                    check=False,
                    cwd=str(REPO_ROOT),
                )

                if not status_check.stdout.strip():
                    return  # No changes

                # Commit (Removed --no-verify for security)
                subprocess.run(
                    ["git", "commit", "-m", f"docs: update global stats for {user_id}"],
                    check=False,
                    cwd=str(REPO_ROOT),
                    capture_output=True,
                )

                # Push (Removed --no-verify for security)
                subprocess.run(
                    ["git", "push", "origin", "HEAD"],
                    check=False,
                    cwd=str(REPO_ROOT),
                    capture_output=True,
                    timeout=15,
                )
            finally:
                # Always release lock
                fcntl.flock(lock_f, fcntl.LOCK_UN)

    except Exception as e:
        logger.debug(f"Global stats sync failed: {e}")


def trigger_background_stats_update() -> None:
    """
    Trigger a silent background refresh of statistics.
    Uses the sbm cli to run the backfill script and sync global stats.
    """
    try:
        # Trigger command in background
        run_background_task([os.sys.executable, "-m", "sbm.cli", "internal-refresh-stats"])

    except Exception as e:
        logger.debug(f"Failed to trigger background stats update: {e}")
