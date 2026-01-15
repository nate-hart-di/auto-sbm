import firebase_admin
from firebase_admin import credentials, db
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbm.config import get_settings


def delete_specific_slugs():
    settings = get_settings()
    user_id = "nate-hart-di"

    slugs_to_delete = [
        "boggustiptonchryslerdodgejeepram",
        "daviddodge",
        "iversonautogroup",
        "vallejochryslerdodgejeepram",
    ]

    print(f"Deleting runs for {len(slugs_to_delete)} slugs...")

    if settings.firebase.is_admin_mode():
        cred = credentials.Certificate(str(settings.firebase.credentials_path))
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {"databaseURL": settings.firebase.database_url})

        ref = db.reference(f"users/{user_id}/runs")
        all_runs = ref.get() or {}

        deleted_count = 0
        for key, run in all_runs.items():
            if run.get("slug") in slugs_to_delete:
                print(f"Deleting run for {run.get('slug')} (Key: {key})")
                ref.child(key).delete()
                deleted_count += 1

        print(f"Deleted {deleted_count} records.")
    else:
        print("Admin mode required.")


if __name__ == "__main__":
    delete_specific_slugs()
