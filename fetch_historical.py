import json
import subprocess
import os

def get_pr_data(url):
    try:
        result = subprocess.run(
            ["gh", "pr", "view", url, "--json", "additions,author,createdAt,title"],
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)
        return {
            "url": url,
            "additions": data.get("additions", 0),
            "author": data.get("author", {}).get("login", "unknown"),
            "createdAt": data.get("createdAt"),
            "title": data.get("title")
        }
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def main():
    with open("merged_prs.json", "r") as f:
        all_prs = json.load(f)
    
    automated_prs = [
        pr for pr in all_prs 
        if pr.get("title", "").endswith(" - SBM FE Audit") or "PCON-727" in pr.get("title", "")
    ]
    
    results = []
    print(f"Fetching data for {len(automated_prs)} PRs...")
    for i, pr in enumerate(automated_prs):
        if i % 10 == 0:
            print(f"Progress: {i}/{len(automated_prs)}")
        data = get_pr_data(pr["url"])
        if data:
            results.append(data)
    
    with open("historical_data.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"Done! Saved {len(results)} PRs to historical_data.json")

if __name__ == "__main__":
    main()
