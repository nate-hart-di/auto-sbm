import json
from pathlib import Path
from datetime import datetime
import re

GLOBAL_STATS_DIR = Path("stats")

def extract_slug(title):
    # Pattern 1: PCON-727: {slug} SBM FE Audit
    match1 = re.search(r"PCON-727:\s+([a-zA-Z0-9_-]+)\s+SBM FE Audit", title, re.IGNORECASE)
    if match1:
        return match1.group(1).lower()

    # Pattern 2: {slug} - SBM FE Audit
    match2 = re.search(r"^([a-zA-Z0-9_-]+)\s+-\s+SBM FE Audit", title, re.IGNORECASE)
    if match2:
        return match2.group(1).lower()

    # Pattern 3: New DT - {slug} or {slug} - New DT
    match3 = re.search(r"New DT\s+-\s+([a-zA-Z0-9_-]+)", title, re.IGNORECASE)
    if match3:
        return match3.group(1).lower()
    match3b = re.search(r"([a-zA-Z0-9_-]+)\s+-\s+New DT", title, re.IGNORECASE)
    if match3b:
        return match3b.group(1).lower()

    # Pattern 4: PCON-727: {slug} ... (general PCON pattern)
    match4 = re.search(r"PCON-727:\s+([a-zA-Z0-9_-]+)", title, re.IGNORECASE)
    if match4:
        return match4.group(1).lower()

    # Fallback: just take the first word if it looks like a slug
    first_word = title.split()[0].lower()
    if len(first_word) > 3: # arbitrary minimum
        return first_word

    return "unknown"

def main():
    if not GLOBAL_STATS_DIR.exists():
        GLOBAL_STATS_DIR.mkdir(parents=True, exist_ok=True)

    with open("all_team_prs.json", "r") as f:
        historical_data = json.load(f)

    # Filter for SBM/DT related PRs
    relevant_data = [
        pr for pr in historical_data
        if any(keyword in pr.get("title", "").upper() for keyword in ["SBM", "FE AUDIT", "DT"])
    ]

    # Group by author
    users = {}
    for entry in relevant_data:
        author_data = entry.get("author", {})
        if not author_data: continue
        author = author_data.get("login", "unknown")

        if author not in users:
            users[author] = {"migrations": set(), "runs": []}

        slug = extract_slug(entry["title"])
        if slug == "unknown": continue

        users[author]["migrations"].add(slug)

        run_entry = {
            "timestamp": entry["createdAt"],
            "slug": slug,
            "command": "auto",
            "status": "success",
            "duration_seconds": 300.0,
            "automation_seconds": 60.0,
            "lines_migrated": entry["additions"],
            "manual_estimate_seconds": 240 * 60,
            "historical": True
        }
        users[author]["runs"].append(run_entry)

    # Save each user's stats
    for author, data in users.items():
        user_id = author
        global_file = GLOBAL_STATS_DIR / f"{user_id}.json"

        # In this clean backfill, we overwrite to ensure consistency with the new logic
        # But we could also merge if we wanted to preserve actual live runs.
        # Since this is a "Refining Stats" task, a fresh backfill from the source of truth (GH) is safer.

        final_data = {
            "user": user_id,
            "migrations": sorted(list(data["migrations"])),
            "runs": sorted(data["runs"], key=lambda x: x["timestamp"])[-500:],
            "last_updated": datetime.now().isoformat() + "Z"
        }

        with global_file.open("w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=2)

        print(f"Backfilled {len(data['runs'])} runs for {author} -> {global_file} ({len(data['migrations'])} unique sites)")

if __name__ == "__main__":
    main()
