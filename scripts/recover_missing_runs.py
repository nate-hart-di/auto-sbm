import json
import subprocess
import sys
from pathlib import Path
from sbm.utils.tracker import get_global_reporting_data, record_run
from rich.console import Console

console = Console()

REPO = "carsdotcom/di-websites-platform"


def get_missing_slugs():
    """Identify slugs in 'migrations' that lack a valid run."""
    runs, migrations = get_global_reporting_data()

    # We focus on the current user's lists for now
    target_user = "nate-hart-di"

    user_mig_list = migrations.get(target_user, set())  # This is a set of slugs

    # Identify valid run slugs
    valid_run_slugs = set()
    for r in runs:
        if r.get("_user") == target_user and r.get("status") == "success":
            valid_run_slugs.add(r.get("slug"))

    missing = user_mig_list - valid_run_slugs
    console.print(f"[bold]Analysis for {target_user}:[/bold]")
    console.print(f"Total in Migrations List: {len(user_mig_list)}")
    console.print(f"Total Valid Runs: {len(valid_run_slugs)}")
    console.print(f"Missing Runs: {len(missing)}")

    return list(missing)


def find_pr(slug):
    """Search GitHub for a merged PR matching the slug, prioritizing current user."""
    queries = [f"head:migrate/{slug}", f"head:{slug}-sbm", f"head:{slug}", f"{slug} in:title"]

    current_user_login = "nate-hart-di"  # Hardcoded for reliability

    candidates = []

    for q in queries:
        cmd = [
            "gh",
            "pr",
            "list",
            "--repo",
            REPO,
            "--state",
            "merged",
            "--search",
            q,
            "--json",
            "url,title,author,mergedAt,additions,deletions,headRefName",
            "--limit",
            "5",
        ]
        try:
            result = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
            data = json.loads(result)
            if data:
                candidates.extend(data)
        except Exception:
            continue

    if not candidates:
        return None

    # Deduplicate by URL
    unique_candidates = {}
    for c in candidates:
        unique_candidates[c["url"]] = c

    candidates = list(unique_candidates.values())

    # Sort/Prioritize
    # 1. Author match
    # 2. Slug in headRefName (exactish)

    def score(pr):
        s = 0
        if pr["author"]["login"] == current_user_login:
            s += 100
        if slug.lower() in pr["headRefName"].lower():
            s += 50
        return s

    best_pr = sorted(candidates, key=score, reverse=True)[0]
    return best_pr


def recover(dry_run=True):
    missing_slugs = get_missing_slugs()

    success_count = 0
    total_lines_recovered = 0

    for i, slug in enumerate(missing_slugs):
        console.print(f"[{i + 1}/{len(missing_slugs)}] Searching for [cyan]{slug}[/cyan]...")
        pr = find_pr(slug)

        if pr:
            console.print(
                f"  [green]Found PR:[/green] {pr['title']} ({pr['url']}) by {pr['author']['login']}"
            )

            # Prepare run data
            lines = pr["additions"]
            author = pr["author"]["login"]
            url = pr["url"]
            state = "MERGED"

            if not dry_run:
                try:
                    record_run(
                        slug=slug,
                        command="backfill_recovery",
                        status="success",
                        duration=0.0,
                        automation_time=0.0,
                        lines_migrated=lines,
                        files_created_count=0,
                        scss_line_count=0,
                        manual_estimate_minutes=0,  # No estimate
                        pr_url=url,
                        pr_author=author,
                        pr_state=state,
                    )
                    console.print("  [blue]Backfilled run to Firebase[/blue]")
                    total_lines_recovered += lines
                    success_count += 1
                except Exception as e:
                    console.print(f"  [red]Failed to write to Firebase: {e}[/red]")
            else:
                console.print(f"  [dim]Would backfill: lines={lines}, author={author}[/dim]")
                total_lines_recovered += lines
                success_count += 1
        else:
            console.print(f"  [red]No PR found[/red]")

    console.print(f"\n[bold]Recovery Complete[/bold]")
    console.print(f"Recovered {success_count} / {len(missing_slugs)} missing runs")
    console.print(f"Total Lines Recovered: {total_lines_recovered}")


if __name__ == "__main__":
    import sys

    dry = "--dry-run" in sys.argv
    recover(dry_run=dry)
