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

from .logger import logger

# Local tracker file (legacy/individual)
TRACKER_FILE = Path.home() / ".sbm_migrations.json"

# Global stats directory in the repo
REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
GLOBAL_STATS_DIR = REPO_ROOT / "stats"


def _get_user_id() -> str:
    """Generate a unique ID for the current user based on git config or hostname."""
    try:
        # Try to get git email
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
    except Exception:
        pass

    # Fallback to hostname + username
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
        "manual_estimate_seconds": manual_estimate_minutes * 60,
    }

    # Keep only the last 500 runs to prevent file bloat
    runs.append(run_entry)
    data["runs"] = runs[-500:]
    data["last_updated"] = run_entry["timestamp"]

    _write_tracker(data)


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
        "user_id": _get_user_id()
    }


def _calculate_metrics(data: dict) -> dict:
    """Helper to calculate metrics from tracker data structure."""
    runs = data.get("runs", [])
    total_runs = len(runs)
    successful_runs = [r for r in runs if r.get("status") == "success"]
    success_count = len(successful_runs)

    # Calculate time saved
    total_automation_seconds = sum(r.get("automation_seconds", 0) for r in successful_runs)
    total_manual_estimated_seconds = sum(r.get("manual_estimate_seconds", 0) for r in successful_runs)
    time_saved_seconds = max(0, total_manual_estimated_seconds - total_automation_seconds)

    # Calculate averages
    avg_duration = 0.0
    if success_count > 0:
        avg_duration = total_automation_seconds / success_count

    return {
        "total_runs": total_runs,
        "success_count": success_count,
        "success_rate": (success_count / total_runs * 100) if total_runs > 0 else 0,
        "total_automation_time_h": round(total_automation_seconds / 3600, 2),
        "total_time_saved_h": round(time_saved_seconds / 3600, 1),
        "avg_automation_time_m": round(avg_duration / 60, 1),
    }


def _aggregate_global_stats() -> dict:
    """Aggregate stats from all users in the stats/ directory."""
    if not GLOBAL_STATS_DIR.exists():
        return {}

    all_migrations = set()
    total_runs = 0
    total_success = 0
    total_automation_seconds = 0.0
    total_manual_seconds = 0.0
    user_count = 0

    for stats_file in GLOBAL_STATS_DIR.glob("*.json"):
        try:
            with stats_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                user_count += 1

                # Combined unique migrations
                all_migrations.update(data.get("migrations", []))

                # Sum metrics
                runs = data.get("runs", [])
                total_runs += len(runs)

                for run in runs:
                    if run.get("status") == "success":
                        total_success += 1
                        total_automation_seconds += run.get("automation_seconds", 0)
                        total_manual_seconds += run.get("manual_estimate_seconds", 0)
        except Exception:
            continue

    time_saved_seconds = max(0, total_manual_seconds - total_automation_seconds)

    return {
        "total_users": user_count,
        "total_migrations": len(all_migrations),
        "total_runs": total_runs,
        "success_rate": (total_success / total_runs * 100) if total_runs > 0 else 0,
        "total_time_saved_h": round(time_saved_seconds / 3600, 1),
        "total_automation_time_h": round(total_automation_seconds / 3600, 2),
    }


def sync_global_stats() -> None:
    """Background sync: Commit and push the current user's stats file."""
    try:
        user_id = _get_user_id()
        stats_file = GLOBAL_STATS_DIR / f"{user_id}.json"

        if not stats_file.exists():
            return

        # Check if we have uncommitted changes in the stats file
        rel_path = f"stats/{user_id}.json"

        # Add the file
        subprocess.run(
            ["git", "add", rel_path],
            check=False,
            cwd=str(REPO_ROOT),
            capture_output=True
        )

        # Check if there's anything to commit
        status = subprocess.run(
            ["git", "status", "--porcelain", rel_path],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(REPO_ROOT)
        )

        if not status.stdout.strip():
            return  # No changes

        # Commit
        subprocess.run(
            ["git", "commit", "-m", f"docs: update global stats for {user_id}", "--no-verify"],
            check=False,
            cwd=str(REPO_ROOT),
            capture_output=True
        )

        # Push in background (non-blocking if possible, but we'll just run it)
        # sbm cli logic already does pulls, so we just need to push
        subprocess.run(
            ["git", "push", "origin", "HEAD", "--no-verify"],
            check=False,
            cwd=str(REPO_ROOT),
            capture_output=True,
            timeout=10
        )

    except Exception as e:
        logger.debug(f"Global stats sync failed: {e}")
