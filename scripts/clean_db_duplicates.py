import os
import sys
from collections import defaultdict

import firebase_admin
from firebase_admin import credentials, db

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbm.config import get_settings


def clean_database():
    settings = get_settings()
    user_id = "nate-hart-di"  # Hardcoded based on context

    print(f"Cleaning database for user: {user_id}")

    if settings.firebase.is_admin_mode():
        cred = credentials.Certificate(str(settings.firebase.credentials_path))
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {"databaseURL": settings.firebase.database_url})
        ref = db.reference(f"users/{user_id}/runs")
        data = ref.get()
    else:
        print("This script requires Admin Mode to delete duplicates safely.")
        return

    if not data:
        print("No data found.")
        return

    print(f"Total raw records: {len(data)}")

    # Group by slug
    runs_by_slug = defaultdict(list)
    failed_keys = []

    for key, run in data.items():
        if run.get("status") == "success":
            slug = run.get("slug")
            if slug:
                runs_by_slug[slug].append((key, run))
            else:
                print(f"Warning: Success run missing slug: {key}")
                failed_keys.append(key)  # Treat as failed if no slug
        else:
            failed_keys.append(key)

    unique_slugs = len(runs_by_slug)
    print(f"Unique successful slugs found: {unique_slugs}")

    keys_to_delete = []
    keys_to_keep = []

    # 1. Mark failed runs for deletion
    keys_to_delete.extend(failed_keys)
    print(f"Failed/Invalid runs to delete: {len(failed_keys)}")

    # 2. Deduplicate successful runs
    duplicate_count = 0
    for slug, entries in runs_by_slug.items():
        if len(entries) > 1:
            # Sort by timestamp (newest first)
            # Timestamps are in the key now: slug_YYYY-MM-DD... so alphabetical sort of key works perfectly for latest
            # But let's rely on the run['timestamp'] field if possible, or key if not.

            def sort_key(item):
                k, r = item
                ts = r.get("timestamp", "")
                return ts

            # Sort descending (newest first)
            entries.sort(key=sort_key, reverse=True)

            # Keep first (newest), delete rest
            keep_key, keep_run = entries[0]
            keys_to_keep.append(keep_key)

            for delete_key, _ in entries[1:]:
                keys_to_delete.append(delete_key)
                duplicate_count += 1
        else:
            keys_to_keep.append(entries[0][0])

    print(f"Duplicates to delete: {duplicate_count}")
    print(f"Total records to delete: {len(keys_to_delete)}")
    print(f"Total records to keep: {len(keys_to_keep)}")

    if len(keys_to_keep) != unique_slugs:
        print(f"WARNING: Keep count ({len(keys_to_keep)}) != Unique Slugs ({unique_slugs})")

    print("-" * 30)
    print("Preview of Keeps:")
    print(keys_to_keep[:5])

    if input("Commit deletion of duplicates and failures? (y/n): ").lower() == "y":
        update_payload = {}
        for key in keys_to_delete:
            update_payload[key] = None

        ref.update(update_payload)
        print("Cleanup complete.")
    else:
        print("Aborted.")


if __name__ == "__main__":
    clean_database()
