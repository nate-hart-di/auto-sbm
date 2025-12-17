import json
import re

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
        
    return None

def main():
    with open("nate_all_prs.json", "r") as f:
        data = json.load(f)
        
    slugs = {}
    for entry in data:
        slug = extract_slug(entry["title"])
        if slug:
            if slug not in slugs:
                slugs[slug] = []
            slugs[slug].append(entry)
            
    print(f"Total PRs: {len(data)}")
    print(f"SBM/DT Migrations Found: {len(slugs)}")
    print("\nMigrations List:")
    for slug in sorted(slugs.keys()):
        print(f"- {slug} ({len(slugs[slug])} PRs)")

if __name__ == "__main__":
    main()
