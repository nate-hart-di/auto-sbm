import os
import sys

import firebase_admin
from firebase_admin import credentials, db

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbm.config import get_settings


def verify_data_integrity():
    settings = get_settings()
    if not settings.firebase.is_admin_mode():
        print("Admin required")
        return

    cred = credentials.Certificate(str(settings.firebase.credentials_path))
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {"databaseURL": settings.firebase.database_url})

    ref = db.reference("users")
    all_users = ref.get() or {}

    total_lines = 0
    total_runs = 0

    print(f"{'User':<20} | {'Runs':<5} | {'Lines':<10}")
    print("-" * 40)

    for uid, data in all_users.items():
        runs = data.get("runs", {})
        user_lines = 0
        user_run_count = 0  # Initialize to 0, will count successful runs

        for r in runs.values():
            if r.get("status") != "success":
                continue

            # Handle string vs int issues if any
            l = r.get("lines_migrated", 0)
            try:
                user_lines += int(l)
                user_run_count += 1  # Increment only for successful runs with valid lines
            except:
                pass

        total_runs += user_run_count
        total_lines += user_lines
        print(f"{uid:<20} | {user_run_count:<5} | {user_lines:<10,}")

    print("-" * 40)
    print(f"TOTAL TEAM RUNS:  {total_runs}")
    print(f"TOTAL TEAM LINES: {total_lines:,}")


if __name__ == "__main__":
    verify_data_integrity()
