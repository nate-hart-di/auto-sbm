#!/usr/bin/env python3
"""
Backfill Firebase runs with PR links, lines_migrated, PR author, and merged date.

STRICT DATA HYGIENE:
1. Only MERGED PRs count - CLOSED PRs are ignored entirely.
2. Runs without a MERGED PR are marked as 'needs_review'.
3. Duplicate slugs: LATEST run gets the line count, older runs get 0.
4. Stores: pr_url, pr_author, pr_state, merged_at, lines_migrated

Usage:
    python scripts/backfill_firebase_runs.py --dry-run
    python scripts/backfill_firebase_runs.py --force
    python scripts/backfill_firebase_runs.py --reprocess-incomplete
    python scripts/backfill_firebase_runs.py --add-merged-at
"""

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT))

from sbm.utils.firebase_sync import get_firebase_db, is_firebase_available


def is_valid_sbm_pr(slug: str, title: str, branch: str) -> bool:
    """
    Check if a PR matches valid SBM PR patterns.

    Valid title patterns:
    - "{slug} - SBM FE Audit"
    - "PCON-727: {slug} SBM FE Audit"
    - "SBM: Migrate {slug} to Site Builder format"
    - "[{slug}] - Site Builder Migration"
    - "{slug} - Site Builder Migration"

    Valid branch patterns:
    - "{slug}-sbm{mmyy}" (e.g., "fowlerjeepofboulder-sbm0725")
    - "pcon-727-{slug}-sbm{mmyy}" (e.g., "pcon-727-lexusofclearwater-sbm1225")
    - "sbm/{slug}"
    """
    slug_lower = slug.lower()
    title_lower = title.lower()
    branch_lower = branch.lower()

    # Title pattern checks (must contain SBM-related keywords)
    title_patterns = [
        (slug_lower in title_lower and "sbm fe audit" in title_lower),
        (title_lower.startswith("sbm:") and slug_lower in title_lower),
        (slug_lower in title_lower and "site builder migration" in title_lower),
        (slug_lower in title_lower and "sbm migration" in title_lower),
    ]

    # Branch pattern checks
    branch_patterns = [
        re.match(rf"^{re.escape(slug_lower)}-sbm\d{{4}}$", branch_lower) is not None,
        re.match(rf"^pcon-727-{re.escape(slug_lower)}-sbm\d{{4}}$", branch_lower) is not None,
        branch_lower == f"sbm/{slug_lower}",
    ]

    return any(title_patterns) or any(branch_patterns)


def get_pr_details_for_slug(slug: str) -> dict | None:
    """
    Find MERGED SBM PR for a slug (ignores CLOSED PRs entirely).

    Returns dict with: url, lines, author, state, merged_at
    """
    try:
        # Search for MERGED PRs only (strict - no CLOSED)
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                "carsdotcom/di-websites-platform",
                "--state",
                "merged",  # Only merged!
                "--search",
                f"{slug} in:title",
                "--json",
                "url,title,headRefName,additions,author,state,mergedAt,number",
                "--limit",
                "20",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

        if result.returncode != 0:
            return None

        prs = json.loads(result.stdout)

        # Filter to only valid SBM PRs
        candidates = []
        for pr in prs:
            branch = pr.get("headRefName", "")
            title = pr.get("title", "")
            if is_valid_sbm_pr(slug, title, branch):
                candidates.append(pr)

        if not candidates:
            # No merged SBM PR found - check for open PRs as fallback info
            return _check_open_prs(slug)

        # Sort by exact branch match, then by date
        def sort_key(pr):
            slug_lower = slug.lower()
            branch_lower = pr.get("headRefName", "").lower()
            if branch_lower == f"sbm/{slug_lower}":
                exact_branch = 2
            elif f"-{slug_lower}-sbm" in branch_lower or branch_lower.startswith(
                f"{slug_lower}-sbm"
            ):
                exact_branch = 1
            else:
                exact_branch = 0
            merged = pr.get("mergedAt", "")
            return (exact_branch, merged)

        candidates.sort(key=sort_key, reverse=True)
        best = candidates[0]

        return {
            "url": best.get("url"),
            "lines": best.get("additions", 0),
            "author": best.get("author", {}).get("login"),
            "state": "MERGED",
            "merged_at": best.get("mergedAt"),
            "pr_number": best.get("number"),
        }

    except Exception as e:
        print(f"  Error searching for PR: {e}")
        return None


