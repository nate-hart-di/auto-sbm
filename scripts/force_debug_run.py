import logging

from rich.console import Console

from sbm.utils.firebase_sync import FirebaseSync
from sbm.utils.github_pr import GitHubPRManager

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
console = Console()


def debug_run():
    console.print("[bold cyan]Starting Debug for 'newportlexus'...[/bold cyan]")

    sync = FirebaseSync()
    console.print("Fetching all users...")
    all_data = sync.fetch_all_users_raw()

    # Find ALL runs for the slug
    matching_runs = []
    for u_id, u_data in all_data.items():
        if not isinstance(u_data, dict):
            continue
        runs = u_data.get("runs", {})
        for r_id, r_data in runs.items():
            if r_data.get("slug") == "newportlexus":
                matching_runs.append((u_id, r_id, r_data))

    if not matching_runs:
        console.print("[red]Could not find any run for 'newportlexus'[/red]")
        return

    console.print(f"[green]Found {len(matching_runs)} runs![/green]")

    for target_user_id, target_run_id, target_run in matching_runs:
        console.print("\n" + "=" * 50)
        console.print(f"[bold]Checking Run: {target_run_id}[/bold]")
        console.print(f"Timestamp: {target_run.get('timestamp')}")
        console.print(f"Current PR State: {target_run.get('pr_state')}")
        console.print(f"Owner: {target_user_id}")

        # Check if we SHOULD refresh
        should = GitHubPRManager.should_refresh_pr_data(target_run)
        console.print(f"Should Refresh? [bold]{should}[/bold]")

        if should:
            console.print("Attempting to enrich...")
            try:
                enriched = GitHubPRManager.enrich_run_with_pr_data(target_run, force_refresh=True)
                console.print(f"Enriched PR State: {enriched.get('pr_state')}")
                console.print(f"Enriched Merged At: {enriched.get('merged_at')}")

                # Try Update
                console.print("Attempting Firebase Write...")
                update_data = {
                    "created_at": enriched.get("created_at"),
                    "merged_at": enriched.get("merged_at"),
                    "closed_at": enriched.get("closed_at"),
                    "pr_state": enriched.get("pr_state"),
                }
                # Remove None values
                update_data = {k: v for k, v in update_data.items() if v is not None}

                success = sync.update_run(
                    user_id=target_user_id, run_key=target_run_id, updates=update_data
                )
                if success:
                    console.print("[bold green]Firebase Update SUCCESS[/bold green]")
                else:
                    console.print("[bold red]Firebase Update FAILED[/bold red]")
            except Exception as e:
                console.print(f"[red]Enrichment/Update Failed: {e}[/red]")


if __name__ == "__main__":
    debug_run()
