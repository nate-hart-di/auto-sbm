import os
from sbm.utils.firebase_sync import is_firebase_available, get_firebase_db, get_settings
from sbm.utils.tracker import _get_user_id


def inspect_runs():
    output = []
    output.append(f"Firebase available: {is_firebase_available()}")
    if not is_firebase_available():
        output.append("Firebase unavailable.")
        with open("suspicious_runs.txt", "w") as f:
            f.write("\n".join(output))
        return

    settings = get_settings()
    user_id = _get_user_id()
    output.append(f"Inspecting runs for user: {user_id}")

    runs_data = {}
    if settings.firebase.is_admin_mode():
        output.append("Mode: Admin")
        db = get_firebase_db()
        ref = db.reference(f"users/{user_id}/runs")
        runs_data = ref.get() or {}
        output.append(f"Fetched {len(runs_data)} runs.")
    else:
        output.append("Mode: User (Not supported in this script)")
        with open("suspicious_runs.txt", "w") as f:
            f.write("\n".join(output))
        return
        # User mode fetch
        pass  # Simplified for admin/dev usage for now as user likely has admin creds locally

    count_zero = 0
    count_total = 0

    output.append(f"{'Slug':<30} | {'Lines':<10} | {'Date':<20}")
    output.append("-" * 65)

    for key, run in runs_data.items():
        count_total += 1
        lines = run.get("lines_migrated", 0)
        timestamp = run.get("timestamp", "")
        slug = run.get("slug", "unknown")

        if lines <= 0 and run.get("status") == "success":
            count_zero += 1
            output.append(f"{slug:<30} | {lines:<10} | {timestamp:<20}")

    output.append("-" * 65)
    output.append(f"Total Runs: {count_total}")
    output.append(f"Suspicious (0 lines) Runs: {count_zero}")

    with open("suspicious_runs.txt", "w") as f:
        f.write("\n".join(output))


if __name__ == "__main__":
    inspect_runs()
