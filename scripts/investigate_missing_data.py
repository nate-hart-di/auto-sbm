#!/usr/bin/env python3
"""
Investigate 32 missing SBM runs by checking GitHub for valid PRs.
Uses `gh` CLI to search for merged PRs matching the slugs.
"""

import json
import subprocess
import time

MISSING_SLUGS = [
    "aberdeenchryslercenter",
    "armbrustermotorcompany",
    "berlincitydodgechryslerjeepram",
    "bluebonnetchryslerdodge",
    "breedendodgechryslerjeepram",
    "budclarymoseslakechryslerdodgejeepr",
    "burrittcdjr",
    "crowleychryslerjeepdodgeram",
    "deweycdjr",
    "flowermotorcompany",
    "helfmandodgechryslerjeep",
    "kengarffwestvalley",
    "landerschryslerdodgejeepramofnorman",
    "lundgrendodgeramofrutland",
    "lutherbrookdalechryslerjeepdodgeram",
    "lutherhudsonchryslerdodgejeepram",
    "machaikdodgechryslerjeepram1",
    "maseratiofstpete",
    "miraclechryslerdodgejeepram",
    "olympiajeep",
    "portagechryslerdodgejeepram",
    "rontonkinchryslercjdrf",
    "samlemanchryslerjeepdodgemorton",
    "samlemanchryslerjeepdodgeofpeoria",
    "southtowncdjr",
    "sterlingkiaoflafayette",
    "stevelanderschryslerdodgejeepram",
    "stewhansenchryslerjeepdodgeram",
    "texancdjr",
    "thomasautocenter",
    "uftringcdj",
    "zimmerchryslerdodgejeepram",
]


def search_pr(slug):
    """Search for all merged PRs for the given slug."""
    # Target the dealer-themes repo
    cwd = "/Users/nathanhart/di-websites-platform/dealer-themes"
    try:
        # Search for slug in title, merged state
        cmd = [
            "gh",
            "pr",
            "list",
            "--search",
            f"{slug} in:title",
            "--state",
            "merged",
            "--json",
            "title,url,createdAt,author",
            "--limit",
            "100",  # Get more PRs to find the original migration
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=cwd)
        prs = json.loads(result.stdout)
        return prs
    except subprocess.CalledProcessError as e:
        print(f"Error searching for {slug}: {e.stderr}")
        return []
    except FileNotFoundError:
        print(f"Error: Directory {cwd} not found.")
        return []


def is_sbm_migration(title):
    """Check if PR title matches SBM migration patterns."""
    # Strict patterns
    if "SBM FE Audit" in title:
        return True  # strict case

    # Other indicators (case sensitive or specific)
    # The user mentioned "New PR pattern is obviously what it is now"
    # Typically [Slug] SBM Migration ...

    title_lower = title.lower()
    # If it says "sbm" and "audit" but lowercase, user says INVALID/MANUAL?
    # "MANUAL/INVALID: lundgrendodgeramofrutland sbm fe audit"

    # Let's trust "SBM" in caps as a strong signal + "Migration" or "Archive"
    if "SBM" in title:
        return True
    if "Archive" in title:
        return True
    if "Migrat" in title:
        return True  # catches Migration, Migrated

    return False


def main():
    print(f"Investigating {len(MISSING_SLUGS)} missing slugs (checking all PRs)...")

    verified_sbm = []
    potential_matches = []
    not_found = []

    for slug in MISSING_SLUGS:
        print(f"Checking {slug}...", end="", flush=True)
        prs = search_pr(slug)

        if not prs:
            print(" NO PR FOUND")
            not_found.append(slug)
            continue

        # Sort by date usually helps context, but we want to find THE match
        # Let's look for the best match
        found_match = False
        candidates = []

        for pr in prs:
            if is_sbm_migration(pr["title"]):
                verified_sbm.append((slug, pr))
                print(f" FOUND SBM: {pr['title']}")
                found_match = True
                break
            candidates.append(pr)

        if not found_match:
            # If no strict SBM match, list the oldest PR (often the creation/migration)
            # or the one that looks most like a setup
            best_candidate = sorted(candidates, key=lambda x: x["createdAt"])[
                0
            ]  # Oldest might be migration?
            potential_matches.append((slug, best_candidate, len(candidates)))
            print(f" POTENTIAL: {best_candidate['title']}")

        time.sleep(1)

    print("\n" + "=" * 60)
    print("INVESTIGATION REPORT (Strict Pattern Matching)")
    print("=" * 60)

    if verified_sbm:
        print(f"\n✅ VERIFIED SBM MIGRATIONS ({len(verified_sbm)})")
        for slug, pr in verified_sbm:
            print(f"  {slug:<40} | {pr['author']['login']:<15} | {pr['url']}")
            print(f"    Title: {pr['title']}")

    if potential_matches:
        print(f"\n⚠️  NO STRICT SBM MATCH - BEST GUESSES ({len(potential_matches)})")
        for slug, pr, count in potential_matches:
            print(f"  {slug:<40} | {pr['author']['login']:<15} | {pr['url']}")
            print(f"    Title: {pr['title']} (found {count} total PRs)")

    if not_found:
        print(f"\n❌ NO PR FOUND ({len(not_found)})")
        for slug in not_found:
            print(f"  {slug}")


if __name__ == "__main__":
    main()
