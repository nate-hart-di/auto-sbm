#!/usr/bin/env python3
"""List Firebase runs missing PR author/user_id."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT))

from sbm.utils.firebase_sync import get_firebase_db, is_firebase_available


def is_unknown(value: str | None) -> bool:
    if not value:
        return True
    return value.strip().lower() in {"unknown", "unknown_user"}


def main() -> None:
    if not is_firebase_available():
        print("Error: Firebase not available")
        sys.exit(1)

    db = get_firebase_db()
    users = db.reference("/users").get() or {}

    for user_id, user_data in users.items():
        if not isinstance(user_data, dict):
            continue
        runs = user_data.get("runs", {})
        if not isinstance(runs, dict):
            continue
        for run_id, run in runs.items():
            if not isinstance(run, dict):
                continue
            pr_url = run.get("pr_url")
            if not pr_url:
                continue
            pr_author = run.get("pr_author")
            run_user_id = run.get("user_id")
            if is_unknown(pr_author) or is_unknown(run_user_id) or run_user_id != pr_author:
                slug = run.get("slug", "unknown")
                print(f"{user_id}\t{run_id}\t{slug}\t{pr_url}\tpr_author={pr_author}\tuser_id={run_user_id}")


if __name__ == "__main__":
    main()
