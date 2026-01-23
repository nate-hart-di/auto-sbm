import json
from pathlib import Path
from datetime import datetime
import re

# REPO_ROOT = Path(__file__).parent.resolve()
GLOBAL_STATS_DIR = Path("stats")

def extract_slug(title):
    # Pattern 1: PCON-864: {slug} SBM FE Audit
    match1 = re.search(r"PCON-864:\s+([a-zA-Z0-9_-]+)\s+SBM FE Audit", title)
    if match1:
        return match1.group(1)

    # Pattern 2: {slug} - SBM FE Audit
    match2 = re.search(r"^([a-zA-Z0-9_-]+)\s+-\s+SBM FE Audit", title)
    if match2:
        return match2.group(1)

    # Fallback: just take the first word if it looks like a slug
    return title.split()[0].lower()

def main():
    if not GLOBAL_STATS_DIR.exists():
        GLOBAL_STATS_DIR.mkdir(parents=True, exist_ok=True)

    with open("historical_data.json", "r") as f:
        historical_data = json.load(f)

    # Group by author
    users = {}
    for entry in historical_data:
        author = entry["author"]
        if author not in users:
            users[author] = {"migrations": set(), "runs": []}

        slug = extract_slug(entry["title"])
        users[author]["migrations"].add(slug)

        # Create a run entry
        # Note: We don't have duration/automation_time for history, so we'll use defaults
        # But we DO have additions (lines_migrated)
        run_entry = {
            "timestamp": entry["createdAt"],
            "slug": slug,
            "command": "auto",  # Assume auto for history
            "status": "success",
            "duration_seconds": 300.0,  # Proxy: 5 minutes
            "automation_seconds": 60.0,   # Proxy: 1 minute
            "lines_migrated": entry["additions"],
            "manual_estimate_seconds": 240 * 60, # 4 hours legacy proxy
            "historical": True
        }
        users[author]["runs"].append(run_entry)

    # Save each user's stats
    for author, data in users.items():
        user_id = author.replace("@", "_").replace(".", "_")
        global_file = GLOBAL_STATS_DIR / f"{user_id}.json"

        # If file exists, merge data
        existing_migrations = []
        existing_runs = []
        if global_file.exists():
            with global_file.open("r", encoding="utf-8") as f:
                try:
                    existing_data = json.load(f)
                    existing_migrations = existing_data.get("migrations", [])
                    existing_runs = existing_data.get("runs", [])
                except Exception:
                    pass

        # Combine
        combined_migrations = sorted(list(set(existing_migrations) | data["migrations"]))
        combined_runs = existing_runs + data["runs"]

        # Sort runs by timestamp
        combined_runs.sort(key=lambda x: x["timestamp"])

        final_data = {
            "user": user_id,
            "migrations": combined_migrations,
            "runs": combined_runs[-500:], # keep last 500
            "last_updated": datetime.now().isoformat() + "Z"
        }

        with global_file.open("w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=2)

        print(f"Backfilled {len(data['runs'])} runs for {author} -> {global_file}")

if __name__ == "__main__":
    main()
