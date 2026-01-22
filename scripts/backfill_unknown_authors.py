#!/usr/bin/env python3
"""
Backfill PR author/user_id for Firebase runs with unknown attribution.

Usage:
  python scripts/backfill_unknown_authors.py --apply
  python scripts/backfill_unknown_authors.py --dry-run
"""

import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT))

from sbm.utils.firebase_sync import get_firebase_db, is_firebase_available
from sbm.utils.github_pr import GitHubPRManager


def is_unknown(value: str | None) -> bool:
    if not value:
        return True
    return value.strip().lower() in {"unknown", "unknown_user"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill PR author/user_id for runs")
    parser.add_argument("--apply", action="store_true", help="Write updates to Firebase")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--limit", type=int, default=0, help="Max runs to process (0 = all)")
    parser.add_argument("--sleep", type=float, default=0.5, help="Sleep between GH calls")
    parser.add_argument(
        "--progress-every",
        type=int,
        default=100,
        help="Print progress every N runs scanned",
    )
    args = parser.parse_args()

    if args.apply and args.dry_run:
        print("Error: choose either --apply or --dry-run, not both")
        sys.exit(1)

    if not is_firebase_available():
        print("Error: Firebase not available")
        sys.exit(1)

    db = get_firebase_db()
    users_ref = db.reference("/users")
    users_data = users_ref.get() or {}

    scanned = 0
    updated = 0
    skipped_no_pr = 0
    skipped_no_author = 0

    for user_id, user_data in users_data.items():
        if not isinstance(user_data, dict):
            continue
        runs = user_data.get("runs", {})
        if not isinstance(runs, dict):
            continue

        for run_id, run in runs.items():
            if not isinstance(run, dict):
                continue
            scanned += 1
            if args.progress_every and scanned % args.progress_every == 0:
                print(f"Scanned {scanned} runs... (updated {updated})")
            if args.limit and scanned > args.limit:
                break

            pr_url = run.get("pr_url")
            if not pr_url:
                skipped_no_pr += 1
                continue

            pr_author = run.get("pr_author")
            run_user_id = run.get("user_id")
            if not (is_unknown(pr_author) or is_unknown(run_user_id) or run_user_id != pr_author):
                continue

            metadata = GitHubPRManager.fetch_pr_metadata(pr_url)
            if not metadata or not metadata.get("author"):
                skipped_no_author += 1
                continue

            update_data = {
                "pr_author": metadata.get("author"),
                "user_id": metadata.get("author"),
                "created_at": metadata.get("created_at"),
                "merged_at": metadata.get("merged_at"),
                "closed_at": metadata.get("closed_at"),
                "pr_state": metadata.get("state"),
            }

            if args.dry_run or not args.apply:
                print(f"[DRY RUN] {user_id}/{run_id}: {update_data}")
            else:
                db.reference(f"/users/{user_id}/runs/{run_id}").update(update_data)
                print(f"Updated {user_id}/{run_id}: {update_data['pr_author']}")
            updated += 1

            if args.sleep > 0:
                time.sleep(args.sleep)

        if args.limit and scanned > args.limit:
            break

    print(f"Scanned runs: {scanned}")
    print(f"Updated runs: {updated}")
    print(f"Skipped (no PR url): {skipped_no_pr}")
    print(f"Skipped (no PR author found): {skipped_no_author}")


if __name__ == "__main__":
    main()
