#!/usr/bin/env python3
"""
Backfill Firebase from merged SBM PRs found on GitHub.

Searches for all merged PRs matching SBM patterns and creates runs
for any that aren't already tracked in Firebase.

Usage:
    python scripts/backfill_from_github_prs.py --dry-run
    python scripts/backfill_from_github_prs.py
"""

import argparse
import json
import logging
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT))

from sbm.utils.firebase_sync import get_firebase_db, is_firebase_available


# Valid SBM PR title patterns
SBM_TITLE_PATTERNS = [
    r"^(.+?)\s*-\s*SBM FE Audit",  # "slug - SBM FE Audit"
    r"^PCON-\d+:\s*(.+?)\s+SBM",  # "PCON-727: slug SBM FE Audit"
    r"^SBM:\s*Migrate\s+(.+?)\s+to",  # "SBM: Migrate slug to Site Builder"
    r"^\[(.+?)\]\s*-\s*Site Builder",  # "[slug] - Site Builder Migration"
    r"^(.+?)\s*-\s*Site Builder Migration",  # "slug - Site Builder Migration"
    r"^(.+?)\s+SBM Migration",  # "slug SBM Migration"
]


def extract_slug_from_title(title: str) -> str | None:
    """Extract the dealer slug from a valid SBM PR title."""
    for pattern in SBM_TITLE_PATTERNS:
        match = re.match(pattern, title, re.IGNORECASE)
        if match:
            slug = match.group(1).strip().lower()
            # Clean up common prefixes
            slug = re.sub(r"^pcon-\d+-", "", slug)
            return slug
    return None


def extract_slug_from_branch(branch: str) -> str | None:
    """Extract slug from SBM branch patterns."""
    branch_lower = branch.lower()

    # "pcon-727-{slug}-sbm{mmyy}"
    match = re.match(r"^pcon-\d+-(.+?)-sbm\d{4}$", branch_lower)
    if match:
        return match.group(1)

    # "{slug}-sbm{mmyy}"
    match = re.match(r"^(.+?)-sbm\d{4}$", branch_lower)
    if match:
        return match.group(1)

    # "sbm/{slug}"
    if branch_lower.startswith("sbm/"):
        return branch_lower[4:]

    return None


def get_all_sbm_prs() -> list[dict]:
    """Fetch all merged SBM PRs from GitHub."""
    all_prs = []

    # Search queries for different SBM title patterns
    search_queries = [
        '"SBM FE Audit" in:title',
        '"SBM: Migrate" in:title',
        '"Site Builder Migration" in:title',
        '"SBM Migration" in:title',
    ]

    for query in search_queries:
        print(f"  Searching: {query}...")
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
                    "url,title,headRefName,additions,author,createdAt,mergedAt,closedAt,state,number",
                    "--limit",
                    "500",
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
            print(f"    Error: {e}")

    # Deduplicate by PR number
    seen = set()
    unique_prs = []
    for pr in all_prs:
        pr_num = pr.get("number")
        if pr_num and pr_num not in seen:
            seen.add(pr_num)
            unique_prs.append(pr)

    return unique_prs


def get_existing_slugs() -> set[str]:
    """Get all slugs already in Firebase."""
    db = get_firebase_db()
    users_ref = db.reference("/users")
    users_data = users_ref.get() or {}

    slugs = set()
    for user_id, user_data in users_data.items():
        if not isinstance(user_data, dict):
            continue
        runs = user_data.get("runs", {})
        for run in runs.values():
            slug = run.get("slug", "").lower()
            if slug:
                slugs.add(slug)

    return slugs


def main():
    parser = argparse.ArgumentParser(description="Backfill Firebase from GitHub PRs")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    # Setup error logging
    log_file = REPO_ROOT / "logs" / f"backfill_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_file.parent.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logging.info(f"Backfill started. Log file: {log_file}")

    if not is_firebase_available():
        logging.error("Firebase not available")
        print("Error: Firebase not available")
        sys.exit(1)

    print("Fetching merged SBM PRs from GitHub...")
    all_prs = get_all_sbm_prs()
    print(f"Found {len(all_prs)} merged SBM PRs\n")

    print("Fetching existing slugs from Firebase...")
    existing_slugs = get_existing_slugs()
    print(f"Found {len(existing_slugs)} existing slugs\n")

    # Process PRs and extract slugs
    missing_runs = []
    for pr in all_prs:
        title = pr.get("title", "")
        branch = pr.get("headRefName", "")

        # Try to extract slug from title first, then branch
        slug = extract_slug_from_title(title) or extract_slug_from_branch(branch)

        if not slug:
            continue

        if slug.lower() not in existing_slugs:
            missing_runs.append(
                {
                    "slug": slug,
                    "pr_url": pr.get("url"),
                    "pr_number": pr.get("number"),
                    "lines": pr.get("additions", 0),
                    "author": pr.get("author", {}).get("login"),
                    "created_at": pr.get("createdAt"),
                    "merged_at": pr.get("mergedAt"),
                    "closed_at": pr.get("closedAt"),
                    "state": pr.get("state"),
                    "title": title,
                }
            )

    print(f"Found {len(missing_runs)} PRs not yet tracked in Firebase\n")

    if not missing_runs:
        print("Everything is already tracked!")
        return

    # Show what would be added
    print("=== PRs to backfill ===")
    for run in missing_runs[:20]:
        print(f"  {run['slug']}: PR #{run['pr_number']} (+{run['lines']} lines) by {run['author']}")

    if len(missing_runs) > 20:
        print(f"  ... and {len(missing_runs) - 20} more")

    if args.dry_run:
        print(f"\n[DRY RUN] Would add {len(missing_runs)} runs to Firebase.")
        return

    # Confirm before adding
    confirm = input(f"\nAdd {len(missing_runs)} runs to Firebase? (yes/no): ")
    if confirm.lower() != "yes":
        print("Aborted.")
        return

    # Add runs to Firebase
    print("\nAdding runs to Firebase...")
    db = get_firebase_db()
    added = 0
    errors = 0

    for run_info in missing_runs:
        try:
            # Use the author as the user ID
            user_id = run_info["author"] or "unknown"
            user_ref = db.reference(f"/users/{user_id}/runs")

            # Create run entry
            run_entry = {
                "slug": run_info["slug"],
                "timestamp": run_info["merged_at"] or run_info["created_at"] or datetime.now().isoformat() + "Z",
                "command": "auto",
                "status": "success",
                "lines_migrated": run_info["lines"],
                "pr_url": run_info["pr_url"],
                "pr_author": run_info["author"],
                "pr_state": run_info.get("state", "MERGED"),
                "created_at": run_info.get("created_at"),
                "merged_at": run_info.get("merged_at"),
                "closed_at": run_info.get("closed_at"),
                "historical": True,
                "source": "github_backfill",
                "duration_seconds": 300.0,
                "automation_seconds": 60.0,
                "manual_estimate_seconds": 14400,
            }

            user_ref.push(run_entry)
            added += 1

            if added % 10 == 0:
                print(f"  Added {added}/{len(missing_runs)}...")

        except Exception as e:
            error_msg = f"Error adding {run_info['slug']}: {e}"
            print(f"  {error_msg}")
            logging.error(error_msg, exc_info=True)
            errors += 1

    summary = f"Complete! Added {added} runs, {errors} errors."
    print(f"\n{summary}")
    logging.info(summary)
    if errors > 0:
        logging.warning(f"Backfill completed with {errors} errors. Check log for details: {log_file}")


if __name__ == "__main__":
    main()
