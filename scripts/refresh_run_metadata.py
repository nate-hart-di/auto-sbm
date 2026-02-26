#!/usr/bin/env python3
"""
Refresh PR metadata and lines_migrated for Firebase runs.

- Updates PR timestamps/state/author when missing or stale.
- Backfills lines_migrated using GitHub additions.

Usage:
    python scripts/refresh_run_metadata.py --dry-run
    python scripts/refresh_run_metadata.py --all
    python scripts/refresh_run_metadata.py
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT))

from sbm.utils.firebase_sync import get_firebase_db, is_firebase_available
from sbm.utils.github_pr import GitHubPRManager


def fetch_additions(pr_url: str) -> int | None:
    """Fetch PR additions via gh CLI."""
    try:
        result = subprocess.run(
            ["gh", "pr", "view", pr_url, "--json", "additions"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        additions = data.get("additions")
        return additions if isinstance(additions, int) else None
    except Exception:
        return None


def needs_lines_backfill(run: dict) -> bool:
    lines = run.get("lines_migrated")
    return lines is None or lines == 0


def should_refresh_run(run: dict, force_all: bool) -> bool:
    if run.get("status") in {"failed", "invalid", "duplicate"}:
        return False
    if force_all:
        return True
    return GitHubPRManager.should_refresh_pr_data(run) or not run.get("pr_author")


def should_fix_user_id(run: dict) -> bool:
    """Return True if user_id should be set to the PR author."""
    pr_author = run.get("pr_author")
    if not pr_author:
        return False
    return run.get("user_id") != pr_author


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh Firebase run metadata")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--all", action="store_true", help="Force refresh all PRs")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of runs processed (0 = no limit)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.5,
        help="Sleep between GitHub requests in seconds (default: 0.5)",
    )
    args = parser.parse_args()

    if not is_firebase_available():
        print("Error: Firebase not available")
        sys.exit(1)

    db = get_firebase_db()
    users_ref = db.reference("/users")
    users_data = users_ref.get() or {}

    updated = 0
    lines_updated = 0
    scanned = 0

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
            if args.limit and scanned > args.limit:
                break
            pr_url = run.get("pr_url")
            if not pr_url:
                continue

            update_data = {}

            if should_refresh_run(run, args.all):
                metadata = GitHubPRManager.fetch_pr_metadata(pr_url)
                if metadata:
                    update_data.update(
                        {
                            "created_at": metadata.get("created_at"),
                            "merged_at": metadata.get("merged_at"),
                            "closed_at": metadata.get("closed_at"),
                            "pr_state": metadata.get("state"),
                            "pr_author": metadata.get("author"),
                        }
                    )
            if update_data.get("pr_author"):
                update_data["user_id"] = update_data["pr_author"]
            elif should_fix_user_id(run):
                update_data["user_id"] = run.get("pr_author")

            if needs_lines_backfill(run):
                additions = fetch_additions(pr_url)
                if additions is not None:
                    update_data["lines_migrated"] = additions

            if update_data:
                if args.dry_run:
                    print(f"[DRY RUN] Update {user_id}/{run_id}: {update_data}")
                else:
                    db.reference(f"/users/{user_id}/runs/{run_id}").update(update_data)
                updated += 1
                if "lines_migrated" in update_data:
                    lines_updated += 1

            # Rate limit GitHub requests
            if not args.dry_run and args.sleep > 0:
                time.sleep(args.sleep)
        if args.limit and scanned > args.limit:
            break

    print(f"Scanned runs: {scanned}")
    print(f"Updated runs: {updated}")
    print(f"Runs with lines_migrated backfilled: {lines_updated}")


if __name__ == "__main__":
    main()
