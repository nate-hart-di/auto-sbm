import glob
import json
import os

from sbm.utils.firebase_sync import (
    get_firebase_db,
    is_firebase_available,
)

# Initialize Firebase
if not is_firebase_available():
    print("Initializing Firebase...")
    # This triggers internal initialization

if not is_firebase_available():
    print("❌ Failed to initialize Firebase. Exiting.")
    exit(1)

db = get_firebase_db()
users_ref = db.reference("/users")


def backfill_firebase():
    print("=" * 60)
    print("FIREBASE BACKFILL START")
    print("=" * 60)

    # Find all archive files
    archive_pattern = os.path.join("stats", "archive", "*.json")
    files = glob.glob(archive_pattern)

    if not files:
        print("❌ No archive files found in stats/archive/")
        return

    print(f"Found {len(files)} archive files to process.\n")

    total_runs_added = 0
    total_runs_skipped = 0
    total_users_processed = 0

    for file_path in sorted(files):
        filename = os.path.basename(file_path)
        user_id_from_file = os.path.splitext(filename)[0]

        print(f"Processing {user_id_from_file}...")

        try:
            with open(file_path) as f:
                data = json.load(f)
        except Exception as e:
            print(f"  ❌ Error reading file: {e}")
            continue

        legacy_runs = data.get("runs", [])
        legacy_migrations = data.get("migrations", [])

        if not legacy_runs:
            print("  ⚠️ No runs found in file. Skipped.")
            continue

        # Get existing Firebase data for user
        user_ref = users_ref.child(user_id_from_file)
        firebase_user_data = user_ref.get() or {}

        existing_runs = firebase_user_data.get("runs", {})
        existing_migrations = firebase_user_data.get("migrations", [])

        # Convert existing runs to a lookup set (slug + timestamp)
        existing_run_keys = set()
        if existing_runs:
            for r in existing_runs.values():
                key = f"{r.get('slug')}_{r.get('timestamp')}"
                existing_run_keys.add(key)

        runs_added = 0
        runs_skipped = 0

        # Process runs
        for run in legacy_runs:
            # Ensure essential fields
            slug = run.get("slug")
            timestamp = run.get("timestamp")

            if not slug or not timestamp:
                continue

            key = f"{slug}_{timestamp}"

            if key in existing_run_keys:
                runs_skipped += 1
                continue

            # Prepare run data (sanitize/ensure types)
            new_run = {
                "slug": slug,
                "timestamp": timestamp,
                "command": run.get("command", "auto"),
                "status": run.get("status", "success"),
                "user_id": user_id_from_file,
                "historical": True,  # Mark as backfilled
                "source": "legacy_archive",
            }

            # Add metrics if available
            if "lines_migrated" in run:
                new_run["lines_migrated"] = int(run["lines_migrated"])
            if "duration_seconds" in run:
                new_run["duration_seconds"] = float(run["duration_seconds"])
            if "automation_seconds" in run:
                new_run["automation_seconds"] = float(run["automation_seconds"])
            if "manual_estimate_seconds" in run:
                new_run["manual_estimate_seconds"] = int(run["manual_estimate_seconds"])

            # Push to Firebase
            user_ref.child("runs").push(new_run)
            runs_added += 1
            total_runs_added += 1

        print(f"  ✅ Added {runs_added} runs, Skipped {runs_skipped} duplicates.")
        total_runs_skipped += runs_skipped
        total_users_processed += 1

        # Check migrations list
        if isinstance(existing_migrations, list):
            existing_slugs = set(existing_migrations)
        else:
            existing_slugs = set(existing_migrations.values()) if existing_migrations else set()

        migrations_added = 0
        for slug in legacy_migrations:
            if slug not in existing_slugs:
                # Add to migrations list if missing
                # Note: 'migrations' in Firebase can be a list or dict.
                # Ideally we push to it.
                if isinstance(existing_migrations, list):
                    # It's a list, we can't easily append without race conditions or re-writing
                    # But if we just want to ensure coverage, adding runs is the most important part.
                    # Let's skip modifying the simple migrations list for now to avoid complexity,
                    # as runs are the source of truth for stats now.
                    pass
                else:
                    # It's a dict (or empty), safe to push
                    user_ref.child("migrations").push(slug)
                    migrations_added += 1

        if migrations_added > 0:
            print(f"  ➕ Added {migrations_added} missing slugs to migrations list.")

    print("\n" + "=" * 60)
    print("BACKFILL COMPLETE")
    print("=" * 60)
    print(f"Total Users Processed: {total_users_processed}")
    print(f"Total Runs Added:      {total_runs_added}")
    print(f"Total Runs Skipped:    {total_runs_skipped}")


if __name__ == "__main__":
    try:
        backfill_firebase()
    except KeyboardInterrupt:
        print("\n🚫 Backfill cancelled by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
