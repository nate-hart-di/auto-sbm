#!/usr/bin/env python3
"""
Clean up Firebase by removing garbage runs with invalid slugs.

Invalid slugs include:
- Numeric strings (ticket numbers like "03512576")
- Bracket-prefixed strings like "[ready]"
- Generic words like "added", "dealertheme", "update", "test"
- Very short slugs (< 4 chars)

Usage:
    python scripts/cleanup_firebase_garbage.py --dry-run
    python scripts/cleanup_firebase_garbage.py
"""

import argparse
import re
import sys
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT))

from sbm.utils.firebase_sync import get_firebase_db, is_firebase_available


def is_garbage_slug(slug: str) -> bool:
    """
    Return True if the slug is garbage/invalid data.

    Garbage patterns:
    - Empty or None
    - Purely numeric (ticket numbers)
    - Starts with [ (bracketed text)
    - Generic words that aren't real dealer slugs
    - Less than 4 characters
    """
    if not slug:
        return True

    slug_lower = slug.strip().lower()

    # Too short to be a real dealer slug
    if len(slug_lower) < 4:
        return True

    # Purely numeric (ticket numbers)
    if slug_lower.isdigit():
        return True

    # Starts with bracket
    if slug_lower.startswith("["):
        return True

    # Generic garbage words (not real dealers)
    garbage_words = {
        "added",
        "adding",
        "update",
        "updated",
        "test",
        "testing",
        "dealertheme",
        "auto",
        "migrate",
        "migration",
        "fix",
        "fixes",
        "ready",
        "new",
        "sbm",
        "theme",
        "dealer",
        "site",
        "builder",
    }
    if slug_lower in garbage_words:
        return True

    # Contains only generic prefix without substance
    if re.match(r"^(pcon-\d+|sdweb-\d+|\d+-\w+)$", slug_lower):
        return True

    return False


def main():
    parser = argparse.ArgumentParser(description="Clean up garbage Firebase runs")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview deletions without executing"
    )
    args = parser.parse_args()

    if not is_firebase_available():
        print("Error: Firebase not available")
        sys.exit(1)

    print("Fetching all runs from Firebase...")
    db = get_firebase_db()
    users_ref = db.reference("/users")
    users_data = users_ref.get() or {}

    garbage_runs = []
    valid_runs = 0

    # Scan all runs
    for user_id, user_data in users_data.items():
        if not isinstance(user_data, dict):
            continue
        runs = user_data.get("runs", {})

        for run_key, run in runs.items():
            slug = run.get("slug", "")

            if is_garbage_slug(slug):
                garbage_runs.append(
                    {
                        "user_id": user_id,
                        "run_key": run_key,
                        "slug": slug,
                        "status": run.get("status"),
                    }
                )
            else:
                valid_runs += 1

    print(f"\nFound {len(garbage_runs)} garbage runs to delete")
    print(f"Found {valid_runs} valid runs to keep")

    if not garbage_runs:
        print("\nNo garbage runs found. Database is clean!")
        return

    # Show sample of what will be deleted
    print("\n=== Sample garbage slugs ===")
    unique_slugs = sorted(set(r["slug"] for r in garbage_runs))[:20]
    for slug in unique_slugs:
        count = sum(1 for r in garbage_runs if r["slug"] == slug)
        print(f"  '{slug}' ({count} runs)")

    if len(unique_slugs) < len(set(r["slug"] for r in garbage_runs)):
        print(f"  ... and {len(set(r['slug'] for r in garbage_runs)) - 20} more unique slugs")

    if args.dry_run:
        print(f"\n[DRY RUN] Would delete {len(garbage_runs)} garbage runs.")
        return

    # Confirm before deleting
    confirm = input(f"\nDelete {len(garbage_runs)} garbage runs? (yes/no): ")
    if confirm.lower() != "yes":
        print("Aborted.")
        return

    # Delete garbage runs
    print("\nDeleting garbage runs...")
    deleted = 0
    errors = 0

    for run_info in garbage_runs:
        try:
            run_ref = db.reference(f"/users/{run_info['user_id']}/runs/{run_info['run_key']}")
            run_ref.delete()
            deleted += 1
            if deleted % 50 == 0:
                print(f"  Deleted {deleted}/{len(garbage_runs)}...")
        except Exception as e:
            print(f"  Error deleting {run_info['run_key']}: {e}")
            errors += 1

    print(f"\nComplete! Deleted {deleted} runs, {errors} errors.")


if __name__ == "__main__":
    main()
