"""
Simple migration tracking for SBM.

Persists a list of migrated slugs in the user's home directory to avoid
double-counting reruns. Provides helpers to record completions and read stats.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sbm.config import get_settings

from .constants import (
    COMPLETION_CLOSED,
    COMPLETION_COMPLETE,
    COMPLETION_IN_REVIEW,
    COMPLETION_SUPERSEDED,
    COMPLETION_UNKNOWN,
    PR_STATE_CLOSED,
    PR_STATE_MERGED,
    PR_STATE_OPEN,
    RUN_STATUS_SUCCESS,
)
from .firebase_sync import FirebaseSync, get_user_mode_identity, is_firebase_available
from .logger import logger
from .processes import run_background_task
from .run_helpers import is_complete_run
from .slug_validation import is_official_slug

# Local tracker file (legacy/individual)
TRACKER_FILE = Path.home() / ".sbm_migrations.json"

# Repository root for reference
REPO_ROOT = Path(__file__).parent.parent.parent.resolve()


class SyncStatus:
    PENDING = "pending_sync"
    SYNCED = "synced"
    MISSING_GITHUB_AUTH = "missing_github_auth"
    AUTHOR_MISMATCH = "author_mismatch"
    INVALID_SLUG = "invalid_slug"
    VALIDATION_UNAVAILABLE = "validation_unavailable"
    SKIPPED_EMPTY = "skipped_empty"


def _get_github_login() -> str | None:
    """Return the authenticated GitHub username, if available."""
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
        logger.debug(f"Could not get GitHub username via GitHub CLI: {e}")
    return None


def _get_user_id() -> str:
    """Generate a unique ID for the user based on GitHub username, git config, or hostname."""
    github_login = _get_github_login()
    if github_login:
        return github_login

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


def _get_reporting_user_id() -> str:
    """Return a stable identifier for Firebase reporting in user mode."""
    github_login = _get_github_login()
    if github_login:
        return github_login
    return _get_user_id()


def _get_run_author(run: dict) -> str:
    """Canonical author attribution for runs."""
    return run.get("pr_author") or run.get("user_id") or run.get("_user") or "unknown"


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
    pr_url: str | None = None,
    pr_author: str | None = None,
    pr_state: str | None = None,
    created_at: str | None = None,
    merged_at: str | None = None,
    closed_at: str | None = None,
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
        pr_url: GitHub Pull Request URL (optional)
        pr_author: PR author username from GitHub (optional)
        pr_state: PR state (OPEN, MERGED, CLOSED) (optional)
        created_at: PR creation timestamp from GitHub (optional)
        merged_at: PR merge timestamp from GitHub (optional)
        closed_at: PR close timestamp from GitHub (optional)
    """
    data = _read_tracker()
    runs = data.get("runs", [])

    github_login = _get_github_login()
    if github_login and pr_author and pr_author != github_login:
        logger.warning(
            "PR author mismatch. Expected authenticated GitHub user "
            f"'{github_login}', got '{pr_author}'."
        )
    if not github_login:
        logger.warning(
            "GitHub CLI not authenticated; user_id/pr_author will be missing until `gh auth login`."
        )

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
        "pr_url": pr_url,
        "user_id": github_login,
        "pr_author": pr_author or github_login,
        "pr_state": pr_state,
        "created_at": created_at,
        "merged_at": merged_at,
        "closed_at": closed_at,
        "sync_status": SyncStatus.PENDING,  # Default to pending
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
            # If successful, mark as synced immediately to prevent background
            # process from sending duplicate
            run_entry["sync_status"] = SyncStatus.SYNCED
        # Update the latest entry in the list and save, including validation status updates
        runs[-1] = run_entry
        data["runs"] = runs
        _write_tracker(data)

        # Always trigger background update to handle any other pending items
        trigger_background_stats_update()