def _check_open_prs(slug: str) -> dict | None:
    """Check for OPEN PRs as info (not for stats, just tracking)."""
    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                "carsdotcom/di-websites-platform",
                "--state",
                "open",
                "--search",
                f"{slug} in:title",
                "--json",
                "url,title,headRefName,author,state,number",
                "--limit",
                "5",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )

        if result.returncode != 0:
            return None

        prs = json.loads(result.stdout)
        for pr in prs:
            if is_valid_sbm_pr(slug, pr.get("title", ""), pr.get("headRefName", "")):
                return {
                    "url": pr.get("url"),
                    "lines": 0,  # Don't count lines for open PRs
                    "author": pr.get("author", {}).get("login"),
                    "state": "OPEN",
                    "merged_at": None,
                    "pr_number": pr.get("number"),
                }
        return None
    except Exception:
        return None


def update_firebase_run(user_id: str, run_key: str, updates: dict) -> bool:
    try:
        db = get_firebase_db()
        run_ref = db.reference(f"/users/{user_id}/runs/{run_key}")
        run_ref.update(updates)
        return True
    except Exception as e:
        print(f"  Error updating Firebase: {e}")
        return False


def should_process_run(run: dict, reprocess_incomplete: bool, add_merged_at: bool) -> bool:
    """Determine if a run needs processing."""
    if add_merged_at:
        # Only process MERGED runs that are missing merged_at
        pr_state = run.get("pr_state", "")
        if pr_state == "MERGED" and not run.get("merged_at"):
            return True
        return False
    if reprocess_incomplete:
        # Only process runs that are incomplete or have non-MERGED state
        pr_state = run.get("pr_state", "")
        if pr_state == "MERGED":
            return False  # Already complete
        if not run.get("pr_url"):
            return True  # Missing PR data
        if pr_state in ("OPEN", "CLOSED", ""):
            return True  # Needs update
        return False
    return True  # Process all


