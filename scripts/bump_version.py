#!/usr/bin/env python3
"""
Automated version bumping script for auto-sbm.
Usage: python scripts/bump_version.py --type [bugfix|feature|major]
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = ROOT / "pyproject.toml"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
README_PATH = ROOT / "README.md"


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


def read_version() -> str:
    if not PYPROJECT_PATH.exists():
        print(f"❌ Error: pyproject.toml not found at {PYPROJECT_PATH}")
        sys.exit(1)

    content = PYPROJECT_PATH.read_text()
    version_match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)

    if not version_match:
        print("❌ Error: Could not find version in pyproject.toml")
        sys.exit(1)

    return version_match.group(1)


def update_pyproject(new_version: str) -> None:
    content = PYPROJECT_PATH.read_text()
    new_content = re.sub(
        r'^version\s*=\s*["\'][^"\']+["\']',
        f'version = "{new_version}"',
        content,
        flags=re.MULTILINE,
    )
    PYPROJECT_PATH.write_text(new_content)
    print(f"✅ Updated {PYPROJECT_PATH}")


def _normalize_notes(raw_notes: str) -> list[str]:
    lines = [line.strip() for line in raw_notes.splitlines() if line.strip()]
    if not lines:
        return []

    normalized = []
    for line in lines:
        if line.startswith("### "):
            normalized.append(line)
        elif line.startswith("- "):
            normalized.append(line)
        else:
            normalized.append(f"- {line}")
    return normalized


def _get_last_changelog_version(changelog_content: str) -> str | None:
    match = re.search(r"^## \[([0-9]+\.[0-9]+\.[0-9]+)\]", changelog_content, re.MULTILINE)
    if match:
        return match.group(1)
    return None


def _git_notes_since(version: str | None) -> list[str]:
    if version:
        tag = f"v{version}"
        tag_check = subprocess.run(
            ["git", "tag", "--list", tag],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        if tag_check.stdout.strip() == tag:
            log_cmd = ["git", "log", "--oneline", f"{tag}..HEAD"]
        else:
            log_cmd = ["git", "log", "--oneline", "-n", "15"]
    else:
        log_cmd = ["git", "log", "--oneline", "-n", "15"]

    result = subprocess.run(
        log_cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return _normalize_notes("\n".join(lines))


def update_changelog(new_version: str, notes: list[str]) -> None:
    if not CHANGELOG_PATH.exists():
        print(f"❌ Error: CHANGELOG.md not found at {CHANGELOG_PATH}")
        sys.exit(1)

    from datetime import date

    today = date.today().isoformat()
    header = f"## [{new_version}] - {today}"

    if not notes:
        print("❌ Error: No changelog notes found. Provide --notes or add commits.")
        sys.exit(1)

    has_heading = any(line.startswith("### ") for line in notes)
    if has_heading:
        entry_lines = [header, ""] + notes
    else:
        entry_lines = [header, "", "### Changed"] + notes

    entry_text = "\n".join(entry_lines) + "\n\n"

    changelog_content = CHANGELOG_PATH.read_text()
    insert_match = re.search(r"^## \[", changelog_content, re.MULTILINE)
    if insert_match:
        insert_at = insert_match.start()
        changelog_content = changelog_content[:insert_at] + entry_text + changelog_content[insert_at:]
    else:
        changelog_content = changelog_content.strip() + "\n\n" + entry_text

    CHANGELOG_PATH.write_text(changelog_content)
    print("✅ Updated CHANGELOG.md")


def update_readme_version(new_version: str) -> None:
    if not README_PATH.exists():
        print(f"⚠️  README.md not found at {README_PATH}. Skipping README update.")
        return

    content = README_PATH.read_text()
    if re.search(r"^Current version:\s*", content, re.MULTILINE):
        updated = re.sub(
            r"^Current version:\s*[0-9]+\.[0-9]+\.[0-9]+\s*$",
            f"Current version: {new_version}",
            content,
            flags=re.MULTILINE,
        )
    else:
        updated = content.strip() + f"\n\nCurrent version: {new_version}\n"

    README_PATH.write_text(updated)
    print("✅ Updated README.md")


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
    parser.add_argument(
        "--notes",
        help="Changelog notes (use \\n for multiple lines).",
    )
    parser.add_argument(
        "--notes-file",
        help="Path to a file containing changelog notes.",
    )
    args = parser.parse_args()

    current_version = read_version()
    new_version = bump_version(current_version, args.type)

    print(f"🚀 Bumping version: {current_version} -> {new_version} ({args.type})")

    if args.dry_run:
        print("✨ Dry run complete. No changes made.")
        return

    notes_raw = ""
    if args.notes_file:
        notes_path = Path(args.notes_file)
        if not notes_path.exists():
            print(f"❌ Error: notes file not found at {notes_path}")
            sys.exit(1)
        notes_raw = notes_path.read_text()
    elif args.notes:
        notes_raw = args.notes.replace("\\n", "\n")
    else:
        changelog_content = CHANGELOG_PATH.read_text() if CHANGELOG_PATH.exists() else ""
        last_version = _get_last_changelog_version(changelog_content)
        notes = _git_notes_since(last_version)
        notes_raw = "\n".join(notes)

    notes = _normalize_notes(notes_raw)

    update_pyproject(new_version)
    update_changelog(new_version, notes)
    update_readme_version(new_version)

    print("\nNext steps:")
    print("1. git add pyproject.toml CHANGELOG.md README.md")
    print(f'2. git commit -m "chore: bump version to {new_version}"')
    print(f"3. git tag v{new_version}")


if __name__ == "__main__":
    main()
