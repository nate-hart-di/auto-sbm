import firebase_admin
from firebase_admin import credentials, db
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbm.config import get_settings


def find_duplicates():
    settings = get_settings()
    if not settings.firebase.is_admin_mode():
        print("Admin required")
        return

    cred = credentials.Certificate(str(settings.firebase.credentials_path))
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {"databaseURL": settings.firebase.database_url})

    ref = db.reference("users")
    all_users = ref.get() or {}

    total_dupes = 0

    print("Scanning for duplicates...")

    for uid, user_data in all_users.items():
        if not isinstance(user_data, dict):
            continue

        runs = user_data.get("runs", {})
        if not runs:
            continue

        slug_map = {}
        for key, run in runs.items():
            if run.get("status") != "success":
                continue

            slug = run.get("slug")
            if not slug:
                continue

            if slug not in slug_map:
                slug_map[slug] = []
            slug_map[slug].append({"key": key, "timestamp": run.get("timestamp", "")})

        for slug, run_list in slug_map.items():
            if len(run_list) > 1:
                print(f"User {uid}: Duplicate slug '{slug}' ({len(run_list)} runs)")
                # Sort by timestamp descending (newest first)
                run_list.sort(key=lambda x: x["timestamp"], reverse=True)

                # Keep first (newest), delete rest
                to_delete = run_list[1:]
                for item in to_delete:
                    print(f"  -> Would delete old key: {item['key']} (Time: {item['timestamp']})")
                    total_dupes += 1

                # Execute deletion
                run_ref = db.reference(f"users/{uid}/runs")
                update_payload = {item["key"]: None for item in to_delete}
                run_ref.update(update_payload)
                print(f"  -> DELETED {len(to_delete)} duplicates.")

    print("-" * 30)
    print(f"Scan complete. Deleted {total_dupes} duplicates.")


if __name__ == "__main__":
    find_duplicates()
