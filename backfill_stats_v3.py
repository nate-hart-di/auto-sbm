import json
from pathlib import Path
from datetime import datetime
import re

GLOBAL_STATS_DIR = Path("stats")

def extract_slug(title):
    if not title: return None
    
    # Clean title
    title = title.strip()
    
    # Pattern 1: PCON-727: {slug} SBM FE Audit
    match1 = re.search(r"PCON-727:\s+([a-zA-Z0-9_-]+)", title, re.IGNORECASE)
    if match1:
        return match1.group(1).lower()
    
    # Pattern 2: {slug} - SBM FE Audit (or {slug} SBM FE Audit)
    match2 = re.search(r"^([a-zA-Z0-9_-]+)(?:\s+-\s+|\s+)(?:SBM|FE Audit|NEW SITE|DEALERTHEME|Legacy Code Migration)", title, re.IGNORECASE)
    if match2:
        slug = match2.group(1).lower().strip("[]")
        if slug not in ["sbm", "new", "fe", "legacy"]:
            return slug
    
    # Pattern 3: New DT - {slug} or {slug} - New DT
    match3 = re.search(r"(?:New DT|SBM|Legacy Code Migration)\s+-\s+([a-zA-Z0-9_-]+)", title, re.IGNORECASE)
    if match3:
        return match3.group(1).lower()
    match3b = re.search(r"([a-zA-Z0-9_-]+)\s+-\s+(?:New DT|SBM|Legacy Code Migration)", title, re.IGNORECASE)
    if match3b:
        return match3b.group(1).lower()

    # Pattern 4: {slug} - SBM
    match4 = re.search(r"^([a-zA-Z0-9_-]+)\s+-\s+SBM", title, re.IGNORECASE)
    if match4:
        return match4.group(1).lower()
        
    # Pattern 5: {slug} SBM
    match5 = re.search(r"^([a-zA-Z0-9_-]+)\s+SBM", title, re.IGNORECASE)
    if match5:
        slug = match5.group(1).lower()
        if slug != "alfa": # special case like "Alfa Romeo of ... - SBM"
            return slug

    # Special Case: "Alfa Romeo of {slug} - SBM" or "BMW of {slug} - SBM"
    match_special = re.search(r"(?:BMW|Alfa Romeo) of ([a-zA-Z0-9_-]+)", title, re.IGNORECASE)
    if match_special:
        return match_special.group(1).lower()

    return None

def process_file(filepath, users_dict):
    if not Path(filepath).exists():
        print(f"File not found: {filepath}")
        return
        
    with open(filepath, "r") as f:
        try:
            data = json.load(f)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return
            
    processed_count = 0
    for entry in data:
        # Normalize entry structure
        author = "unknown"
        if "author" in entry:
            auth_val = entry["author"]
            if isinstance(auth_val, dict):
                author = auth_val.get("login", "unknown")
            else:
                author = auth_val
        
        if author == "unknown": continue
        
        slug = extract_slug(entry.get("title", ""))
        if not slug: continue
        
        if author not in users_dict:
            users_dict[author] = {"migrations": set(), "runs": {}}
        
        users_dict[author]["migrations"].add(slug)
        processed_count += 1
        
        # De-duplicate runs by timestamp and slug
        ts = entry.get("createdAt")
        run_key = f"{ts}_{slug}"
        
        if run_key not in users_dict[author]["runs"]:
            users_dict[author]["runs"][run_key] = {
                "timestamp": ts,
                "slug": slug,
                "command": "auto",
                "status": "success",
                "duration_seconds": 300.0,
                "automation_seconds": 60.0,
                "lines_migrated": entry.get("additions", 0),
                "manual_estimate_seconds": 240 * 60,
                "historical": True
            }
    print(f"Processed {processed_count} relevant entries from {filepath}")

def main():
    if not GLOBAL_STATS_DIR.exists():
        GLOBAL_STATS_DIR.mkdir(parents=True, exist_ok=True)

    users = {}
    
    # Process all sources
    process_file("historical_data.json", users)
    process_file("nate_all_prs.json", users)
    process_file("all_team_prs.json", users)
    
    # Save each user's stats
    for author, data in users.items():
        user_id = author
        global_file = GLOBAL_STATS_DIR / f"{user_id}.json"
        
        # Combine historical and live
        hist_runs = list(data["runs"].values())
        
        # Sort runs by timestamp
        combined_runs = sorted(hist_runs, key=lambda x: x["timestamp"])
        
        # Recalculate unique migrations
        all_slugs = sorted(list(set(r["slug"] for r in combined_runs)))

        final_data = {
            "user": user_id,
            "migrations": all_slugs,
            "runs": combined_runs[-500:], # keep last 500
            "last_updated": datetime.now().isoformat() + "Z"
        }

        with global_file.open("w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=2)
        
        print(f"Overall Merge for {author}: {len(combined_runs)} runs, {len(all_slugs)} unique sites")

if __name__ == "__main__":
    main()
