#!/usr/bin/env python3
"""
Backfill historical stats where lines_migrated = 0.

This script fixes the bug where lines_migrated was always recorded as 0
from approximately Jan 6-9, 2026. Uses a default of 800 lines per migration
(the standard used in time savings calculations: 1 hour per 800 lines).
"""

import json
from pathlib import Path

# Project Root
ROOT_DIR = Path(__file__).parent.parent.parent.resolve()
STATS_DIR = ROOT_DIR / "stats"
DEFAULT_LINES = 800  # Standard assumption: 800 lines per migration


def backfill_stats():
    """Fix stats files where lines_migrated = 0 for successful runs."""
    print("🔍 Backfilling historical stats with lines_migrated = 0...")

    total_fixed = 0
    total_files = 0

    # Process each stats file in the stats directory
    target_files = list(STATS_DIR.glob("*.json"))

    # Also include the home directory tracker
    home_tracker = Path.home() / ".sbm_migrations.json"
    if home_tracker.exists():
        target_files.append(home_tracker)

    for stats_file in target_files:
        if stats_file.name.startswith("."):
            continue

        print(f"📄 Processing {stats_file.name}...")

        try:
            data = json.loads(stats_file.read_text())
        except Exception as e:
            print(f"⚠️  Skipping {stats_file.name}: {e}")
            continue

        if "runs" not in data:
            print(f"⚠️  Skipping {stats_file.name}: no runs found")
            continue

        file_changed = False
        fixed_in_file = 0

        for run in data["runs"]:
            # Only fix successful runs with 0 lines
            status = run.get("status", "").lower()
            lines = run.get("lines_migrated", 0)

            if status == "success" and lines == 0:
                run["lines_migrated"] = DEFAULT_LINES
                file_changed = True
                fixed_in_file += 1
                total_fixed += 1

        if file_changed:
            stats_file.write_text(json.dumps(data, indent=2) + "\n")
            total_files += 1
            print(f"  ✨ Fixed {fixed_in_file} runs")

    print(f"\n🎉 Done! Fixed {total_fixed} runs across {total_files} files.")
    print(f"   Default: {DEFAULT_LINES} lines per migration")


if __name__ == "__main__":
    backfill_stats()
