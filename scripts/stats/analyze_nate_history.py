import json
import re
from pathlib import Path

# Find project root (2 levels up from scripts/stats/)
ROOT_DIR = Path(__file__).parent.parent.parent.resolve()
RAW_DATA_DIR = ROOT_DIR / "stats" / "raw"

def extract_slug(title: str) -> str | None:
    # Pattern 1: PCON-864: {slug} SBM FE Audit
    match1 = re.search(r"PCON-864:\s+([a-zA-Z0-9_-]+)\s+SBM FE Audit", title, re.IGNORECASE)
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

def main() -> None:
    filepath = RAW_DATA_DIR / "nate_all_prs.json"
    if not filepath.exists():
        print(f"File not found: {filepath}")
        return

    try:
        with filepath.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return

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