def main():
    parser = argparse.ArgumentParser(description="Backfill & Clean Firebase Stats")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of SLUGS")
    parser.add_argument("--force", action="store_true", help="Force update all fields")
    parser.add_argument(
        "--reprocess-incomplete",
        action="store_true",
        help="Only reprocess runs with missing/incomplete PR data",
    )
    parser.add_argument(
        "--add-merged-at",
        action="store_true",
        help="Only fill in merged_at for MERGED runs missing it",
    )
    args = parser.parse_args()

    if not is_firebase_available():
        print("Error: Firebase not available")
        sys.exit(1)

    print("Fetching all runs from Firebase...")
    db = get_firebase_db()
    users_ref = db.reference("/users")
    users_data = users_ref.get() or {}

    slug_groups = defaultdict(list)

    # Track questionable items for summary
    questionable = []

    # Garbage slugs to mark invalid
    garbage_patterns = ["added", "update", "test", "auto", "migrate", "adding", "dealertheme"]

    # 1. Group Runs
    for user_id, user_data in users_data.items():
        if not isinstance(user_data, dict):
            continue
        runs = user_data.get("runs", {})

        for run_key, run in runs.items():
            if run.get("status") not in ("success", "needs_review"):
                continue

            slug = run.get("slug", "")
            if not slug:
                continue

            # Check if we should process this run
            if not should_process_run(run, args.reprocess_incomplete, args.add_merged_at):
                continue

            slug_groups[slug].append(
                {
                    "user_id": user_id,
                    "run_key": run_key,
                    "data": run,
                    "timestamp": run.get("timestamp", ""),
                }
            )

    # Sort runs within each slug group (Newest First)
    for slug in slug_groups:
        slug_groups[slug].sort(key=lambda x: x["timestamp"], reverse=True)

    slugs_to_process = sorted(list(slug_groups.keys()))
    if args.limit:
        slugs_to_process = slugs_to_process[: args.limit]

    print(f"\nProcessing {len(slugs_to_process)} unique slugs...")
    updates_made = 0
    pr_cache = {}

    for i, slug in enumerate(slugs_to_process, 1):
        runs = slug_groups[slug]

        # --- PATH A: GARBAGE SLUGS ---
        if slug.lower() in garbage_patterns or slug.isdigit() or slug.startswith("["):
            print(f"\n[{i}/{len(slugs_to_process)}] Slug: {slug} (INVALID - marking)")
            for run_info in runs:
                updates = {"status": "invalid"}
                if not args.dry_run:
                    update_firebase_run(run_info["user_id"], run_info["run_key"], updates)
                updates_made += 1
            continue

        # --- PATH B: VALID SLUGS ---
        print(f"\n[{i}/{len(slugs_to_process)}] Slug: {slug} ({len(runs)} runs)")

        # Get PR Data (cached)
        if slug in pr_cache:
            pr_data = pr_cache[slug]
        else:
            print(f"  Searching for MERGED PR...")
            pr_data = get_pr_details_for_slug(slug)
            pr_cache[slug] = pr_data

        if pr_data:
            state = pr_data.get("state", "UNKNOWN")
            if state == "MERGED":
                print(
                    f"  ✅ MERGED: {pr_data['url']} (+{pr_data['lines']} lines) by {pr_data['author']}"
                )
            elif state == "OPEN":
                print(f"  ⚠️ OPEN (not merged): {pr_data['url']} by {pr_data['author']}")
                questionable.append({"slug": slug, "reason": "OPEN PR only", "pr": pr_data["url"]})
        else:
            print(f"  ❌ No MERGED/OPEN SBM PR found")
            questionable.append({"slug": slug, "reason": "No PR found", "pr": None})

        # Apply Updates to Runs
        for idx, run_info in enumerate(runs):
            run = run_info["data"]
            updates = {}

            if pr_data:
                # Always update PR context
                if pr_data.get("url") and (args.force or not run.get("pr_url")):
                    updates["pr_url"] = pr_data["url"]
                if pr_data.get("author") and (args.force or not run.get("pr_author")):
                    updates["pr_author"] = pr_data["author"]
                if pr_data.get("state") and (args.force or not run.get("pr_state")):
                    updates["pr_state"] = pr_data["state"]
                if pr_data.get("merged_at") and (args.force or not run.get("merged_at")):
                    updates["merged_at"] = pr_data["merged_at"]
                if pr_data.get("pr_number") and (args.force or not run.get("pr_number")):
                    updates["pr_number"] = pr_data["pr_number"]

                # If PR is OPEN (not merged), mark run for review
                if pr_data.get("state") == "OPEN":
                    updates["status"] = "needs_review"

            else:
                # No PR found - mark as needs_review
                updates["status"] = "needs_review"

            # Line counting: LATEST run gets lines, older runs get 0
            is_latest = idx == 0
            current_lines = run.get("lines_migrated", 0)
            pr_lines = pr_data.get("lines", 0) if pr_data else 0

            if is_latest and pr_data and pr_data.get("state") == "MERGED":
                if pr_lines > 0 and (args.force or current_lines == 0):
                    updates["lines_migrated"] = pr_lines
                    print(f"  -> Run {run_info['run_key'][-6:]}: lines={pr_lines}")
            elif not is_latest and current_lines > 0:
                updates["lines_migrated"] = 0
                print(f"  -> Run {run_info['run_key'][-6:]}: lines=0 (older duplicate)")

            if updates:
                if args.dry_run:
                    print(f"  [DRY RUN] Would update: {list(updates.keys())}")
                else:
                    update_firebase_run(run_info["user_id"], run_info["run_key"], updates)
                updates_made += 1

    # Print summary
    print(f"\n{'=' * 60}")
    print(f"{'[DRY RUN] ' if args.dry_run else ''}Complete. {updates_made} updates made.")

    if questionable:
        print(f"\n⚠️ QUESTIONABLE ITEMS ({len(questionable)}):")
        for item in questionable:
            print(f"  - {item['slug']}: {item['reason']}")
            if item["pr"]:
                print(f"    PR: {item['pr']}")


if __name__ == "__main__":
    main()
