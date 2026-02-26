import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from sbm.utils.firebase_sync import (
    get_firebase_db,
    get_settings,
    is_firebase_available,
)
from sbm.utils.logger import setup_logger

logger = setup_logger()


def get_db_ref(path):
    """Helper to get DB reference regardless of mode."""
    settings = get_settings()
    if settings.firebase.is_admin_mode():
        db = get_firebase_db()
        return db.reference(path)
    return None  # REST mode handling needed if we want to fully support it, but for migration script arguably we might need admin or careful REST calls.
    # Actually, the user might be in User Mode. Let's support both if possible, or fail if not.
    # The user info says "nate-hart-di" is the user.


def migrate_keys(commit=False):
    if not is_firebase_available():
        logger.error("Firebase unavailable. Cannot migrate.")
        return

    settings = get_settings()
    if not settings.firebase.is_admin_mode():
        logger.error("Migration requires Admin Mode to enumerate all users.")
        return

    db = get_firebase_db()
    users_ref = db.reference("users")
    all_users = users_ref.get()

    if not all_users:
        logger.info("No users found in database.")
        return

    logger.info(f"Found {len(all_users)} users in database. Starting team-wide migration...")

    total_stats = {"users_processed": 0, "runs_migrated": 0, "errors": 0}

    for user_id, user_data in all_users.items():
        if not isinstance(user_data, dict) or "runs" not in user_data:
            continue

        logger.info(f"Processing user: {user_id}")
        runs_data = user_data.get("runs", {})

        updates = {}
        deletions = []

        # Track seen keys to avoid collisions
        seen_keys = set()

        # Pre-scan existing valid keys to avoiding collisions with already migrated data
        for k in runs_data.keys():
            if "_" in k and "-" in k:  # Rough heuristic for new format
                seen_keys.add(k)

        for key, run in runs_data.items():
            # Skip if already migrated (simple check: key contains slug)
            # Or if it's already in the new format (contains underscore and timestamp-ish)
            slug = run.get("slug", "unknown")

            # Check if key looks like "slug_timestamp"
            if key.startswith(f"{slug}_"):
                # Likely already migrated
                continue

            # It's an old key (Firebase Push ID starts with -)
            # OR just doesn't match our format

            timestamp = run.get("timestamp", datetime.now().isoformat())

            # 1. Clean timestamp
            ts_clean = timestamp.strip()
            if ts_clean.endswith("Z"):
                ts_clean = ts_clean[:-1]

            try:
                # Handle potentially missing seconds or timezone info by standardizing
                # We expect ISO format: YYYY-MM-DDTHH:MM:SS...
                # If +00:00 is missing, assume UTC
                dt = datetime.fromisoformat(ts_clean.replace("Z", "+00:00"))
                ts_str = dt.strftime("%Y-%m-%d_%H-%M-%S")
            except ValueError:
                logger.warning(f"  Invalid timestamp for {key}: {timestamp}. Using current time.")
                ts_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

            new_key = f"{slug}_{ts_str}"

            # 2. Collision handling
            files__created = run.get("files_created_count", 0)

            # If we simply have duplicate timestamps for the same slug, append valid counter
            base_key = new_key
            counter = 1
            while new_key in seen_keys or (new_key in updates):
                new_key = f"{base_key}_{counter}"
                counter += 1

            # Add to batch
            updates[new_key] = run
            deletions.append(key)
            seen_keys.add(new_key)

        if not updates and not deletions:
            logger.info(f"  No runs to migrate for {user_id}.")
            continue

        logger.info(f"  Prepared {len(updates)} migrations for {user_id}.")

        if commit:
            user_runs_ref = db.reference(f"users/{user_id}/runs")
            update_payload = {}
            for k, v in updates.items():
                update_payload[k] = v
            for k in deletions:
                update_payload[k] = None

            try:
                user_runs_ref.update(update_payload)
                logger.info(f"  SUCCESS: Migrated {len(updates)} runs for {user_id}.")
                total_stats["runs_migrated"] += len(updates)
                total_stats["users_processed"] += 1
            except Exception as e:
                logger.error(f"  FAILED to commit for {user_id}: {e}")
                total_stats["errors"] += 1
        else:
            logger.info(f"  [DRY RUN] Would migrate {len(updates)} runs for {user_id}.")

    logger.info("-" * 30)
    if commit:
        logger.info(
            f"Team migration complete. Processed {total_stats['users_processed']} users. Migrated {total_stats['runs_migrated']} runs."
        )
    else:
        logger.info("Dry run complete. Run with --commit to execute.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--commit", action="store_true", help="Execute the migration (default is dry-run)"
    )
    args = parser.parse_args()

    migrate_keys(commit=args.commit)
