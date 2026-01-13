import json
import os
import glob
from pathlib import Path
from typing import List, Optional

from sbm.utils.firebase_sync import (
    get_firebase_db,
    is_firebase_available,
)
from sbm.utils.logger import logger

# Marker file to skip redundant syncing after initial migration
LEGACY_SYNC_MARKER = Path.home() / ".sbm_legacy_sync_complete"


def sync_legacy_stats(specific_files: Optional[List[Path]] = None) -> bool:
    """
    Sync legacy archive stats to Firebase.
    Returns True if successful (or nothing to do), False on critical error.

    This is a one-time migration from local archive files to Firebase.
    After successful sync, a marker file is created to skip future syncs.
    """
    # Skip if already synced (one-time migration)
    if LEGACY_SYNC_MARKER.exists() and not specific_files:
        logger.debug("Legacy sync already complete, skipping.")
        return True

    if not is_firebase_available():
        logger.warning("Firebase unavailable. Cannot sync legacy stats.")
        return False

    db = get_firebase_db()
    users_ref = db.reference("/users")

    if specific_files:
        files = [str(f) for f in specific_files]
    else:
        # Find all archive files relative to repo root if possible, or CWD
        # Assuming run from repo root usually
        archive_pattern = os.path.join("stats", "archive", "*.json")
        files = glob.glob(archive_pattern)

    if not files:
        logger.debug("No legacy archive files found to sync.")
        return True

    logger.info(f"Syncing {len(files)} legacy archive files to Firebase...")

    total_runs_added = 0
    total_runs_skipped = 0

    for file_path in sorted(files):
        filename = os.path.basename(file_path)
        user_id_from_file = os.path.splitext(filename)[0]

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Error reading legacy file {file_path}: {e}")
            continue

        legacy_runs = data.get("runs", [])
        if not legacy_runs:
            continue

        # Get existing Firebase data for user
        user_ref = users_ref.child(user_id_from_file)
        # Optimization: Only fetch runs keys if possible, but structure prevents easy key-only fetch
        # So we fetch user data (might be large, but necessary for dedupe)
        # To avoid large fetch, we could fetch shallow=True or just push and tolerate dupes?
        # But we want to avoid dupes.
        # Let's try to fetch just runs if we can.
        firebase_runs = user_ref.child("runs").get() or {}

        existing_run_keys = set()
        for r in firebase_runs.values():
            key = f"{r.get('slug')}_{r.get('timestamp')}"
            existing_run_keys.add(key)

        runs_added = 0
        runs_skipped = 0

        for run in legacy_runs:
            slug = run.get("slug")
            timestamp = run.get("timestamp")

            if not slug or not timestamp:
                continue

            key = f"{slug}_{timestamp}"

            if key in existing_run_keys:
                runs_skipped += 1
                continue

            # Prepare run data - ensure correct types
            new_run = {
                "slug": slug,
                "timestamp": timestamp,
                "command": run.get("command", "auto"),
                "status": run.get("status", "success"),
                "user_id": user_id_from_file,
                "historical": True,
                "source": "legacy_archive_sync",
            }

            # Map metrics
            if "lines_migrated" in run:
                new_run["lines_migrated"] = int(run["lines_migrated"])
            if "duration_seconds" in run:
                new_run["duration_seconds"] = float(run["duration_seconds"])
            if "automation_seconds" in run:
                new_run["automation_seconds"] = float(run["automation_seconds"])

            # Push
            user_ref.child("runs").push(new_run)
            runs_added += 1
            total_runs_added += 1

        if runs_added > 0:
            logger.info(
                f"  Synced {runs_added} runs for {user_id_from_file} (skipped {runs_skipped})"
            )

    logger.info(f"Legacy sync complete. Added {total_runs_added} runs.")

    # Create marker to skip future syncs (one-time migration complete)
    if not specific_files:
        try:
            LEGACY_SYNC_MARKER.touch()
            logger.debug("Created legacy sync marker file.")
        except Exception as e:
            logger.debug(f"Could not create sync marker: {e}")

    return True
