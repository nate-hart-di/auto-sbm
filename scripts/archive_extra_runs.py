#!/usr/bin/env python3
"""
Archive extra SBM runs in Firebase.
Moves runs that are present in Firebase but missing from the CSV to an 'archived_runs' node.
"""

import logging
import os
import sys

sys.path.append(os.getcwd())
from dotenv import load_dotenv

load_dotenv()


from sbm.utils.firebase_sync import get_firebase_db, get_settings, is_firebase_available

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


from scripts.cross_check_csv_db import (
    find_prefix_matches,
    load_csv_slugs,
    load_firebase_slugs,
)


def archive_extras():
    if not is_firebase_available():
        logger.error("Firebase not available")
        sys.exit(1)

    settings = get_settings()
    if not settings.firebase.is_admin_mode():
        logger.error("This script requires Admin Mode (service account) to move data.")
        sys.exit(1)

    db = get_firebase_db()

    # 1. Load Data using shared logic
    csv_path = "data/sbms-07.1.25-to-present.csv"
    if not os.path.exists(csv_path):
        logger.error(f"CSV not found at {csv_path}")
        sys.exit(1)

    csv_slugs = load_csv_slugs(csv_path)
    db_slugs = load_firebase_slugs()

    # 2. Perform strict matching
    matches = find_prefix_matches(csv_slugs, db_slugs)
    matched_db_slugs = set(matches.values())

    # 3. Identify all DB runs that are NOT in the matched set

    # We need the full run keys to delete/move. db_slugs only has info.
    # We need to re-query or reconstruct?
    # load_firebase_slugs returns {slug: {user, lines, pr_url, timestamp}}
    # It doesn't give us the run_key!

    # We need to iterate the raw DB again to get keys.
    ref = db.reference("users")
    users_data = ref.get() or {}

    moves_count = 0

    for user_id, user_data in users_data.items():
        if not isinstance(user_data, dict):
            continue
        runs = user_data.get("runs", {})

        user_archive_ref = db.reference(f"users/{user_id}/archived_runs")
        user_runs_ref = db.reference(f"users/{user_id}/runs")

        for run_key, run in runs.items():
            if not isinstance(run, dict):
                continue
            slug = run.get("slug", "").lower()

            # If slug is not in the "Matched DB Slugs" set, it's an Extra.
            if slug not in matched_db_slugs:
                logger.info(f"User {user_id}: Archiving Extra {slug} ({run_key})...")
                # Archive
                user_archive_ref.child(run_key).set(run)
                # Delete
                user_runs_ref.child(run_key).delete()
                moves_count += 1

    logger.info(f"Done. Archived {moves_count} extra runs.")


if __name__ == "__main__":
    archive_extras()
