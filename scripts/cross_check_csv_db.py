#!/usr/bin/env python3
"""
Cross-check CSV export against Firebase database.
Extracts slugs from Dev URL column and compares to verified runs.
Uses prefix matching to handle truncated slugs in CSV.
"""

import csv
import os
import sys
from urllib.parse import urlparse

sys.path.append(os.getcwd())
from dotenv import load_dotenv

load_dotenv()

import firebase_admin
from firebase_admin import credentials, db

from sbm.config import get_settings


def extract_slug_from_dev_url(dev_url: str) -> str | None:
    """Extract slug from Dev URL - everything before the first hyphen in the subdomain."""
    if not dev_url or not isinstance(dev_url, str):
        return None

    dev_url = dev_url.strip()
    if not dev_url:
        return None

    if not dev_url.startswith("http"):
        dev_url = "https://" + dev_url

    try:
        parsed = urlparse(dev_url)
        hostname = parsed.netloc or parsed.path.split("/")[0]
        subdomain = hostname.split(".")[0]

        if "-" in subdomain:
            slug = subdomain.split("-")[0]
        else:
            slug = subdomain

        return slug.lower() if slug else None
    except Exception:
        return None


def load_csv_slugs(csv_path: str) -> dict[str, dict]:
    """Load CSV and extract slugs from Dev URL column."""
    slugs = {}

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dev_url = row.get("Dev URL", "")
            account_name = row.get("Account: Account Name", "")
            site_developer = row.get("Site Developer", "")
            status = row.get("Status", "")

            slug = extract_slug_from_dev_url(dev_url)
            if slug and slug not in ["www", ""]:
                slugs[slug] = {
                    "account": account_name,
                    "developer": site_developer,
                    "status": status,
                    "dev_url": dev_url,
                }

    return slugs


def load_firebase_slugs() -> dict[str, dict]:
    """Load all verified runs from Firebase."""
    try:
        app = firebase_admin.get_app()
    except ValueError:
        settings = get_settings()
        if not settings.firebase.credentials_path or not settings.firebase.database_url:
            print("Error: Firebase credentials not found.")
            return {}
        cred = credentials.Certificate(settings.firebase.credentials_path)
        firebase_admin.initialize_app(cred, {"databaseURL": settings.firebase.database_url})

    ref = db.reference("users")
    users_data = ref.get()

    if not users_data:
        return {}

    slugs = {}
    for user_id, data in users_data.items():
        if not isinstance(data, dict):
            continue
        runs = data.get("runs", {})
        if isinstance(runs, list):
            run_items = enumerate(runs)
        else:
            run_items = runs.items()

        for _, run in run_items:
            if not isinstance(run, dict):
                continue

            if run.get("status") != "success":
                continue
            lines = run.get("lines_migrated", 0)
            if not lines or lines <= 0:
                continue
            pr_url = run.get("pr_url", "")
            if not pr_url or "github.com" not in str(pr_url):
                continue

            slug = run.get("slug", "").lower()
            if slug:
                slugs[slug] = {
                    "user": user_id,
                    "lines": lines,
                    "pr_url": pr_url,
                    "timestamp": run.get("timestamp", ""),
                }

    return slugs


def find_prefix_matches(csv_slugs: dict, db_slugs: dict) -> dict:
    """Find DB slugs that start with truncated CSV slugs."""
    matches = {}  # csv_slug -> db_slug

    for csv_slug in csv_slugs:
        # Exact match first
        if csv_slug in db_slugs:
            matches[csv_slug] = csv_slug
        else:
            # Find DB slugs that start with the CSV slug (truncated match)
            for db_slug in db_slugs:
                if db_slug.startswith(csv_slug):
                    matches[csv_slug] = db_slug
                    break

    return matches


def main():
    csv_path = "/Users/nathanhart/auto-sbm/data/sbms-07.1.25-to-present.csv"

    print("Loading CSV slugs...")
    csv_slugs = load_csv_slugs(csv_path)
    print(f"  Found {len(csv_slugs)} unique slugs in CSV")

    print("\nLoading Firebase slugs...")
    db_slugs = load_firebase_slugs()
    print(f"  Found {len(db_slugs)} verified slugs in Firebase")

    # Do prefix matching
    print("\nMatching (exact + prefix)...")
    matches = find_prefix_matches(csv_slugs, db_slugs)

    matched_csv = set(matches.keys())
    matched_db = set(matches.values())

    unmatched_csv = set(csv_slugs.keys()) - matched_csv
    unmatched_db = set(db_slugs.keys()) - matched_db

    print(f"\n{'=' * 70}")
    print("CROSS-CHECK RESULTS (with prefix matching for truncated slugs)")
    print(f"{'=' * 70}")
    print(f"Matched (CSV→DB):               {len(matches)}")
    print(f"In CSV but NOT in DB:           {len(unmatched_csv)}")
    print(f"In DB but NOT in CSV:           {len(unmatched_db)}")

    if unmatched_csv:
        print(f"\n{'=' * 70}")
        print(f"TRULY MISSING: In CSV but NOT in Database ({len(unmatched_csv)})")
        print(f"{'=' * 70}")
        for slug in sorted(unmatched_csv):
            info = csv_slugs[slug]
            print(f"  {slug:<50} | {info['developer']:<20} | {info['status']}")

    if unmatched_db:
        print(f"\n{'=' * 70}")
        print(f"EXTRA IN DB: In Database but NOT in CSV ({len(unmatched_db)})")
        print(f"{'=' * 70}")
        for slug in sorted(unmatched_db):
            info = db_slugs[slug]
            print(f"  {slug:<50} | {info['user']:<20} | {info['lines']} lines")

    # Show truncation matches for reference
    truncation_matches = {k: v for k, v in matches.items() if k != v}
    if truncation_matches:
        print(f"\n{'=' * 70}")
        print(f"TRUNCATION MATCHES: CSV slug matched to longer DB slug ({len(truncation_matches)})")
        print(f"{'=' * 70}")
        for csv_slug, db_slug in sorted(truncation_matches.items()):
            print(f"  {csv_slug:<40} → {db_slug}")

    print(f"\n{'=' * 70}")
    print("FINAL SUMMARY")
    print(f"{'=' * 70}")
    print(f"CSV Total:              {len(csv_slugs)}")
    print(f"DB Verified Total:      {len(db_slugs)}")
    print(f"Matched:                {len(matches)}")
    print(f"Truly Missing (CSV→DB): {len(unmatched_csv)}")
    print(f"Extra in DB:            {len(unmatched_db)}")

    if unmatched_db:
        print("\n" + "=" * 70)
        print(f"EXTRA IN DB DETAILS ({len(unmatched_db)}) - POTENTIAL ARCHIVE CANDIDATES")
        print("=" * 70)
        print(f"{'Slug':<40} | {'User':<20} | {'Timestamp'}")
        print("-" * 80)

        extras_details = []
        for slug in unmatched_db:
            info = db_slugs[slug]
            extras_details.append((slug, info["user"], info["timestamp"]))

        # Sort by timestamp
        extras_details.sort(key=lambda x: x[2])

        for slug, user, ts in extras_details:
            print(f"{slug:<40} | {user:<20} | {ts}")


if __name__ == "__main__":
    main()
