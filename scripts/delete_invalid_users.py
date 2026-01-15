import firebase_admin
from firebase_admin import credentials, db
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbm.config import get_settings


def delete_invalid_users():
    settings = get_settings()
    if not settings.firebase.is_admin_mode():
        print("Admin required")
        return

    cred = credentials.Certificate(str(settings.firebase.credentials_path))
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {"databaseURL": settings.firebase.database_url})

    users_to_clean = ["dancrum-di", "stephthorn"]

    for uid in users_to_clean:
        print(f"Deleting runs for user: {uid}")
        ref = db.reference(f"users/{uid}/runs")
        # Check if exists first just to be sure
        if ref.get():
            ref.delete()
            print(f"  Deleted runs for {uid}")
        else:
            print(f"  No runs found for {uid} (already deleted?)")


if __name__ == "__main__":
    delete_invalid_users()
