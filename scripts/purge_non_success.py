import firebase_admin
from firebase_admin import credentials, db
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbm.config import get_settings


def purge_non_success():
    settings = get_settings()
    if not settings.firebase.is_admin_mode():
        print("Admin required")
        return

    cred = credentials.Certificate(str(settings.firebase.credentials_path))
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {"databaseURL": settings.firebase.database_url})

    ref = db.reference("users")
    all_users = ref.get() or {}

    total_deleted = 0

    print("Scanning for non-successful runs...")

    for uid, user_data in all_users.items():
        if not isinstance(user_data, dict):
            continue

        runs = user_data.get("runs", {})
        if not runs:
            continue

        deletions = []
        for key, run in runs.items():
            status = run.get("status", "unknown")
            if status != "success":
                deletions.append(key)

        if deletions:
            print(
                f"User {uid}: Deleting {len(deletions)} non-success runs (Status: {[runs[k].get('status') for k in deletions]})"
            )
            run_ref = db.reference(f"users/{uid}/runs")
            update_payload = {k: None for k in deletions}
            run_ref.update(update_payload)
            total_deleted += len(deletions)

    print("-" * 30)
    print(f"Purge complete. Deleted {total_deleted} runs.")


if __name__ == "__main__":
    purge_non_success()
