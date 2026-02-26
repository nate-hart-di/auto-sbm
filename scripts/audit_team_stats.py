import os
import sys

import firebase_admin
from firebase_admin import credentials, db

# Setup env
sys.path.append(os.getcwd())
try:
    from dotenv import load_dotenv

    load_dotenv()
    from sbm.config import get_settings
except ImportError:
    # Fallback if sbm module path issues
    sys.path.append(os.path.join(os.getcwd(), "sbm"))
    from sbm.config import get_settings


def audit():
    print("Initializing audit...")
    # Init Firebase (check if already init)
    try:
        app = firebase_admin.get_app()
    except ValueError:
        settings = get_settings()
        if not settings.firebase.credentials_path or not settings.firebase.database_url:
            print("Error: Firebase credentials not found in env.")
            return
        cred = credentials.Certificate(settings.firebase.credentials_path)
        firebase_admin.initialize_app(cred, {"databaseURL": settings.firebase.database_url})

    print("Fetching data...")
    ref = db.reference("users")
    users_data = ref.get()

    if not users_data:
        print("No data found in Firebase.")
        return

    print("\nAUDIT RESULTS (Strict Criteria: Success, Lines > 0, Has PR URL)")
    print(f"{'User':<30} | {'Total Runs':<10} | {'Strict Count':<12} | {'Strict Lines':<12}")
    print("-" * 75)

    global_verified_slugs = set()
    total_strict_lines_sum = 0

    user_counts = []

    for user_id, data in users_data.items():
        if not isinstance(data, dict):
            continue
        runs = data.get("runs", {})

        # Set for this user to dedupe re-runs of same slug
        user_valid_slugs = set()
        user_valid_lines = 0

        # Parse runs
        # Ensure runs is dict
        if isinstance(runs, list):
            # Should be dict but handle list just in case
            run_items = enumerate(runs)
        else:
            run_items = runs.items()

        for _, run in run_items:
            if not isinstance(run, dict):
                continue

            # CRITERIA 1: Status Success
            if run.get("status") != "success":
                continue

            # CRITERIA 2: Lines > 0
            lines = run.get("lines_migrated", 0)
            if not isinstance(lines, (int, float)) or lines <= 0:
                continue

            # CRITERIA 3: Has PR URL
            pr_url = run.get("pr_url")
            # Check for valid URL string
            if not pr_url or not isinstance(pr_url, str) or "github.com" not in pr_url:
                # Also accept if command is backfill_recovery (since we just verified those via script)
                # But wait, user said "Verified... that have a real PR".
                # My backfill script ADDS pr_url. So it should PASS this.
                # If command is 'backfill_recovery' AND pr_url is present, it's good.
                continue

            # CRITERIA 4: Slug exists
            slug = run.get("slug")
            if not slug:
                continue

            # Deduping Logic:
            # If user ran same slug twice, and both valid, usually we take latest.
            # But for "Sites Migrated", it's distinct slugs.
            # So we just add to set.
            # For Lines? We should sum lines of DISTINCT slugs. (Take max? Or Latest?)
            # SBM Stats logic sums lines of ALL successful runs (even duplicates?)
            # No, `get_migration_stats` does: `runs_by_slug[slug] = run`. So it takes LATEST per slug.
            # We will replicate that strict logic.

            # If checking duplicates, we need to store runs by slug first then sum.

        # Second Pass: Select Latest Valid Run per Slug
        valid_runs_by_slug = {}
        for _, run in run_items:
            if not isinstance(run, dict):
                continue
            slug = run.get("slug")
            if not slug:
                continue

            # Check validity
            lines = run.get("lines_migrated", 0)
            pr_url = run.get("pr_url")
            status = run.get("status")

            is_valid = (status == "success") and (lines > 0) and (pr_url and "github.com" in pr_url)

            if is_valid:
                # Overwrite (assuming order is chronological or don't care, just need ONE valid one)
                # Actually firebase dict keys are sorted by push ID (chronological).
                valid_runs_by_slug[slug] = run

        # Now sum
        count = len(valid_runs_by_slug)
        u_lines = sum(r.get("lines_migrated", 0) for r in valid_runs_by_slug.values())

        user_valid_slugs.update(valid_runs_by_slug.keys())
        global_verified_slugs.update(valid_runs_by_slug.keys())

        total_strict_lines_sum += u_lines

        print(f"{user_id:<30} | {len(runs):<10} | {count:<12} | {u_lines:<12,}")

    print("-" * 75)
    print("Total Runs (Raw DB count): variable")
    print(f"Global Unique Verified Sites: {len(global_verified_slugs)}")
    print(f"Global Verified Lines: {total_strict_lines_sum:,}")


if __name__ == "__main__":
    audit()
