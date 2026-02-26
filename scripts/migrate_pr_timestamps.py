#!/usr/bin/env python3
"""
One-time migration script to fix PR timestamps in Firebase.

Fetches all existing runs with pr_url, queries GitHub for accurate timestamps
(created_at, merged_at, closed_at), and updates Firebase with the new fields.

Usage:
    python scripts/migrate_pr_timestamps.py --dry-run  # Preview changes
    python scripts/migrate_pr_timestamps.py            # Execute migration
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

from rich.console import Console
from rich.progress import track

from sbm.utils.firebase_sync import get_firebase_db, is_firebase_available

console = Console()


def get_pr_timestamps(pr_url: str, max_retries: int = 3) -> dict | None:
    """
    Fetch PR timestamps from GitHub using gh CLI with retry logic.

    Args:
        pr_url: GitHub PR URL
        max_retries: Maximum retry attempts for transient failures

    Returns dict with createdAt, mergedAt, closedAt, state or None if error.
    """
    for attempt in range(max_retries):
        try:
            # Rate limiting: sleep between requests to avoid hitting API limits
            # GitHub API allows ~5000 req/hr, so 0.5s = ~7200/hr buffer
            if attempt > 0:
                # Exponential backoff on retries: 2s, 4s, 8s
                backoff = 2**attempt
                console.print(f"[dim]Retry {attempt}/{max_retries} after {backoff}s...[/dim]")
                time.sleep(backoff)
            else:
                # Rate limit all requests
                time.sleep(0.5)

            result = subprocess.run(
                ["gh", "pr", "view", pr_url, "--json", "createdAt,mergedAt,closedAt,state"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            data = json.loads(result.stdout)

            # Validate timestamp format (ISO 8601)
            def validate_timestamp(ts: str | None) -> str | None:
                if not ts:
                    return None
                # Basic validation: check if it looks like ISO format
                if len(ts) >= 19 and "T" in ts:
                    return ts
                console.print(f"[yellow]Warning: Invalid timestamp format: {ts}[/yellow]")
                return None

            return {
                "created_at": validate_timestamp(data.get("createdAt")),
                "merged_at": validate_timestamp(data.get("mergedAt")),
                "closed_at": validate_timestamp(data.get("closedAt")),
                "state": data.get("state"),  # OPEN, CLOSED, MERGED
            }
        except subprocess.TimeoutExpired:
            if attempt == max_retries - 1:
                console.print(
                    f"[yellow]Timeout fetching {pr_url} after {max_retries} attempts[/yellow]"
                )
                return None
            continue
        except subprocess.CalledProcessError as e:
            # Don't retry on 404 (PR not found) or auth errors
            if "404" in str(e.stderr) or "authentication" in str(e.stderr).lower():
                console.print(f"[yellow]Permanent error for {pr_url}: {e.stderr}[/yellow]")
                return None
            if attempt == max_retries - 1:
                console.print(
                    f"[yellow]Error fetching {pr_url} after {max_retries} attempts: {e.stderr}[/yellow]"
                )
                return None
            continue
        except Exception as e:
            if attempt == max_retries - 1:
                console.print(f"[red]Unexpected error for {pr_url}: {e}[/red]")
                return None
            continue

    return None


def get_all_runs_with_prs() -> list[tuple[str, str, dict]]:
    """
    Fetch all runs from Firebase that have pr_url.

    Returns list of (user_id, run_id, run_data) tuples.
    """
    db = get_firebase_db()
    users_ref = db.reference("/users")
    users_data = users_ref.get() or {}

    runs_with_prs = []

    for user_id, user_data in users_data.items():
        if not isinstance(user_data, dict):
            continue

        runs = user_data.get("runs", {})
        for run_id, run_data in runs.items():
            if not isinstance(run_data, dict):
                continue

            pr_url = run_data.get("pr_url")
            if pr_url:
                runs_with_prs.append((user_id, run_id, run_data))

    return runs_with_prs


def update_run_timestamps(user_id: str, run_id: str, timestamps: dict) -> bool:
    """
    Update a specific run in Firebase with new timestamp fields.

    Args:
        user_id: Firebase user ID
        run_id: Firebase run ID
        timestamps: Dict with created_at, merged_at, closed_at, state

    Returns:
        True if update successful, False otherwise
    """
    try:
        from datetime import datetime

        db = get_firebase_db()
        run_ref = db.reference(f"/users/{user_id}/runs/{run_id}")

        # Update timestamp fields and also standardize the "timestamp" field
        # Use same fallback logic as backfill_from_github_prs.py for consistency
        timestamp_value = (
            timestamps["merged_at"] or timestamps["created_at"] or datetime.now().isoformat() + "Z"
        )

        update_data = {
            "created_at": timestamps["created_at"],
            "merged_at": timestamps["merged_at"],
            "closed_at": timestamps["closed_at"],
            "pr_state": timestamps["state"],  # Update pr_state to current state
            "timestamp": timestamp_value,  # Standardize timestamp field for consistency
        }

        # Remove None values except for timestamp (which always has fallback)
        update_data = {k: v for k, v in update_data.items() if v is not None or k == "timestamp"}

        run_ref.update(update_data)
        return True
    except Exception as e:
        console.print(f"[red]Error updating run {run_id}: {e}[/red]")
        return False


def main():
    parser = argparse.ArgumentParser(description="Migrate PR timestamps in Firebase")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    args = parser.parse_args()

    if not is_firebase_available():
        console.print("[red]Error: Firebase not available[/red]")
        sys.exit(1)

    console.print("[bold blue]Fetching all runs with PR URLs from Firebase...[/bold blue]")
    runs = get_all_runs_with_prs()
    console.print(f"Found {len(runs)} runs with PR URLs\n")

    if not runs:
        console.print("[yellow]No runs with PR URLs found.[/yellow]")
        return

    # Preview mode - show what would be updated
    if args.dry_run:
        console.print("[bold yellow]=== DRY RUN MODE ===[/bold yellow]")
        console.print("Fetching timestamps for first 10 runs as preview...\n")

        preview_runs = runs[:10]
        for user_id, run_id, run_data in preview_runs:
            pr_url = run_data.get("pr_url")
            slug = run_data.get("slug", "unknown")

            console.print(f"[cyan]{slug}[/cyan] ({user_id})")
            console.print(f"  PR: {pr_url}")

            timestamps = get_pr_timestamps(pr_url)
            if timestamps:
                console.print(f"  [green]✓[/green] created_at: {timestamps['created_at']}")
                console.print(f"  [green]✓[/green] merged_at:  {timestamps['merged_at']}")
                console.print(f"  [green]✓[/green] closed_at:  {timestamps['closed_at']}")
                console.print(f"  [green]✓[/green] state:      {timestamps['state']}")
            else:
                console.print("  [red]✗[/red] Failed to fetch timestamps")
            console.print()

        console.print(f"[yellow]DRY RUN: Would update {len(runs)} runs total.[/yellow]")
        return

    # Confirm before proceeding
    console.print(f"[bold]Ready to update {len(runs)} runs with accurate PR timestamps.[/bold]")
    confirm = console.input("\n[yellow]Proceed with migration? (yes/no):[/yellow] ")

    if confirm.lower() != "yes":
        console.print("[yellow]Aborted.[/yellow]")
        return

    # Execute migration
    console.print("\n[bold blue]Starting migration...[/bold blue]\n")

    updated = 0
    errors = 0

    for user_id, run_id, run_data in track(runs, description="Migrating runs"):
        pr_url = run_data.get("pr_url")

        # Always fetch from GitHub to ensure complete and accurate data
        # Don't skip runs with existing timestamps - we want to validate everything
        timestamps = get_pr_timestamps(pr_url)
        if not timestamps:
            errors += 1
            continue

        # Update Firebase with validated GitHub data
        if update_run_timestamps(user_id, run_id, timestamps):
            updated += 1
        else:
            errors += 1

    # Summary
    console.print("\n[bold green]Migration Complete![/bold green]")
    console.print(f"Updated:  {updated}")
    console.print(f"Errors:   {errors}")
    console.print(
        "\n[dim]All runs validated against GitHub. Both created_at and merged_at tracked when available.[/dim]"
    )


if __name__ == "__main__":
    main()
