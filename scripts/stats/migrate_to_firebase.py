#!/usr/bin/env python3
"""
Legacy Data Import Utility for SBM.
Migrates local .sbm_migrations.json history to Firebase.
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterable, Tuple
import time

try:
    from rich.console import Console
    from rich.progress import track as rich_track
except ImportError:
    print("Rich library not found. Please install requirements.")
    sys.exit(1)

# Ensure project root is in path to import sbm modules
# assuming this script is in scripts/stats/
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from sbm.config import AutoSBMSettings
    from sbm.utils.firebase_sync import get_firebase_db, is_firebase_available, _initialize_firebase
except ImportError as e:
    print(f"Error importing SBM modules: {e}")
    sys.exit(1)

console = Console()


def _load_json_with_recovery(path: Path) -> Optional[Dict[str, Any]]:
    """Load JSON from path with best-effort recovery for truncated files."""
    try:
        text = path.read_text()
    except Exception as e:
        console.print(f"[red]Error reading {path}: {e}[/red]")
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        console.print(
            f"[yellow]{path} appears corrupted; attempting partial recovery.[/yellow]"
        )
        recovered = _recover_tracker_json(text, e)
        if recovered is None:
            console.print(f"[red]Failed to recover {path}: {e}[/red]")
        return recovered


def load_local_history() -> List[Dict[str, Any]]:
    """
    Load local migration history.
    Expects .sbm_migrations.json with structure: {"runs": [...], "last_updated": ...}
    """
    history_path = Path.home() / ".sbm_migrations.json"
    if not history_path.exists():
        console.print(f"[yellow]No local history found at {history_path}[/yellow]")
        return []

    data = _load_json_with_recovery(history_path)
    if not data:
        return []
    # Schema Fix: Return the 'runs' list, not the whole object
    return data.get("runs", [])


def _recover_tracker_json(text: str, error: json.JSONDecodeError) -> Dict[str, Any] | None:
    """Best-effort recovery for truncated tracker JSON."""
    # Trim to the point of failure and drop the last incomplete entry.
    prefix = text[: error.pos]
    last_comma = prefix.rfind(",")
    if last_comma != -1:
        prefix = prefix[:last_comma]
    prefix = prefix.rstrip()
    if prefix.endswith(":"):
        prefix = prefix[:-1]

    # Balance braces/brackets as a simple recovery strategy.
    open_braces = prefix.count("{") - prefix.count("}")
    open_brackets = prefix.count("[") - prefix.count("]")
    if open_braces < 0 or open_brackets < 0:
        return None

    candidate = prefix + ("]" * open_brackets) + ("}" * open_braces)
    try:
        return json.loads(candidate)
    except Exception:
        return None


def push_run_to_firebase(user_id: str, run_data: Dict[str, Any]) -> bool:
    """Push a single run to Firebase using FirebaseSync (handles Admin/User mode)."""
    try:
        # Generate a run_id if missing (legacy data might skip it)
        # But wait, legacy data doesn't have run_id usually?
        # In tracker.py, runs are just a list.
        # Firebase expects a dict of push IDs.
        # We should just push usage FirebaseSync.push_run which generates the ID.

        from sbm.utils.firebase_sync import FirebaseSync

        # Ensure we don't push duplicates if we can avoid it.
        # Currently the script tries to check existence by run_id, but local data DOES NOT HAVE run_id.
        # It relies on list index or timestamp usually.
        # Retrospective Finding: "Legacy script ... expects run_id (never recorded)"
        # FIX: We will just push all of them? Or checks for slug/timestamp duplicate?
        # Story 2-5 added global duplicate check.
        # Let's rely on FirebaseSync.push_run.
        # But we want to avoid re-pushing if run already exists?
        # We can fetch all runs for user first (in memory check).

        sync = FirebaseSync()
        return sync.push_run(user_id, run_data)

    except Exception as e:
        console.print(f"[red]Error pushing run: {e}[/red]")
        return False


def track_progress(sequence, description):
    """Wrapper for rich.progress.track to simplify mocking in tests."""
    return rich_track(sequence, description=description)


def get_existing_signatures(user_id: str) -> set[str]:
    """Fetch existing runs to prevent duplicates (by timestamp + slug)."""
    try:
        from sbm.utils.firebase_sync import is_firebase_available, get_firebase_db
        from sbm.config import get_settings
        import requests

        if not is_firebase_available():
            return set()

        settings = get_settings()
        existing = set()

        if settings.firebase.is_admin_mode():
            db = get_firebase_db()
            ref = db.reference(f"users/{user_id}/runs")
            data = ref.get()
        else:
            url = f"{settings.firebase.database_url}/users/{user_id}/runs.json"
            resp = requests.get(url, timeout=10)
            data = resp.json() if resp.ok else None

        if data:
            for _, run in data.items():
                sig = f"{run.get('timestamp')}_{run.get('slug')}"
                existing.add(sig)
        return existing
    except Exception:
        return set()


def _normalize_run(user_id: str, run: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure run payload has minimal context for Firebase."""
    normalized = dict(run)
    normalized.setdefault("user_id", user_id)
    return normalized


