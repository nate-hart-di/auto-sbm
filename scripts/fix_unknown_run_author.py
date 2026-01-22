#!/usr/bin/env python3
"""
Fix a single Firebase run's author/user_id using GitHub PR metadata.

Usage:
  python scripts/fix_unknown_run_author.py --user-id <firebase_user_id> --run-id <run_key>
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT))

from sbm.utils.firebase_sync import get_firebase_db, is_firebase_available
from sbm.utils.github_pr import GitHubPRManager


def main() -> None:
    parser = argparse.ArgumentParser(description="Fix a single run's author/user_id")
    parser.add_argument("--user-id", required=True, help="Firebase user bucket id")
    parser.add_argument("--run-id", required=True, help="Run key under user bucket")
    args = parser.parse_args()

    if not is_firebase_available():
        print("Error: Firebase not available")
        sys.exit(1)

    db = get_firebase_db()
    ref = db.reference(f"/users/{args.user_id}/runs/{args.run_id}")
    run = ref.get()
    if not isinstance(run, dict):
        print("Error: run not found or invalid")
        sys.exit(1)

    pr_url = run.get("pr_url")
    if not pr_url:
        print("Error: run has no pr_url")
        sys.exit(1)

    metadata = GitHubPRManager.fetch_pr_metadata(pr_url)
    if not metadata or not metadata.get("author"):
        print("Error: could not resolve PR author")
        sys.exit(1)

    update = {
        "pr_author": metadata.get("author"),
        "user_id": metadata.get("author"),
        "created_at": metadata.get("created_at"),
        "merged_at": metadata.get("merged_at"),
        "closed_at": metadata.get("closed_at"),
        "pr_state": metadata.get("state"),
    }

    ref.update(update)
    print(f"Updated {args.user_id}/{args.run_id} -> {metadata.get('author')}")


if __name__ == "__main__":
    main()
