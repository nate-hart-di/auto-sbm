import firebase_admin
from firebase_admin import credentials, db
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbm.config import get_settings


def find_missing():
    settings = get_settings()
    user_id = "nate-hart-di"

    if settings.firebase.is_admin_mode():
        cred = credentials.Certificate(str(settings.firebase.credentials_path))
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {"databaseURL": settings.firebase.database_url})

        # Fetch Migrations (List of slugs)
        migrations_ref = db.reference(f"users/{user_id}/migrations")
        migrations_data = migrations_ref.get()

        # Fetch Runs (Dict of run objects)
        runs_ref = db.reference(f"users/{user_id}/runs")
        runs_data = runs_ref.get()

    else:
        print("Admin mode required.")
        return

    # Parse Migrations
    migrations_set = set()
    if isinstance(migrations_data, list):
        migrations_set = set(filter(None, migrations_data))
    elif isinstance(migrations_data, dict):
        migrations_set = set(migrations_data.keys())

    print(f"Total Migrations (Target): {len(migrations_set)}")

    # Parse Runs
    runs_slugs = set()
    if runs_data:
        for r in runs_data.values():
            if r.get("status") == "success":
                runs_slugs.add(r.get("slug"))

    print(f"Total Successful Runs: {len(runs_slugs)}")

    # Diff
    missing = migrations_set - runs_slugs
    if missing:
        print(f"Missing Slugs ({len(missing)}):")
        for s in missing:
            print(f" - {s}")
    else:
        print("No missing slugs found! (Wait, then why the count mismatch?)")
        if len(runs_slugs) > len(migrations_set):
            extra = runs_slugs - migrations_set
            print(f"Extra Runs not in Migrations ({len(extra)}):")
            for s in extra:
                print(f" - {s}")


if __name__ == "__main__":
    find_missing()
