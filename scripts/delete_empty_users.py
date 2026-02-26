import os
import sys

import firebase_admin
from firebase_admin import credentials, db

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbm.config import get_settings


def delete_empty_users():
    settings = get_settings()
    if not settings.firebase.is_admin_mode():
        print("Admin required")
        return

    cred = credentials.Certificate(str(settings.firebase.credentials_path))
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {"databaseURL": settings.firebase.database_url})

    ref = db.reference("users")
    all_users = ref.get() or {}

    users_to_delete = []

    print("Scanning for users with 0 successful runs...")

    for uid, user_data in all_users.items():
        if not isinstance(user_data, dict):
            # If it's not a dict, it's malformed or empty, mark for delete
            users_to_delete.append(uid)
            continue

        runs = user_data.get("runs", {})

        # Count successful runs
        success_count = 0
        if runs:
            for r in runs.values():
                if r.get("status") == "success":
                    success_count += 1

        if success_count == 0:
            print(f"User {uid}: Has {success_count} successful runs. Marking for deletion.")
            users_to_delete.append(uid)

    if users_to_delete:
        print(f"Deleting {len(users_to_delete)} users: {users_to_delete}")

        # We can delete them one by one or via a multi-path update.
        # Multi-path update is safer/atomic-ish.
        update_payload = dict.fromkeys(users_to_delete)
        ref.update(update_payload)
        print("Deletion complete.")
    else:
        print("No empty users found.")


if __name__ == "__main__":
    delete_empty_users()
