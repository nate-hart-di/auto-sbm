#!/usr/bin/env python3
"""
Daily Firebase sync script for GitHub Action.

This script:
1. Fetches recently merged SBM PRs from GitHub (last 7 days)
2. Updates Firebase runs with merged_at, lines_migrated, pr_state
3. Marks runs without merged PRs as needs_review after 30 days

Designed to run as a scheduled GitHub Action.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT))

from sbm.utils.firebase_sync import get_firebase_db, is_firebase_available


def get_recently_merged_sbm_prs(days: int = 7) -> list[dict]:
    """Fetch SBM PRs merged in the last N days."""
    since_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    all_prs = []
    search_queries = [
        f'"SBM FE Audit" in:title merged:>={since_date}',
        f'"Site Builder Migration" in:title merged:>={since_date}',
        f'"SBM: Migrate" in:title merged:>={since_date}',
    ]

    for query in search_queries:
        try:
            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "list",
                    "--repo",
                    "carsdotcom/di-websites-platform",
                    "--state",
                    "merged",
                    "--search",
                    query,
                    "--json",
                    "url,title,headRefName,additions,author,mergedAt,number",
                    "--limit",
                    "100",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
            if result.returncode == 0:
                prs = json.loads(result.stdout)
                all_prs.extend(prs)
        except Exception as e:
            print(f"Error searching PRs: {e}")

    # Deduplicate
    seen = set()
    unique = []
    for pr in all_prs:
        pr_num = pr.get("number")
        if pr_num and pr_num not in seen:
            seen.add(pr_num)
            unique.append(pr)

    return unique


def extract_slug_from_pr(pr: dict) -> str | None:
    """Extract slug from PR title or branch."""
    import re

    title = pr.get("title", "")
    branch = pr.get("headRefName", "")

    # Title patterns
    patterns = [
        r"^(.+?)\s*-\s*SBM FE Audit",
        r"^PCON-\d+:\s*(.+?)\s+SBM",
        r"^\[(.+?)\]\s*-\s*Site Builder",
        r"^(.+?)\s*-\s*Site Builder Migration",
        r"^SBM:\s*Migrate\s+(.+?)\s+to",
    ]

    for pattern in patterns:
        match = re.match(pattern, title, re.IGNORECASE)
        if match:
            return match.group(1).strip().lower()

    # Branch patterns
    branch_lower = branch.lower()
    match = re.match(r"^pcon-\d+-(.+?)-sbm\d{4}$", branch_lower)
    if match:
        return match.group(1)

    match = re.match(r"^(.+?)-sbm\d{4}$", branch_lower)
    if match:
        return match.group(1)

    if branch_lower.startswith("sbm/"):
        return branch_lower[4:]

    return None


def main():
    print("=" * 60)
    print("DAILY FIREBASE SYNC")
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    if not is_firebase_available():
        print("ERROR: Firebase not available")
        sys.exit(1)

    # 1. Fetch recently merged PRs
    print("\n[1/3] Fetching recently merged SBM PRs...")
    merged_prs = get_recently_merged_sbm_prs(days=7)
    print(f"Found {len(merged_prs)} merged SBM PRs in last 7 days")

    # Build slug -> PR mapping
    pr_by_slug = {}
    for pr in merged_prs:
        slug = extract_slug_from_pr(pr)
        if slug:
            pr_by_slug[slug] = {
                "url": pr.get("url"),
                "lines": pr.get("additions", 0),
                "author": pr.get("author", {}).get("login"),
                "merged_at": pr.get("mergedAt"),
                "pr_number": pr.get("number"),
            }

    print(f"Mapped {len(pr_by_slug)} slugs to PRs")

    # 2. Update Firebase runs
    print("\n[2/3] Updating Firebase runs...")
    db = get_firebase_db()
    users_ref = db.reference("/users")
    users_data = users_ref.get() or {}

    updates_made = 0
    stale_runs = 0

    for user_id, user_data in users_data.items():
        if not isinstance(user_data, dict):
            continue
        runs = user_data.get("runs", {})

        for run_key, run in runs.items():
            # Skip invalid/failed runs
            if run.get("status") not in ("success", "pending_merge", "needs_review"):
                continue

            slug = run.get("slug", "").lower()
            if not slug:
                continue

            pr_data = pr_by_slug.get(slug)

            if pr_data:
                # Update with PR data
                updates = {}
                if not run.get("pr_url"):
                    updates["pr_url"] = pr_data["url"]
                if not run.get("pr_author"):
                    updates["pr_author"] = pr_data["author"]
                if not run.get("merged_at"):
                    updates["merged_at"] = pr_data["merged_at"]
                if not run.get("pr_state") or run.get("pr_state") != "MERGED":
                    updates["pr_state"] = "MERGED"
                if pr_data["lines"] > 0 and run.get("lines_migrated", 0) != pr_data["lines"]:
                    updates["lines_migrated"] = pr_data["lines"]
                if run.get("status") == "pending_merge":
                    updates["status"] = "success"

                if updates:
                    db.reference(f"/users/{user_id}/runs/{run_key}").update(updates)
                    updates_made += 1
                    print(f"  Updated: {slug} - {list(updates.keys())}")

            # Check for stale pending runs (older than 30 days without merge)
            elif run.get("status") == "pending_merge":
                timestamp = run.get("timestamp", "")
                if timestamp:
                    try:
                        run_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                        if datetime.now(timezone.utc) - run_date > timedelta(days=30):
                            db.reference(f"/users/{user_id}/runs/{run_key}").update(
                                {"status": "needs_review"}
                            )
                            stale_runs += 1
                            print(f"  Stale: {slug} -> needs_review (>30 days)")
                    except Exception:
                        pass

    # 3. Summary
    print("\n[3/3] Summary")
    print("=" * 60)
    print(f"PRs processed:    {len(merged_prs)}")
    print(f"Runs updated:     {updates_made}")
    print(f"Stale runs marked: {stale_runs}")
    print(f"Completed at:     {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
