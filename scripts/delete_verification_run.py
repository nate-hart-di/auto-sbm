import logging
import requests
from rich.console import Console
from sbm.utils.firebase_sync import FirebaseSync, get_settings, _get_user_mode_identity

logging.basicConfig(level=logging.DEBUG)
console = Console()


def delete_verification_runs():
    console.print("[bold red]Deleting 'verification-ping' runs...[/bold red]")

    sync = FirebaseSync()
    all_data = sync.fetch_all_users_raw()

    deleted_count = 0

    for user_id, user_data in all_data.items():
        if not isinstance(user_data, dict):
            continue
        runs = user_data.get("runs", {})

        for run_id, run_data in runs.items():
            if run_data.get("slug") == "verification-ping":
                console.print(f"Found verification run: {run_id} (User: {user_id})")

                # DELETE IT
                # We can't use sync.update_run for deletion easily (it's for updates)
                # We'll use raw requests.delete

                settings = get_settings()
                identity = _get_user_mode_identity()
                token = identity[1] if identity else None

                url = f"{settings.firebase.database_url}/users/{user_id}/runs/{run_id}.json"
                if token:
                    url += f"?auth={token}"

                console.print(f"Deleting via {url}...")
                resp = requests.delete(url)

                if resp.ok:
                    console.print("[green]Deleted successfully.[/green]")
                    deleted_count += 1
                else:
                    console.print(f"[red]Failed to delete: {resp.status_code} {resp.text}[/red]")

    console.print(f"Total deleted: {deleted_count}")


if __name__ == "__main__":
    delete_verification_runs()
