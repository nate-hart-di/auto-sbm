import json
from pathlib import Path
from collections import defaultdict, Counter


def analyze(file_path):
    print(f"Reading {file_path}...")
    with open(file_path) as f:
        data = json.load(f)

    users = data.get("users", {})

    total_runs = 0
    valid_runs = 0
    invalid_runs = 0

    unique_slugs = set()
    user_stats = defaultdict(lambda: {"total": 0, "valid": 0, "slugs": set(), "lines": 0})

    print("\n--- Analysis ---")

    for user, user_data in users.items():
        if not isinstance(user_data, dict):
            continue
        runs = user_data.get("runs", {})

        for run_id, run in runs.items():
            total_runs += 1
            status = run.get("status")
            slug = run.get("slug")
            lines = run.get("lines_migrated", 0)

            user_stats[user]["total"] += 1

            if status == "success":
                valid_runs += 1
                user_stats[user]["valid"] += 1
                user_stats[user]["lines"] += lines
                if slug:
                    unique_slugs.add(slug)
                    user_stats[user]["slugs"].add(slug)
            else:
                invalid_runs += 1

    print(f"Total Runs in DB: {total_runs}")
    print(f"Valid Runs (success): {valid_runs}")
    print(f"Invalid Runs (not success): {invalid_runs}")
    print(f"Total Unique Valid Slugs: {len(unique_slugs)}")

    print("\n--- By User ---")
    for user, stats in user_stats.items():
        print(f"User: {user}")
        print(f"  Total Runs: {stats['total']}")
        print(f"  Valid Runs: {stats['valid']}")
        print(f"  Unique Slugs: {len(stats['slugs'])}")
        print(f"  Total Lines: {stats['lines']:,}")

    # Check specifically for nate-hart-di
    target = "nate-hart-di"
    if target in user_stats:
        print(f"\n--- Focus: {target} ---")
        print(f"Valid Runs: {user_stats[target]['valid']}")
        print(f"Unique Slugs: {len(user_stats[target]['slugs'])}")
        print(f"Line Count: {user_stats[target]['lines']:,}")


if __name__ == "__main__":
    analyze("docs/auto-sbm-default-rtdb-export.json")
