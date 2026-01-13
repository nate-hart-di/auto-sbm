import argparse
from sbm.utils.firebase_sync import is_firebase_available, get_firebase_db, get_settings
from sbm.utils.tracker import _get_user_id


def log(msg, file_only=False):
    if not file_only:
        print(msg)
    with open("cleanup_log.txt", "a") as f:
        f.write(msg + "\n")


def clean_runs(force=False):
    # Clear log file
    with open("cleanup_log.txt", "w") as f:
        f.write(f"Starting cleanup. Force: {force}\n")

    if not is_firebase_available():
        log("Firebase unavailable.")
        return

    settings = get_settings()

    log(f"Cleaning empty runs (<= 0 lines). Force: {force}")

    users_ref = None
    if settings.firebase.is_admin_mode():
        db = get_firebase_db()
        users_ref = db.reference("users")
    else:
        log("Admin mode required to clean all users.")
        # Fallback to current user cleanup if needed?
        # For now, assume admin.
        return

    users_data = users_ref.get() or {}
    log(f"Scanning {len(users_data)} users...")

    total_deleted = 0
    total_found_empty = 0

    for user_id, user_data in users_data.items():
        if not isinstance(user_data, dict):
            continue

        runs = user_data.get("runs", {})
        updates = {}

        for run_id, run in runs.items():
            lines = run.get("lines_migrated", 0)
            status = run.get("status")

            if status == "success" and lines <= 0:
                slug = run.get("slug", "unknown")
                timestamp = run.get("timestamp", "")
                log(f"[found] User: {user_id} | Slug: {slug} | Lines: {lines} | Date: {timestamp}")
                total_found_empty += 1
                updates[run_id] = None  # Mark for deletion

        if updates:
            if force:
                ref = db.reference(f"users/{user_id}/runs")
                ref.update(updates)
                log(f"  -> Deleted {len(updates)} runs for {user_id}")
                total_deleted += len(updates)
            else:
                log(f"  -> Would delete {len(updates)} runs for {user_id}")

    log("-" * 50)
    log(f"Total Empty Runs Found: {total_found_empty}")
    if force:
        log(f"Total Deleted: {total_deleted}")
    else:
        log("DRY RUN. Use --force to delete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Actually delete the runs")
    args = parser.parse_args()

    clean_runs(force=args.force)
