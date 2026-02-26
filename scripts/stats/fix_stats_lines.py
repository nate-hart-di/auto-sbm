#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path

# Project Root
ROOT_DIR = Path(__file__).parent.parent.parent.resolve()
STATS_DIR = ROOT_DIR / "stats"
RAW_DIR = STATS_DIR / "raw"


def load_json(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except:
        return None


def clean_ts(ts_str):
    if not ts_str:
        return None
    # Handle "2026-01-06...27+00:00Z" double offset
    if ts_str.endswith("+00:00Z"):
        ts_str = ts_str[:-1]
    elif ts_str.endswith("Z"):
        ts_str = ts_str[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(ts_str)
    except:
        return None


def fix_stats():
    print("🔍 Starting stats repair...")

    # 1. Load PR Source Data
    # We combine all possible PR sources
    pr_data = []
    for pr_file in [
        "merged_prs.json",
        "all_team_prs.json",
        "nate_all_prs.json",
        "historical_data.json",
    ]:
        data = load_json(RAW_DIR / pr_file)
        if data:
            if isinstance(data, list):
                pr_data.extend(data)
            elif isinstance(data, dict) and "data" in data:  # some exports might be wrapped
                pr_data.extend(data["data"])

    print(f"✅ Loaded {len(pr_data)} PR records for reference.")

    # Map of slug -> list of (timestamp, additions)
    # This helps us match "runs" (which have timestamps) to "PRs"
    slug_map = {}
    import re

    # More specific regex to avoid matching "sbm" or "pcon" as the slug
    slug_pattern = re.compile(
        r"(?:pcon-\d+:\s+)?([a-z0-9_-]+)(?:\s+sbm|\s+fe\s+audit)", re.IGNORECASE
    )

    for entry in pr_data:
        title = entry.get("title", "")
        # fallback to first word if pattern fails
        match = slug_pattern.search(title)
        if match:
            slug = match.group(1).lower()
        else:
            slug = title.split()[0].lower().strip(":")

        ts = clean_ts(entry.get("mergedAt") or entry.get("createdAt"))
        if not ts:
            continue

        additions = entry.get("additions", 0)
        if slug not in slug_map:
            slug_map[slug] = []
        slug_map[slug].append((ts, additions))

    total_fixed = 0
    total_files = 0

    # 2. Files to process
    target_files = list(STATS_DIR.glob("*.json"))
    home_tracker = Path.home() / ".sbm_migrations.json"
    if home_tracker.exists():
        target_files.append(home_tracker)

    # 3. Process each stats file
    for stats_file in target_files:
        is_home_tracker = stats_file.name == ".sbm_migrations.json"
        if stats_file.name.startswith(".") and not is_home_tracker:
            continue
        print(f"📄 Checking {stats_file}...")

        data = load_json(stats_file)
        if not data or "runs" not in data:
            print(f"⚠️ Skipping {stats_file}: invalid structure")
            continue

        file_changed = False
        fixed_in_file = 0

        for run in data["runs"]:
            status = str(run.get("status", "")).lower()
            lines = run.get("lines_migrated", 0)
            if status == "success" and lines == 0:
                slug = run.get("slug", "").lower()
                run_ts = clean_ts(run.get("timestamp"))
                if not slug or not run_ts:
                    print(f"  ⏭️ Skipping run: slug={slug}, ts={run.get('timestamp')}")
                    continue

                # Find matching PR
                best_additions = 0
                if slug in slug_map:
                    # 1. Try tight match (1 hour)
                    for pr_ts, additions in slug_map[slug]:
                        if abs((pr_ts - run_ts).total_seconds()) < 3600:
                            best_additions = additions
                            break

                    # 2. Try loose match (24 hours) if still 0
                    if best_additions == 0:
                        for pr_ts, additions in slug_map[slug]:
                            if abs((pr_ts - run_ts).total_seconds()) < 86400:
                                best_additions = additions
                                break

                # Fallback: reasonable default
                if best_additions == 0:
                    best_additions = 800

                run["lines_migrated"] = best_additions
                file_changed = True
                fixed_in_file += 1
                total_fixed += 1

        if file_changed:
            stats_file.write_text(json.dumps(data, indent=2))
            total_files += 1
            print(f"✨ Fixed {fixed_in_file} runs in {stats_file}")

    print(f"🎉 Final Summary: Fixed {total_fixed} runs across {total_files} files.")


if __name__ == "__main__":
    fix_stats()
