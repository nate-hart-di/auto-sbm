#!/usr/bin/env python3
"""
Automated version bumping script for auto-sbm.
Usage: python scripts/bump_version.py --type [bugfix|feature|major]
"""

import argparse
import re
import sys
from pathlib import Path


def bump_version(current_version: str, bump_type: str) -> str:
    """Increment version based on type."""
    major, minor, patch = map(int, current_version.split("."))

    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "feature":
        minor += 1
        patch = 0
    elif bump_type == "bugfix":
        patch += 1
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")

    return f"{major}.{minor}.{patch}"


def main():
    parser = argparse.ArgumentParser(description="Bump auto-sbm version")
    parser.add_argument(
        "--type",
        choices=["bugfix", "feature", "major"],
        required=True,
        help="Type of version bump",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show changes without applying them",
    )
    args = parser.parse_args()

    # Find pyproject.toml
    root_dir = Path(__file__).resolve().parent.parent
    pyproject_path = root_dir / "pyproject.toml"

    if not pyproject_path.exists():
        print(f"❌ Error: pyproject.toml not found at {pyproject_path}")
        sys.exit(1)

    # Read current version
    content = pyproject_path.read_text()
    version_match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)

    if not version_match:
        print("❌ Error: Could not find version in pyproject.toml")
        sys.exit(1)

    current_version = version_match.group(1)
    new_version = bump_version(current_version, args.type)

    print(f"🚀 Bumping version: {current_version} -> {new_version} ({args.type})")

    if args.dry_run:
        print("✨ Dry run complete. No changes made.")
        return

    # Update pyproject.toml
    new_content = re.sub(
        r'^version\s*=\s*["\'][^"\']+["\']',
        f'version = "{new_version}"',
        content,
        flags=re.MULTILINE,
    )
    pyproject_path.write_text(new_content)

    print(f"✅ Updated {pyproject_path}")

    # Optional: Update CHANGELOG.md if it exists
    changelog_path = root_dir / "CHANGELOG.md"
    if changelog_path.exists():
        print("📝 Updating CHANGELOG.md...")
        # Add a placeholder for the new version
        from datetime import date

        today = date.today().isoformat()
        changelog_header = (
            f"\n## [{new_version}] - {today}\n\n### Changed\n- Auto-versioned bump ({args.type})\n"
        )

        changelog_content = changelog_path.read_text()
        # Insert after the main header
        if "# Changelog" in changelog_content:
            changelog_content = changelog_content.replace(
                "# Changelog", f"# Changelog\n{changelog_header}"
            )
        else:
            changelog_content = f"# Changelog\n{changelog_header}\n" + changelog_content

        changelog_path.write_text(changelog_content)
        print("✅ Updated CHANGELOG.md")

    print("\nNext steps:")
    print(f"1. git add pyproject.toml" + (" CHANGELOG.md" if changelog_path.exists() else ""))
    print(f'2. git commit -m "chore: bump version to {new_version}"')
    print(f"3. git tag v{new_version}")


if __name__ == "__main__":
    main()