def _parse_period_to_days(period: str) -> int | None:
    """Convert period string (day/week/month/N) to number of days.

    Args:
        period: Period string like "day", "week", "month", "7", "30"

    Returns:
        Number of days, or None if not a valid period string
    """
    if not period:
        return None

    period_lower = period.lower().strip()

    # Named periods
    if period_lower in {"day", "daily", "1"}:
        return 1
    if period_lower in {"week", "weekly", "7"}:
        return 7
    if period_lower in {"month", "monthly", "30"}:
        return 30
    if period_lower == "all":
        return None  # No filtering

    # Try numeric days
    try:
        # Purely numeric or semantic: "14", "14d", "14 days"
        # Avoid matching "2024-01-15" (ISO date)
        if re.match(r"^\d+$", period_lower):
            days = int(period_lower)
            return days if days > 0 else None

        semantic_match = re.match(r"^(\d+)\s*(d|day|days)$", period_lower)
        if semantic_match:
            days = int(semantic_match.group(1))
            return days if days > 0 else None
    except ValueError:
        pass

    return None


def _parse_date_input(input_str: str) -> tuple[datetime, datetime] | None:
    """
    Parse a flexible date/range string into a (start_dt, end_dt) tuple.
    All dates are treated as UTC for filtering consistency.

    Formats supported:
    - MM/DD/YY or M/D/YY (Specific day)
    - MM/YY or M/YY (Specific month)
    - date to date (Range)
    - N date (N days starting from date)

    Args:
        input_str: The user-provided date/range string

    Returns:
        tuple of (start_dt, end_dt) or None if unparseable
    """
    if not input_str:
        return None

    s = input_str.lower().strip()

    # 1. Handle "date to date" ranges
    if " to " in s:
        parts = s.split(" to ")
        if len(parts) == 2:
            start_range = _parse_date_input(parts[0])
            end_range = _parse_date_input(parts[1])
            if start_range and end_range:
                # Return start of first and end of second
                return start_range[0], end_range[1]

    # 2. Handle "N date" (e.g., "14 1/1/26")
    duration_match = re.match(r"^(\d+)\s+(.*)$", s)
    if duration_match:
        try:
            days = int(duration_match.group(1))
            date_part = duration_match.group(2)
            base_range = _parse_date_input(date_part)
            if base_range:
                # Start at the specified date, duration extends N days
                start_dt = base_range[0]
                end_dt = start_dt + timedelta(days=days)
                return start_dt, end_dt
        except ValueError:
            pass

    # 3. Handle specific dates: MM/DD/YY, M/D/YY, MM/YY, M/YY
    # Avoid matching ISO dates (YYYY-MM-DD) by ensuring month is 1-2 digits and we're at start
    # format: MM/DD/YY(YY) or MM/YY(YY)
    date_match = re.search(r"\b(\d{1,2})/(?:(\d{1,2})/)?(\d{2,4})\b", s)
    if date_match:
        month = int(date_match.group(1))
        day_raw = date_match.group(2)
        year_raw = date_match.group(3)

        # Handle 2-digit years
        year = int(year_raw)
        if len(year_raw) == 2:
            year += 2000

        if day_raw:
            # Specific day: MM/DD/YY
            day = int(day_raw)
            try:
                start_dt = datetime(year, month, day, tzinfo=timezone.utc)
                end_dt = start_dt + timedelta(days=1)
                return start_dt, end_dt
            except ValueError:
                return None
        else:
            # Specific month: MM/YY
            try:
                start_dt = datetime(year, month, 1, tzinfo=timezone.utc)
                # Calculate end of month
                if month == 12:
                    end_dt = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
                else:
                    end_dt = datetime(year, month + 1, 1, tzinfo=timezone.utc)
                return start_dt, end_dt
            except ValueError:
                return None

    return None


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
        since: Period string ("day", "week", "month", "7") OR ISO date (YYYY-MM-DD).
               Period strings filter runs from the last N days.
        until: ISO date string (YYYY-MM-DD) - include runs up to this date
        user: User ID to filter by (case-insensitive partial match)

    Returns:
        Filtered list of runs, sorted by date (most recent first)

    Note:
        Date filtering uses PR state-aware timestamps:
        merged_at for complete, created_at for in_review, closed_at for closed,
        and timestamp as fallback.
    """
    filtered = runs.copy()

    def get_effective_date(run: dict) -> str:
        """Get best date for filtering based on PR completion state."""
        completion_state = get_pr_completion_state(run)
        if completion_state == COMPLETION_COMPLETE:
            return run.get("merged_at") or run.get("timestamp") or ""
        if completion_state == COMPLETION_IN_REVIEW:
            return run.get("created_at") or run.get("timestamp") or ""
        if completion_state == COMPLETION_CLOSED:
            return run.get("closed_at") or run.get("timestamp") or ""
        if completion_state == COMPLETION_SUPERSEDED:
            return run.get("superseded_at") or run.get("merged_at") or run.get("timestamp") or ""
        return run.get("merged_at") or run.get("timestamp") or ""

    # Apply date filtering using effective date
    since_date = None
    until_date = None

    if since:
        # 1. Try new flexible formats (MM/DD/YY, ranges, etc.)
        range_data = _parse_date_input(since)
        if range_data:
            since_date, until_date = range_data
        else:
            # 2. Try semantic periods (day, week, etc.)
            days = _parse_period_to_days(since)
            if days is not None:
                since_date = datetime.now(timezone.utc) - timedelta(days=days)
            # 3. Try ISO date
            elif len(since) >= 10:
                try:
                    if len(since) == 10:
                        parsed_date = datetime.fromisoformat(since + "T00:00:00+00:00")
                    else:
                        parsed_date = datetime.fromisoformat(since.replace("Z", "+00:00"))
                    since_date = parsed_date
                except ValueError:
                    logger.warning(f"Invalid 'since' format: {since}")

    # Explicit 'until' overrides any range end from 'since'
    if until:
        try:
            if len(until) == 10:
                parsed_date = datetime.fromisoformat(until + "T23:59:59+00:00")
            else:
                parsed_date = datetime.fromisoformat(until.replace("Z", "+00:00"))
            until_date = parsed_date
        except ValueError:
            logger.warning(f"Invalid 'until' format: {until}")

    # Ensure timezone awareness
    if since_date and since_date.tzinfo is None:
        since_date = since_date.replace(tzinfo=timezone.utc)
    if until_date and until_date.tzinfo is None:
        until_date = until_date.replace(tzinfo=timezone.utc)

    if since_date or until_date:
        date_filtered = []
        for run in filtered:
            date_str = get_effective_date(run)
            if not date_str:
                continue
            try:
                ts = date_str
                if ts.endswith("+00:00Z"):
                    ts = ts[:-1]
                elif ts.endswith("Z"):
                    ts = ts[:-1] + "+00:00"

                run_ts = datetime.fromisoformat(ts)
                if run_ts.tzinfo is None:
                    run_ts = run_ts.replace(tzinfo=timezone.utc)

                if since_date and run_ts < since_date:
                    continue
                if until_date and run_ts > until_date:
                    continue
                date_filtered.append(run)
            except ValueError:
                continue
        filtered = date_filtered

    # Apply user filtering
    if user:
        user_lower = user.lower()
        user_filtered = []
        for run in filtered:
            run_user = _get_run_author(run)
            run_author = run.get("pr_author", "")
            if (run_user and user_lower in run_user.lower()) or (
                run_author and user_lower in run_author.lower()
            ):
                user_filtered.append(run)
        filtered = user_filtered

    # Sort by effective date (merged_at or timestamp, most recent first)
    filtered.sort(key=get_effective_date, reverse=True)

    # Apply limit (take first N after sorting)
    if limit is not None and limit > 0:
        filtered = filtered[:limit]

    return filtered


def _dedupe_runs_for_display(runs: list[dict]) -> list[dict]:
    """Keep only the most recent run per slug for user-facing displays."""

    def get_effective_date(run: dict) -> str:
        completion_state = get_pr_completion_state(run)
        if completion_state == COMPLETION_COMPLETE:
            return run.get("merged_at") or run.get("timestamp") or ""
        if completion_state == COMPLETION_IN_REVIEW:
            return run.get("created_at") or run.get("timestamp") or ""
        if completion_state == COMPLETION_CLOSED:
            return run.get("closed_at") or run.get("timestamp") or ""
        if completion_state == COMPLETION_SUPERSEDED:
            return run.get("superseded_at") or run.get("merged_at") or run.get("timestamp") or ""
        return run.get("merged_at") or run.get("timestamp") or ""

    def parse_date(ts: str) -> datetime:
        if ts.endswith("+00:00Z"):
            ts = ts[:-1]
        elif ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)

    best_by_slug: dict[str, dict] = {}
    extras: list[dict] = []
    for run in runs:
        slug = run.get("slug")
        if not slug:
            extras.append(run)
            continue
        existing = best_by_slug.get(slug)
        if not existing:
            best_by_slug[slug] = run
            continue
        if parse_date(get_effective_date(run)) > parse_date(get_effective_date(existing)):
            best_by_slug[slug] = run

    deduped = extras + list(best_by_slug.values())
    deduped.sort(key=get_effective_date, reverse=True)
    return deduped


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
    settings = get_settings()
    if settings.firebase.is_user_mode() and not get_user_mode_identity():
        return {
            "error": "Stats unavailable (auth required)",
            "message": "Firebase anonymous auth failed. Check FIREBASE__API_KEY.",
            "user_id": _get_user_id(),
        }

    # If team stats requested, handle filtered vs all-time separately
    if team:
        if since or user:
            all_runs, _ = get_global_reporting_data()
            team_runs = filter_runs(
                all_runs,
                limit=None,
                since=since,
                until=until,
                user=user,
            )
            complete_runs = [
                r
                for r in team_runs
                if r.get("status") == "success" and get_pr_completion_state(r) == "complete"
            ]

            def _run_effective_date(run: dict) -> datetime:
                completion_state = get_pr_completion_state(run)
                if completion_state == COMPLETION_COMPLETE:
                    ts_val = run.get("merged_at") or run.get("timestamp") or ""
                elif completion_state == COMPLETION_IN_REVIEW:
                    ts_val = run.get("created_at") or run.get("timestamp") or ""
                elif completion_state == COMPLETION_CLOSED:
                    ts_val = run.get("closed_at") or run.get("timestamp") or ""
                elif completion_state == COMPLETION_SUPERSEDED:
                    ts_val = (
                        run.get("superseded_at")
                        or run.get("merged_at")
                        or run.get("timestamp")
                        or ""
                    )
                else:
                    ts_val = run.get("merged_at") or run.get("timestamp") or ""

                if ts_val.endswith("+00:00Z"):
                    ts_val = ts_val[:-1]
                elif ts_val.endswith("Z"):
                    ts_val = ts_val[:-1] + "+00:00"

                try:
                    parsed = datetime.fromisoformat(ts_val)
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    return parsed
                except ValueError:
                    return datetime.min.replace(tzinfo=timezone.utc)

            unique_complete_by_slug: dict[str, dict] = {}
            for run in complete_runs:
                slug = run.get("slug")
                if not slug:
                    continue
                existing = unique_complete_by_slug.get(slug)
                if not existing or _run_effective_date(run) > _run_effective_date(existing):
                    unique_complete_by_slug[slug] = run

            total_lines_migrated = sum(
                r.get("lines_migrated", 0) for r in unique_complete_by_slug.values()
            )
            user_counts: dict[str, set] = {}
            for run in unique_complete_by_slug.values():
                author = _get_run_author(run)
                user_counts.setdefault(author, set()).add(run.get("slug"))

            return {
                "team_stats": {
                    "total_users": len(user_counts),
                    "total_migrations": len(unique_complete_by_slug),
                    "total_lines_migrated": total_lines_migrated,
                    "total_runs": len(unique_complete_by_slug),
                    "total_time_saved_h": round(total_lines_migrated / 800.0, 1)
                    if total_lines_migrated
                    else 0.0,
                    "top_contributors": sorted(
                        ((user_id, len(slugs)) for user_id, slugs in user_counts.items()),
                        key=lambda x: x[1],
                        reverse=True,
                    )[:3],
                    "source": "firebase",
                },
                "source": "firebase",
                "user_id": _get_user_id(),
            }

        team_stats = fetch_team_stats()
        if team_stats:
            return {
                "team_stats": team_stats,
                "source": "firebase",
                "user_id": _get_user_id(),
            }

    # Standard Flow: Personal stats from Firebase (or offline message)
    # Note: Local JSON is only for offline queue, not for stats display

    # Try to get all runs from Firebase
    all_firebase_runs, user_migrations = get_global_reporting_data()
    if not all_firebase_runs and not user_migrations and not is_firebase_available():
        return {
            "error": "Stats unavailable (offline mode)",
            "message": "Firebase connection required for stats. Local tracking continues offline.",
            "user_id": _get_user_id(),
        }

    # Extract personal stats from Firebase data
    current_user_id = _get_reporting_user_id()

    # Filter to current user's runs from Firebase
    my_runs = [r for r in all_firebase_runs if r.get("_user") == current_user_id]
    my_migrations = user_migrations.get(current_user_id, set())

    # If user filter is specified, we need to adjust the "stats subject"
    # Otherwise we show "my" stats but list "their" runs, which is confusing.
    target_user_id = current_user_id
    stats_runs = my_runs
    stats_migrations = my_migrations

    has_filters = any([limit, since, until, user])
    if has_filters:
        # If user filter is specified, filter all runs
        runs_to_filter = all_firebase_runs if user else my_runs

        if user:
            # Find the best matching user ID for stats calculation
            # Logic: exact match > partial match > first match
            user_lower = user.lower()
            candidates = [u for u in user_migrations.keys() if user_lower in u.lower()]
            if candidates:
                # Prefer exact match
                target_user_id = next(
                    (u for u in candidates if u.lower() == user_lower), candidates[0]
                )
                stats_migrations = user_migrations.get(target_user_id, set())
                stats_runs = [r for r in all_firebase_runs if r.get("_user") == target_user_id]

        filtered_runs = filter_runs(
            runs_to_filter, limit=limit, since=since, until=until, user=user
        )
        # When filters are active, calculate metrics FROM the filtered runs
        # Get all matching runs (without limit) for accurate metric calculation
        all_matching_runs = filter_runs(
            runs_to_filter, limit=None, since=since, until=until, user=user
        )
        run_metrics = _calculate_metrics({"runs": all_matching_runs})
        # Count unique slugs from filtered runs for "Sites Migrated"
        # Only count complete (merged) runs
        filtered_slugs = {
            r.get("slug")
            for r in all_matching_runs
            if r.get("slug")
            and r.get("status") == "success"
            and get_pr_completion_state(r) == "complete"
        }
        stats_migrations = filtered_slugs
    else:
        filtered_runs = my_runs
        # No filters: show all-time metrics
        run_metrics = _calculate_metrics({"runs": stats_runs})

    # Only show most recent run per slug in user-facing history
    filtered_runs = _dedupe_runs_for_display(filtered_runs)

    firebase_stats = run_metrics

    return {
        "count": len(stats_migrations),
        "migrations": sorted(stats_migrations),
        "runs": filtered_runs,  # Return filtered runs from Firebase
        "metrics": firebase_stats,
        "last_updated": max((r.get("timestamp", "") for r in stats_runs), default=None),
        "path": str(TRACKER_FILE),  # Keep for compatibility
        "user_id": target_user_id,  # Return the ID of the user whose stats we are showing
        "display_name": target_user_id,
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
        settings = get_settings()
        users_data = None

        if settings.firebase.is_admin_mode():
            # Admin mode: use firebase_admin SDK
            from firebase_admin import db

            users_ref = db.reference("/users")
            users_data = users_ref.get()
        else:
            # User mode: use REST API for read access
            import requests

            identity = get_user_mode_identity()
            if not identity:
                return all_runs, user_migrations
            _, token = identity

            url = f"{settings.firebase.database_url}/users.json?auth={token}"
            resp = requests.get(url, timeout=10)
            if resp.ok:
                users_data = resp.json()
            else:
                logger.debug(f"Firebase REST fetch failed: {resp.status_code}")
                return all_runs, user_migrations

        if not users_data:
            return all_runs, user_migrations

        # Process all users' data from Firebase
        for user_id, user_data in users_data.items():
            if not isinstance(user_data, dict):
                continue
            runs = user_data.get("runs", {})

            for _run_id, run in runs.items():
                if run.get("status") == "invalid":
                    continue
                if run.get("slug") == "verification-ping":
                    continue
                run_author = _get_run_author(run)
                run["_user"] = run_author
                all_runs.append(run)

                # Track unique migrations per user
                # Only count complete (merged) runs
                slug = run.get("slug")
                if (
                    slug
                    and run.get("status") == "success"
                    and get_pr_completion_state(run) == "complete"
                ):
                    user_migrations.setdefault(run_author, set()).add(slug)

        return all_runs, user_migrations

    except Exception as e:
        logger.debug(f"Error fetching global reporting data from Firebase: {e}")
        return all_runs, user_migrations


def get_pr_completion_state(run: dict) -> str:
    """
    Classify run completion state based on PR timestamps and state.

    Priority order:
    0. If superseded → "superseded" (run was remigrated)
    1. If merged_at exists → "complete" (PR was merged)
    2. If pr_state is OPEN → "in_review" (PR currently open, even if previously closed)
    3. If pr_state is CLOSED (with or without closed_at) → "closed"
    4. If has created_at → "in_review" (assume open if no other info)
    5. Fallback → "unknown" (no PR data available)

    Note: GitHub doesn't clear closed_at when PR is reopened, so must check pr_state.

    Args:
        run: Run dict with optional created_at, merged_at, closed_at, pr_state, superseded fields

    Returns:
        One of: "superseded", "complete", "in_review", "closed", "unknown"
    """
    # NEW: Check superseded flag first
    if run.get("superseded"):
        return COMPLETION_SUPERSEDED

    merged_at = run.get("merged_at")
    created_at = run.get("created_at")
    closed_at = run.get("closed_at")
    pr_state = run.get("pr_state", "").upper()

    if merged_at:
        return COMPLETION_COMPLETE
    if pr_state == PR_STATE_OPEN:
        # PR is currently open (even if it was previously closed and reopened)
        return COMPLETION_IN_REVIEW
    if pr_state == PR_STATE_MERGED:
        # State says merged but no merged_at timestamp (data inconsistency)
        return COMPLETION_COMPLETE
    if pr_state == PR_STATE_CLOSED:
        # PR is closed without merge (legacy data may be missing closed_at)
        return COMPLETION_CLOSED
    if created_at:
        # Has created_at but no clear state - assume in review
        return COMPLETION_IN_REVIEW
    # Backwards compatibility: runs without new fields
    # Cannot determine completion state without timestamps
    # Return "unknown" to avoid incorrectly inflating stats
    # User should run migrate_pr_timestamps.py to fix
    return COMPLETION_UNKNOWN


def _calculate_metrics(data: dict) -> dict:
    """
    Helper to calculate metrics from tracker data structure.

    Only counts MERGED PRs (merged_at exists) as complete for public stats.
    Excludes superseded runs (remigrations).
    """
    runs = data.get("runs", [])

    # Filter out superseded runs before calculating any metrics
    active_runs = [r for r in runs if not r.get("superseded")]
    total_runs = len(active_runs)

    def _run_sort_key(run: dict) -> datetime:
        ts = run.get("merged_at") or run.get("timestamp") or ""
        if ts.endswith("+00:00Z"):
            ts = ts[:-1]
        elif ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(ts)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)

    # Only count runs that are actually complete (merged), de-duped by slug
    complete_runs = [
        r
        for r in active_runs
        if r.get("status") == RUN_STATUS_SUCCESS
        and get_pr_completion_state(r) == COMPLETION_COMPLETE
    ]
    unique_complete_by_slug: dict[str, dict] = {}
    for run in complete_runs:
        slug = run.get("slug")
        if not slug:
            continue
        existing = unique_complete_by_slug.get(slug)
        if not existing or _run_sort_key(run) > _run_sort_key(existing):
            unique_complete_by_slug[slug] = run

    unique_complete_runs = list(unique_complete_by_slug.values())
    success_count = len(unique_complete_runs)

    # Calculate time saved from unique complete runs only
    total_automation_seconds = sum(r.get("automation_seconds", 0) for r in unique_complete_runs)
    total_lines_migrated = sum(r.get("lines_migrated", 0) for r in unique_complete_runs)

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
        github_login = _get_github_login()
        if not github_login:
            run_entry["sync_status"] = SyncStatus.MISSING_GITHUB_AUTH
            logger.warning("Skipping Firebase sync: GitHub CLI not authenticated.")
            return False

        pr_author = run_entry.get("pr_author")
        if pr_author and pr_author != github_login:
            run_entry["sync_status"] = SyncStatus.AUTHOR_MISMATCH
            logger.warning(
                "Skipping Firebase sync: PR author does not match authenticated GitHub user "
                f"('{pr_author}' != '{github_login}')."
            )
            return False

        run_entry["user_id"] = github_login
        run_entry["pr_author"] = github_login

        slug = run_entry.get("slug")
        if slug:
            valid = is_official_slug(slug)
            # Allow backfill_recovery to bypass validation
            if valid is False and run_entry.get("command") != "backfill_recovery":
                run_entry["sync_status"] = SyncStatus.INVALID_SLUG
                logger.warning(f"Skipping Firebase sync for invalid slug: {slug}")
                return False
            if valid is None:
                run_entry["sync_status"] = SyncStatus.VALIDATION_UNAVAILABLE
                logger.warning("Devtools validation unavailable; delaying Firebase sync.")
                return False

        # Check for empty migrations (false positives)
        lines = run_entry.get("lines_migrated", 0)
        if lines <= 0:
            run_entry["sync_status"] = SyncStatus.SKIPPED_EMPTY
            logger.info(f"Skipping Firebase sync for empty migration ({lines} lines)")
            return False

        sync = FirebaseSync()
        return sync.push_run(github_login, run_entry)
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
            sync_status = run.get(
                "sync_status", SyncStatus.PENDING
            )  # Default to pending if missing

            if sync_status in {SyncStatus.PENDING, SyncStatus.VALIDATION_UNAVAILABLE}:
                # Attempt sync
                success = _sync_to_firebase(run)
                if success:
                    run["sync_status"] = SyncStatus.SYNCED
                    updated = True
                elif run.get("sync_status") == SyncStatus.INVALID_SLUG:
                    # If it failed, ensure it is marked as pending unless invalid
                    updated = True
                elif sync_status != SyncStatus.PENDING:
                    run["sync_status"] = SyncStatus.PENDING
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


def mark_runs_for_remigration(slugs: list[str]) -> dict[str, int]:
    """
    Mark previous completed runs for the given slugs as superseded.

    Adds a superseded flag and timestamp to indicate these runs have been
    replaced by newer migrations. Does NOT change pr_state to preserve
    GitHub truth.

    Args:
        slugs: List of theme slugs to mark for remigration.

    Returns:
        Dictionary with counts: {"updated": N, "failed": M, "not_found": K}
    """
    if not is_firebase_available():
        logger.warning("Firebase not available - cannot mark runs for remigration")
        return {"updated": 0, "failed": 0, "not_found": len(slugs)}

    # Performance warning for large batches
    if len(slugs) > 10:
        logger.warning(
            f"Marking {len(slugs)} runs for remigration. "
            f"This requires fetching all user data from Firebase and may be slow. "
            f"Consider running remigrations in smaller batches for better performance."
        )

    try:
        sync = FirebaseSync()
        settings = get_settings()
        results = {"updated": 0, "failed": 0, "not_found": 0}

        # Fetch all users' data to find runs for these slugs
        users_data = None

        if settings.firebase.is_admin_mode():
            from sbm.utils.firebase_sync import get_firebase_db

            db = get_firebase_db()
            ref = db.reference("users")
            users_data = ref.get()
        else:
            # User Mode: REST
            import requests

            from sbm.utils.firebase_sync import _get_user_mode_identity

            identity = _get_user_mode_identity()
            if not identity:
                logger.warning("Cannot authenticate for remigration marking")
                return {"updated": 0, "failed": 0, "not_found": len(slugs)}

            _, token = identity
            url = f"{settings.firebase.database_url}/users.json?auth={token}"
            resp = requests.get(url, timeout=10)
            if resp.ok:
                users_data = resp.json()
            else:
                logger.warning("Failed to fetch users data for remigration")
                return {"updated": 0, "failed": 0, "not_found": len(slugs)}

        if not users_data:
            return {"updated": 0, "failed": 0, "not_found": len(slugs)}

        # Find the most recent completed run for each slug
        slug_to_runs = {}
        for user_id, user_node in users_data.items():
            if not isinstance(user_node, dict):
                continue

            runs_node = user_node.get("runs", {})
            if not runs_node:
                continue

            for run_key, run in runs_node.items():
                if not isinstance(run, dict):
                    continue

                run_slug = run.get("slug")
                if run_slug not in slugs:
                    continue

                # Only consider completed runs (merged PRs) using shared helper
                if not is_complete_run(run):
                    continue

                # Track the most recent run for this slug
                if run_slug not in slug_to_runs:
                    slug_to_runs[run_slug] = []

                slug_to_runs[run_slug].append(
                    {
                        "user_id": user_id,
                        "run_key": run_key,
                        "merged_at": run.get("merged_at"),
                        "timestamp": run.get("timestamp"),
                    }
                )

        # Update each slug's most recent run
        from datetime import datetime, timezone

        remigrated_at = datetime.now(timezone.utc).isoformat()

        for slug in slugs:
            if slug not in slug_to_runs:
                results["not_found"] += 1
                logger.info(f"No completed run found for {slug} - skipping remigration marking")
                continue

            # Find the most recent run (by merged_at or timestamp)
            runs = slug_to_runs[slug]
            most_recent = max(runs, key=lambda r: r.get("merged_at") or r.get("timestamp") or "")

            # Mark this run as superseded
            # IMPORTANT: Do NOT change pr_state - keep it synced to GitHub reality
            # Add superseded flag to exclude from stats
            new_run_key = f"{slug}_{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H-%M-%S')}"
            updates = {
                "superseded": True,
                "superseded_at": remigrated_at,
                "superseded_by": new_run_key,
            }

            success = sync.update_run(
                user_id=most_recent["user_id"], run_key=most_recent["run_key"], updates=updates
            )

            if success:
                results["updated"] += 1
                logger.info(f"Marked run for {slug} as remigrated")
            else:
                results["failed"] += 1
                logger.warning(f"Failed to mark run for {slug} as remigrated")

        return results

    except Exception as e:
        logger.error(f"Error marking runs for remigration: {e}")
        return {"updated": 0, "failed": 0, "not_found": len(slugs)}
