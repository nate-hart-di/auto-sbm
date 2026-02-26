import json
import subprocess
from pathlib import Path

# Find project root (2 levels up from scripts/stats/)
ROOT_DIR = Path(__file__).parent.parent.parent.resolve()
RAW_DATA_DIR = ROOT_DIR / "stats" / "raw"


def get_pr_data(url: str) -> dict | None:
    try:
        result = subprocess.run(
            ["gh", "pr", "view", url, "--json", "additions,author,createdAt,title"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        return {
            "url": url,
            "additions": data.get("additions", 0),
            "author": data.get("author", {}).get("login", "unknown"),
            "createdAt": data.get("createdAt"),
            "title": data.get("title"),
        }
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def main() -> None:
    input_file = RAW_DATA_DIR / "merged_prs.json"
    if not input_file.exists():
        print(f"File not found: {input_file}")
        return

    try:
        with input_file.open("r", encoding="utf-8") as f:
            all_prs = json.load(f)
    except Exception as e:
        print(f"Error reading {input_file}: {e}")
        return

    automated_prs = [
        pr
        for pr in all_prs
        if pr.get("title", "").endswith(" - SBM FE Audit") or "PCON-864" in pr.get("title", "")
    ]

    results = []
    print(f"Fetching data for {len(automated_prs)} PRs...")
    for i, pr in enumerate(automated_prs):
        if i % 10 == 0:
            print(f"Progress: {i}/{len(automated_prs)}")
        data = get_pr_data(pr["url"])
        if data:
            results.append(data)

    output_file = RAW_DATA_DIR / "historical_data.json"
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Done! Saved {len(results)} PRs to {output_file}")


if __name__ == "__main__":
    main()
