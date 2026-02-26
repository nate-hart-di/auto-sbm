#!/usr/bin/env python3
"""
Daily PR status update script.

Updates PR timestamps for all in-progress runs in Firebase.
This catches PRs that were merged or closed since last check.

Usage:
    python scripts/update_pr_statuses.py              # Update all in-progress PRs
    python scripts/update_pr_statuses.py --all        # Force refresh all PRs
    python scripts/update_pr_statuses.py --dry-run    # Preview changes only

Schedule this to run daily before the Slack notification:
    crontab -e
    0 7 * * * cd /path/to/auto-sbm && source .venv/bin/activate && python scripts/update_pr_statuses.py
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT))

from rich.console import Console
from rich.progress import track

from sbm.utils.firebase_sync import get_firebase_db, is_firebase_available
from sbm.utils.github_pr import GitHubPRManager

console = Console()


def get_runs_needing_update(force_all: bool = False) -> list[tuple[str, str, dict]]:
    """
    Fetch runs from Firebase that need PR status updates.

    Args:
        force_all: If True, update all runs with PRs. If False, only update in-progress.

    Returns:
        List of (user_id, run_id, run_data) tuples
    """
    db = get_firebase_db()
    users_ref = db.reference("/users")
    users_data = users_ref.get() or {}

    runs_needing_update = []

    for user_id, user_data in users_data.items():
        if not isinstance(user_data, dict):
            continue

        runs = user_data.get("runs", {})
        for run_id, run_data in runs.items():
            if not isinstance(run_data, dict):
                continue

            # Skip runs without PR URLs
            if not run_data.get("pr_url"):
                continue

            # Skip failed/invalid runs
            if run_data.get("status") in {"failed", "invalid"}:
                continue

            # Check if run needs update
            if force_all or GitHubPRManager.should_refresh_pr_data(run_data):
                runs_needing_update.append((user_id, run_id, run_data))

    return runs_needing_update


def update_run_in_firebase(user_id: str, run_id: str, run_data: dict) -> bool:
    """
    Update a run in Firebase with fresh PR metadata.

    Args:
        user_id: Firebase user ID
        run_id: Firebase run ID
        run_data: Run dictionary (will be enriched with fresh PR data)

    Returns:
        True if update successful, False otherwise
    """
    try:
        # Enrich run with fresh PR metadata
        enriched_run = GitHubPRManager.enrich_run_with_pr_data(run_data, force_refresh=True)

        # Update Firebase with new data
        db = get_firebase_db()
        run_ref = db.reference(f"/users/{user_id}/runs/{run_id}")

        # Only update the PR-related fields
        update_data = {
            "created_at": enriched_run.get("created_at"),
            "merged_at": enriched_run.get("merged_at"),
            "closed_at": enriched_run.get("closed_at"),
            "pr_state": enriched_run.get("pr_state"),
            "pr_author": enriched_run.get("pr_author"),
        }

        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if update_data:
            run_ref.update(update_data)
            return True
        return False

    except Exception as e:
        console.print(f"[red]Error updating run {run_id}: {e}[/red]")
        return False


def main():
    parser = argparse.ArgumentParser(description="Update PR statuses in Firebase")
    parser.add_argument(
        "--all", action="store_true", help="Force refresh all PRs (not just in-progress)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    args = parser.parse_args()

    if not is_firebase_available():
        console.print("[red]Error: Firebase not available[/red]")
        sys.exit(1)

    scope = "all PRs" if args.all else "in-progress PRs"
    console.print(f"[bold blue]Fetching {scope} from Firebase...[/bold blue]")

    runs = get_runs_needing_update(force_all=args.all)
    console.print(f"Found {len(runs)} runs needing status updates\n")

    if not runs:
        console.print("[green]✓ All PRs are up to date![/green]")
        return

    # Preview mode
    if args.dry_run:
        console.print("[bold yellow]=== DRY RUN MODE ===[/bold yellow]")
        console.print(f"Would update {len(runs)} runs:\n")

        preview_runs = runs[:10]
        for user_id, run_id, run_data in preview_runs:
            slug = run_data.get("slug", "unknown")
            pr_url = run_data.get("pr_url")
            current_state = run_data.get("pr_state", "unknown")

            console.print(f"[cyan]{slug}[/cyan] ({user_id})")
            console.print(f"  Current state: {current_state}")
            console.print(f"  PR: {pr_url}\n")

        if len(runs) > 10:
            console.print(f"[dim]... and {len(runs) - 10} more runs[/dim]")

        console.print(f"\n[yellow]DRY RUN: Would update {len(runs)} runs total.[/yellow]")
        return

    # Confirm before proceeding
    console.print(f"[bold]Ready to update {len(runs)} runs with fresh PR statuses.[/bold]")
    confirm = console.input("\n[yellow]Proceed with update? (yes/no):[/yellow] ")

    if confirm.lower() != "yes":
        console.print("[yellow]Aborted.[/yellow]")
        return

    # Execute updates
    console.print("\n[bold blue]Starting updates...[/bold blue]\n")

    updated = 0
    errors = 0

    for user_id, run_id, run_data in track(runs, description="Updating PR statuses"):
        if update_run_in_firebase(user_id, run_id, run_data):
            updated += 1
        else:
            errors += 1

    # Summary
    console.print("\n[bold green]Update Complete![/bold green]")
    console.print(f"Updated:  {updated}")
    console.print(f"Errors:   {errors}")

    if errors == 0:
        console.print("\n[green]✓ All PR statuses are now current![/green]")
    else:
        console.print(f"\n[yellow]⚠ {errors} updates failed. Check logs for details.[/yellow]")


if __name__ == "__main__":
    main()
