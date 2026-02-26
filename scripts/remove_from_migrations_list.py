import os
import sys

import firebase_admin
from firebase_admin import credentials, db

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbm.config import get_settings


def clean_migrations_list():
    settings = get_settings()
    user_id = "nate-hart-di"

    slugs_to_delete = [
        "boggustiptonchryslerdodgejeepram",
        "daviddodge",
        "iversonautogroup",
        "vallejochryslerdodgejeepram",
    ]

    print(f"Checking 'migrations' list for {len(slugs_to_delete)} slugs...")

    if settings.firebase.is_admin_mode():
        cred = credentials.Certificate(str(settings.firebase.credentials_path))
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {"databaseURL": settings.firebase.database_url})

        ref = db.reference(f"users/{user_id}/migrations")
        current_data = ref.get()

        if not current_data:
            print("No migrations list found.")
            return

        if isinstance(current_data, list):
            new_list = [s for s in current_data if s and s not in slugs_to_delete]
            removed_count = len(current_data) - len(new_list)
            print(f"Found {removed_count} slugs in List format.")
            if removed_count > 0:
                ref.set(new_list)
                print("Updated migrations list.")

        elif isinstance(current_data, dict):
            # Dict keys are the slugs? Or indices?
            # Usually it's a list, but might be dict if keys are large integers
            keys_to_remove = []
            for k, v in current_data.items():
                if v in slugs_to_delete or k in slugs_to_delete:  # Value is slug
                    keys_to_remove.append(k)

            print(f"Found {len(keys_to_remove)} slugs in Dict format.")
            for k in keys_to_remove:
                ref.child(k).delete()
            print("Updated migrations dict.")

    else:
        print("Admin mode required.")


if __name__ == "__main__":
    clean_migrations_list()
