#!/usr/bin/env python3
"""
Backfill ALL Firebase runs with correct lines_migrated from GitHub PRs.

This script:
1. Scans ALL Firebase runs that have pr_url field
2. Fetches additions count from each PR URL using gh CLI
3. Updates lines_migrated where it doesn't match GitHub additions

Usage:
    FIREBASE__CREDENTIALS_PATH="/path/to/creds.json" python scripts/backfill_all_lines_migrated.py --dry-run
    FIREBASE__CREDENTIALS_PATH="/path/to/creds.json" python scripts/backfill_all_lines_migrated.py
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT))

from sbm.utils.firebase_sync import get_firebase_db, is_firebase_available


def fetch_pr_additions(pr_url: str) -> int | None:
    """Fetch additions count from a PR URL."""
    try:
        result = subprocess.run(
            ["gh", "pr", "view", pr_url, "--json", "additions"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        data = json.loads(result.stdout)
        return data.get("additions")
    except Exception:
        return None


def scan_and_update_runs(dry_run: bool = False):
    """Scan all Firebase runs and update lines_migrated from GitHub."""
    print("\n[1/2] Scanning Firebase runs...\n")

    db = get_firebase_db()
    users_ref = db.reference("/users")
    users_data = users_ref.get() or {}

    total_runs = 0
    runs_with_pr_url = 0
    runs_needing_update = []

    for user_id, user_node in users_data.items():
        if not isinstance(user_node, dict):
            continue

        runs_node = user_node.get("runs", {})
        for run_key, run in runs_node.items():
            total_runs += 1
            pr_url = run.get("pr_url")

            if not pr_url:
                continue

            runs_with_pr_url += 1
            slug = run.get("slug", "unknown")
            current_lines = run.get("lines_migrated", 0)

            # Fetch from GitHub
            if runs_with_pr_url % 10 == 0:
                print(f"  Fetched {runs_with_pr_url} PR URLs...")

            github_lines = fetch_pr_additions(pr_url)

            if github_lines is not None and current_lines != github_lines:
                runs_needing_update.append(
                    {
                        "user_id": user_id,
                        "run_key": run_key,
                        "slug": slug,
                        "pr_url": pr_url,
                        "current_lines": current_lines,
                        "github_lines": github_lines,
                    }
                )

    print(f"\nTotal runs scanned: {total_runs}")
    print(f"Runs with PR URL: {runs_with_pr_url}")
    print(f"Runs needing update: {len(runs_needing_update)}\n")

    if not runs_needing_update:
        print("✅ All runs already have correct lines_migrated!")
        return

    # Show preview
    print("=== Preview of updates (first 20) ===")
    for i, update in enumerate(runs_needing_update[:20]):
        print(f"  {update['slug']}: {update['current_lines']} → {update['github_lines']}")

    if len(runs_needing_update) > 20:
        print(f"  ... and {len(runs_needing_update) - 20} more\n")

    if dry_run:
        print(f"\n[DRY RUN] Would update {len(runs_needing_update)} runs.")
        return

    # Confirm
    confirm = input(f"\nUpdate {len(runs_needing_update)} runs? (yes/no): ")
    if confirm.lower() != "yes":
        print("Aborted.")
        return

    # Apply updates
    print("\n[2/2] Applying updates...\n")
    updated = 0
    errors = 0

    for update_info in runs_needing_update:
        try:
            ref = db.reference(f"/users/{update_info['user_id']}/runs/{update_info['run_key']}")
            ref.update({"lines_migrated": update_info["github_lines"]})
            updated += 1

            if updated % 25 == 0:
                print(f"  Updated {updated}/{len(runs_needing_update)}...")
        except Exception as e:
            print(f"  Error updating {update_info['slug']}: {e}")
            errors += 1

    print(f"\n✅ Complete! Updated {updated} runs, {errors} errors.")


def main():
    parser = argparse.ArgumentParser(
        description="Backfill ALL Firebase runs with correct lines_migrated from GitHub"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    print("=" * 60)
    print("BACKFILL ALL LINES_MIGRATED FROM GITHUB")
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    if not is_firebase_available():
        print("ERROR: Firebase not available")
        print("\nMake sure to set FIREBASE__CREDENTIALS_PATH:")
        print('  export FIREBASE__CREDENTIALS_PATH="/path/to/credentials.json"')
        sys.exit(1)

    # Scan and update
    scan_and_update_runs(dry_run=args.dry_run)

    print("\n" + "=" * 60)
    print(f"Completed at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
