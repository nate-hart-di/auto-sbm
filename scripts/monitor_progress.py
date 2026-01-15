import firebase_admin
from firebase_admin import credentials, db
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbm.config import get_settings


def monitor_progress():
    settings = get_settings()
    user_id = "nate-hart-di"  # Assuming this user, or use CLI arg if generic

    # Slugs from the file
    target_slugs = [
        "boggustiptonchryslerdodgejeepram",
        "daviddodge",
        "iversonautogroup",
        "vallejochryslerdodgejeepram",
        "jerryseinersaltlakekia",
        "jerryseinerkiasouthjordan",
    ]

    print(f"Checking status for {len(target_slugs)} slugs...")

    if settings.firebase.is_admin_mode():
        cred = credentials.Certificate(str(settings.firebase.credentials_path))
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {"databaseURL": settings.firebase.database_url})

        ref = db.reference(f"users/{user_id}/runs")
        # Optimization: Get all runs once, then filter in memory
        # Ideally we'd query by slug, but with random keys, we scan.
        # Since we just cleaned the DB, it should be fast.

        all_runs = ref.get() or {}

        # Build lookup: slug -> list of runs
        runs_map = {}
        for key, r in all_runs.items():
            slug = r.get("slug")
            if slug:
                if slug not in runs_map:
                    runs_map[slug] = []
                runs_map[slug].append(r)

        completed = []
        pending = []

        for slug in target_slugs:
            if slug in runs_map:
                # Check for success
                success_runs = [r for r in runs_map[slug] if r.get("status") == "success"]
                if success_runs:
                    latest = sorted(
                        success_runs, key=lambda x: x.get("timestamp", ""), reverse=True
                    )[0]
                    completed.append((slug, latest.get("timestamp")))
                else:
                    pending.append(slug)
            else:
                pending.append(slug)

        print("\n--- COMPLETED ---")
        for s, ts in completed:
            print(f"[✅] {s} (at {ts})")

        print("\n--- PENDING/NOT FOUND ---")
        for s in pending:
            print(f"[⏳] {s}")

    else:
        print("Admin mode required to check exact DB status.")


if __name__ == "__main__":
    monitor_progress()
