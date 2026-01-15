#!/usr/bin/env python3
"""
Verify Firebase data quality and completeness.

Checks:
1. All runs have valid slugs (not garbage)
2. All MERGED runs have: pr_url, pr_author, lines_migrated, merged_at
3. No duplicate line counts for same slug
4. Status is consistent (success, needs_review, invalid)
5. Prints detailed report of issues

Usage:
    python scripts/verify_firebase_data.py
    python scripts/verify_firebase_data.py --fix  # Auto-fix minor issues
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT))

from sbm.utils.firebase_sync import get_firebase_db, is_firebase_available


def is_valid_slug(slug: str) -> bool:
    """Check if slug looks like a valid dealer slug."""
    if not slug or len(slug) < 4:
        return False
    if slug.isdigit():
        return False
    if slug.startswith("["):
        return False
    garbage = {"added", "adding", "update", "test", "dealertheme", "auto", "migrate", "sbm"}
    if slug.lower() in garbage:
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Verify Firebase data quality")
    parser.add_argument("--fix", action="store_true", help="Auto-fix minor issues")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all details")
    args = parser.parse_args()

    if not is_firebase_available():
        print("Error: Firebase not available")
        sys.exit(1)

    print("Loading Firebase data...")
    db = get_firebase_db()
    users_ref = db.reference("/users")
    users_data = users_ref.get() or {}

    # Collect all runs
    all_runs = []
    for user_id, user_data in users_data.items():
        if not isinstance(user_data, dict):
            continue
        runs = user_data.get("runs", {})
        for run_key, run in runs.items():
            run["_user_id"] = user_id
            run["_run_key"] = run_key
            all_runs.append(run)

    print(f"Total runs: {len(all_runs)}\n")

    # Issue trackers
    issues = {
        "invalid_slug": [],
        "missing_pr_url": [],
        "missing_pr_author": [],
        "missing_lines": [],
        "missing_merged_at": [],
        "closed_pr_state": [],
        "open_pr_state": [],
        "duplicate_lines": [],
        "invalid_status": [],
    }

    # Stats
    stats = {
        "total": len(all_runs),
        "success": 0,
        "needs_review": 0,
        "invalid": 0,
        "failed": 0,
        "merged_prs": 0,
        "open_prs": 0,
        "closed_prs": 0,
        "total_lines": 0,
    }

    # Track lines per slug to find duplicates
    slug_lines = defaultdict(list)

    for run in all_runs:
        slug = run.get("slug", "")
        status = run.get("status", "")
        pr_state = run.get("pr_state", "")

        # Count statuses
        if status == "success":
            stats["success"] += 1
        elif status == "needs_review":
            stats["needs_review"] += 1
        elif status == "invalid":
            stats["invalid"] += 1
        elif status == "failed":
            stats["failed"] += 1
        else:
            issues["invalid_status"].append(run)

        # Skip invalid/failed runs for quality checks
        if status in ("invalid", "failed"):
            continue

        # Check slug validity
        if not is_valid_slug(slug):
            issues["invalid_slug"].append(run)
            continue

        # Check PR state
        if pr_state == "MERGED":
            stats["merged_prs"] += 1
        elif pr_state == "OPEN":
            stats["open_prs"] += 1
            issues["open_pr_state"].append(run)
        elif pr_state == "CLOSED":
            stats["closed_prs"] += 1
            issues["closed_pr_state"].append(run)

        # Check for missing fields (only for success runs)
        if status == "success":
            if not run.get("pr_url"):
                issues["missing_pr_url"].append(run)
            if not run.get("pr_author"):
                issues["missing_pr_author"].append(run)
            if pr_state == "MERGED" and not run.get("merged_at"):
                issues["missing_merged_at"].append(run)

            lines = run.get("lines_migrated", 0)
            if lines <= 0 and pr_state == "MERGED":
                issues["missing_lines"].append(run)
            elif lines > 0:
                slug_lines[slug].append(
                    {
                        "run": run,
                        "lines": lines,
                        "timestamp": run.get("timestamp", ""),
                    }
                )
                stats["total_lines"] += lines

    # Check for duplicate line counts
    for slug, runs_with_lines in slug_lines.items():
        if len(runs_with_lines) > 1:
            # Only the latest should have lines
            sorted_runs = sorted(runs_with_lines, key=lambda x: x["timestamp"], reverse=True)
            for run_info in sorted_runs[1:]:  # All except latest
                if run_info["lines"] > 0:
                    issues["duplicate_lines"].append(run_info["run"])

    # Print report
    print("=" * 60)
    print("FIREBASE DATA QUALITY REPORT")
    print("=" * 60)

    print("\n📊 SUMMARY:")
    print(f"  Total runs:      {stats['total']}")
    print(f"  Success:         {stats['success']}")
    print(f"  Needs Review:    {stats['needs_review']}")
    print(f"  Invalid:         {stats['invalid']}")
    print(f"  Failed:          {stats['failed']}")
    print(f"  MERGED PRs:      {stats['merged_prs']}")
    print(f"  OPEN PRs:        {stats['open_prs']}")
    print(f"  CLOSED PRs:      {stats['closed_prs']}")
    print(f"  Total Lines:     {stats['total_lines']:,}")

    print("\n🔍 ISSUES FOUND:")
    total_issues = 0
    for issue_type, runs in issues.items():
        count = len(runs)
        total_issues += count
        if count > 0:
            label = issue_type.replace("_", " ").title()
            print(f"  {label}: {count}")
            if args.verbose and runs:
                for run in runs[:5]:
                    print(f"    - {run.get('slug', 'N/A')} ({run['_user_id'][:10]}...)")
                if len(runs) > 5:
                    print(f"    ... and {len(runs) - 5} more")

    if total_issues == 0:
        print("  ✅ No issues found! Data is clean.")
    else:
        print(f"\n  Total issues: {total_issues}")

    # Detailed breakdown of issues
    if args.verbose:
        print("\n" + "=" * 60)
        print("DETAILED ISSUES")
        print("=" * 60)

        if issues["open_pr_state"] or issues["closed_pr_state"]:
            print("\n⚠️ Runs needing attention:")
            for run in issues["open_pr_state"][:10]:
                print(f"  • {run.get('slug')} - OPEN PR: {run.get('pr_url', 'N/A')}")

        if issues["closed_pr_state"]:
            print("\n❌ Runs with CLOSED PRs (should be removed or reviewed):")
            for run in issues["closed_pr_state"][:10]:
                print(f"  • {run.get('slug')} - {run.get('pr_url', 'N/A')}")

    # Fix mode
    if args.fix and total_issues > 0:
        print("\n" + "=" * 60)
        print("AUTO-FIX MODE")
        print("=" * 60)

        fixes_made = 0

        # Fix: Mark invalid slugs as invalid status
        for run in issues["invalid_slug"]:
            if run.get("status") != "invalid":
                ref = db.reference(f"/users/{run['_user_id']}/runs/{run['_run_key']}")
                ref.update({"status": "invalid"})
                fixes_made += 1
                print(f"  Fixed: {run.get('slug')} -> status=invalid")

        # Fix: Zero out duplicate line counts
        for run in issues["duplicate_lines"]:
            ref = db.reference(f"/users/{run['_user_id']}/runs/{run['_run_key']}")
            ref.update({"lines_migrated": 0})
            fixes_made += 1
            print(f"  Fixed: {run.get('slug')} -> lines_migrated=0 (duplicate)")

        # Fix: Mark CLOSED PRs as needs_review
        for run in issues["closed_pr_state"]:
            if run.get("status") == "success":
                ref = db.reference(f"/users/{run['_user_id']}/runs/{run['_run_key']}")
                ref.update({"status": "needs_review"})
                fixes_made += 1
                print(f"  Fixed: {run.get('slug')} -> status=needs_review (CLOSED PR)")

        print(f"\n✅ Applied {fixes_made} fixes")

    print("\n" + "=" * 60)
    if total_issues > 0:
        print("Run with --fix to auto-fix issues, or use backfill script.")
    print("Done.")


if __name__ == "__main__":
    main()