def perform_migration(user_id: str, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, int]:
    """Execute the migration process."""
    if history is None:
        history = load_local_history()
    stats = {"total": len(history), "migrated": 0, "skipped": 0, "errors": 0}

    if not history:
        return stats

    # Ensure Firebase is ready
    if not is_firebase_available():
        console.print("[yellow]Initializing Firebase connection...[/yellow]")
        if not _initialize_firebase():
            console.print("[red]Failed to initialize Firebase. check configuration.[/red]")
            return stats

    # Pre-fetch existing to skip duplicates
    existing_signatures = get_existing_signatures(user_id)

    console.print(
        f"[bold blue]Found {len(history)} local records. Starting migration...[/bold blue]"
    )

    for run in track_progress(history, description="Migrating records..."):
        # Create signature
        sig = f"{run.get('timestamp')}_{run.get('slug')}"

        if sig in existing_signatures:
            stats["skipped"] += 1
            continue

        if push_run_to_firebase(user_id, _normalize_run(user_id, run)):
            stats["migrated"] += 1
            # Add to local signature set to prevent dupes within same run
            existing_signatures.add(sig)
        else:
            stats["errors"] += 1

    return stats


def _iter_archive_users() -> Iterable[Tuple[str, List[Dict[str, Any]]]]:
    """Yield (user_id, runs) from stats archive files."""
    archive_dir = Path("stats/archive")
    if not archive_dir.exists():
        return []

    for path in sorted(archive_dir.glob("*.json")):
        data = _load_json_with_recovery(path)
        if not data:
            continue
        runs = data.get("runs", [])
        if not isinstance(runs, list) or not runs:
            continue
        user_id = data.get("user") or path.stem
        yield user_id, runs


def _iter_stats_users() -> Iterable[Tuple[str, List[Dict[str, Any]]]]:
    """Yield (user_id, runs) from legacy stats/*.json files (non-archive)."""
    stats_dir = Path("stats")
    if not stats_dir.exists():
        return []

    for path in sorted(stats_dir.glob("*.json")):
        data = _load_json_with_recovery(path)
        if not data:
            continue
        runs = data.get("runs", [])
        if not isinstance(runs, list) or not runs:
            continue
        user_id = data.get("user") or path.stem
        yield user_id, runs


def perform_global_migration() -> Dict[str, Dict[str, int]]:
    """Migrate all historical runs for all users."""
    results: Dict[str, Dict[str, int]] = {}

    sources = list(_iter_stats_users()) + list(_iter_archive_users())
    if not sources:
        console.print("[yellow]No historical stats files found to migrate.[/yellow]")
        return results

    for user_id, runs in sources:
        console.print(
            f"[bold blue]Migrating {len(runs)} runs for user {user_id}...[/bold blue]"
        )
        results[user_id] = perform_migration(user_id, runs)
    return results


def main():
    """Main entry point."""
    settings = AutoSBMSettings()

    if not settings.firebase.is_configured():
        console.print("[red]Firebase not configured. Please check your .env file.[/red]")
        return

    global_mode = "--all-users" in sys.argv

    if global_mode:
        results = perform_global_migration()
        console.print("\n[bold green]Migration Complete![/bold green]")
        for user_id, stats in results.items():
            console.print(f"\n[bold]{user_id}[/bold]")
            console.print(f"Total Records: {stats['total']}")
            console.print(f"Imported:      {stats['migrated']}")
            console.print(f"Skipped:       {stats['skipped']} (Duplicate or Invalid)")
            console.print(f"Errors:        {stats['errors']}")
        return

    # User ID Fix: Use the same logic as tracker.py
    from sbm.utils.tracker import _get_user_id

    user_id = _get_user_id()

    console.print(f"[bold]Migrating history for user: {user_id}[/bold]")

    stats = perform_migration(user_id)

    console.print("\n[bold green]Migration Complete![/bold green]")
    console.print(f"Total Records: {stats['total']}")
    console.print(f"Imported:      {stats['migrated']}")
    console.print(f"Skipped:       {stats['skipped']} (Duplicate or Invalid)")
    console.print(f"Errors:        {stats['errors']}")


if __name__ == "__main__":
    main()
