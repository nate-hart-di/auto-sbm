#!/usr/bin/env python3
"""
Cross-check Salesforce historic-runs.csv against Firebase database.

This script:
1. Parses the Salesforce CSV export
2. Extracts slugs from website URLs
3. Compares against Firebase migrations and runs
4. Reports any discrepancies
"""

import csv
import os

from sbm.utils.firebase_sync import get_firebase_ref


def extract_slug_from_url(url):
    """Extract slug from a URL."""
    if not url or not isinstance(url, str):
        return None

    # Clean up URL
    url = url.strip().lower()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        import re
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc

        # Remove www.
        if domain.startswith("www."):
            domain = domain[4:]

        # Extract first part before .com, .net, etc
        # e.g., "maseratiofpuentehills.com" -> "maseratiofpuentehills"
        slug = re.split(r"\.", domain)[0]
        return slug if slug else None
    except:
        return None


def main():
    # Use existing firebase_sync module initialization
    ref = get_firebase_ref()
    if ref is None:
        print("❌ Failed to initialize Firebase")
        print("   Check Firebase credentials in ~/auto-sbm/.env")
        return

    # Read Salesforce CSV
    csv_path = "/Users/nathanhart/auto-sbm/data/historic-runs.csv"

    if not os.path.exists(csv_path):
        print(f"❌ CSV file not found: {csv_path}")
        return

    print("📊 Parsing Salesforce CSV...")
    salesforce_records = []

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("Account: Website", "").strip()
            web_id = row.get("Website Record: Website #", "").strip()
            account_name = row.get("Account: Account Name", "").strip()
            stage = row.get("Stage", "").strip()

            # Only include "Transitioned" sites (live migrations)
            if stage != "Transitioned":
                continue

            slug = extract_slug_from_url(url)
            if slug:
                salesforce_records.append(
                    {
                        "slug": slug,
                        "url": url,
                        "web_id": web_id,
                        "account_name": account_name,
                        "stage": stage,
                    }
                )

    print(f"✅ Found {len(salesforce_records)} Transitioned sites in Salesforce CSV")

    # Get all Firebase data
    print("\n🔥 Fetching Firebase data...")
    ref = db.reference()
    all_data = ref.get() or {}

    # Track Firebase migrations
    firebase_slugs = set()

    for user_id, user_data in all_data.items():
        if not isinstance(user_data, dict):
            continue

        # Get migrations list (legacy)
        migrations = user_data.get("migrations", [])
        if isinstance(migrations, list):
            firebase_slugs.update(migrations)

        # Get runs (current system)
        runs = user_data.get("runs", {})
        if isinstance(runs, dict):
            for run_id, run in runs.items():
                if not isinstance(run, dict):
                    continue

                slug = run.get("slug")
                status = run.get("status")

                # Only count successful runs
                if slug and status == "success":
                    firebase_slugs.add(slug)

    print(f"✅ Found {len(firebase_slugs)} unique slugs in Firebase")

    # Compare
    print("\n🔍 Cross-checking...")
    salesforce_slugs = {r["slug"] for r in salesforce_records}

    in_salesforce_not_firebase = salesforce_slugs - firebase_slugs
    in_firebase_not_salesforce = firebase_slugs - salesforce_slugs
    in_both = salesforce_slugs & firebase_slugs

    print("\n📈 RESULTS:")
    print(f"  • In both systems: {len(in_both)}")
    print(f"  • In Salesforce only: {len(in_salesforce_not_firebase)}")
    print(f"  • In Firebase only: {len(in_firebase_not_salesforce)}")

    if in_salesforce_not_firebase:
        print(f"\n⚠️  MISSING FROM FIREBASE ({len(in_salesforce_not_firebase)} sites):")
        for slug in sorted(in_salesforce_not_firebase):
            # Find the record
            record = next((r for r in salesforce_records if r["slug"] == slug), None)
            if record:
                print(f"  • {slug:40s} | {record['web_id']:15s} | {record['account_name']}")

    if in_firebase_not_salesforce:
        print(
            f"\n📝 IN FIREBASE BUT NOT IN SALESFORCE CSV ({len(in_firebase_not_salesforce)} sites):"
        )
        for slug in sorted(list(in_firebase_not_salesforce)[:20]):  # Show first 20
            print(f"  • {slug}")
        if len(in_firebase_not_salesforce) > 20:
            print(f"  ... and {len(in_firebase_not_salesforce) - 20} more")

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY:")
    print(f"  Salesforce 'Transitioned' sites: {len(salesforce_slugs)}")
    print(f"  Firebase successful migrations: {len(firebase_slugs)}")
    print(
        f"  Coverage: {len(in_both) / len(salesforce_slugs) * 100:.1f}%"
        if salesforce_slugs
        else "  Coverage: N/A"
    )
    print(f"  Status: {'✅ COMPLETE' if not in_salesforce_not_firebase else '⚠️  NEEDS ATTENTION'}")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
