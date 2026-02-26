import os
import sys

import firebase_admin
from firebase_admin import credentials, db

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbm.config import get_settings


def inspect_failed_users():
    settings = get_settings()
    if not settings.firebase.is_admin_mode():
        print("Admin required")
        return

    cred = credentials.Certificate(str(settings.firebase.credentials_path))
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {"databaseURL": settings.firebase.database_url})

    users = ["dancrum-di", "stephthorn"]

    for uid in users:
        print(f"--- {uid} ---")
        ref = db.reference(f"users/{uid}/runs")
        data = ref.get()
        if data:
            for k, v in data.items():
                print(f"Key: {k}")
                print(f"Slug: {v.get('slug')}")
                print(f"Timestamp: {v.get('timestamp')}")
                print("-" * 10)
        else:
            print("No data found")


if __name__ == "__main__":
    inspect_failed_users()
