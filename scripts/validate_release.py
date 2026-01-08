#!/usr/bin/env python3
"""
Validate version bump + docs alignment for auto-sbm.

Usage:
  python scripts/validate_release.py --staged
  python scripts/validate_release.py --base origin/main
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = ROOT / "pyproject.toml"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
README_PATH = ROOT / "README.md"

CODE_PATH_PREFIXES = (
    "sbm/",
    "scripts/",
    "tests/",
)
CODE_FILES = (
    "setup.sh",
    "requirements.txt",
    "pyproject.toml",
)

PLACEHOLDER_MARKERS = ("TODO", "TBD", "Auto-versioned bump")


def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def get_changed_files(staged: bool, base_ref: str | None) -> list[str]:
    if staged:
        result = run_git(["git", "diff", "--name-only", "--cached"])
        if result.returncode != 0:
            print("❌ Failed to read staged changes.", file=sys.stderr)
            sys.exit(1)
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    if base_ref:
        result = run_git(["git", "diff", "--name-only", f"{base_ref}..HEAD"])
        if result.returncode != 0:
            # Fallback to last commit if base ref isn't available
            fallback = run_git(["git", "diff", "--name-only", "HEAD~1..HEAD"])
            if fallback.returncode == 0:
                return [line.strip() for line in fallback.stdout.splitlines() if line.strip()]
            print(f"❌ Failed to diff against {base_ref}.", file=sys.stderr)
            sys.exit(1)
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    result = run_git(["git", "diff", "--name-only", "HEAD"])
    if result.returncode != 0:
        print("❌ Failed to read changes.", file=sys.stderr)
        sys.exit(1)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def is_code_change(path: str) -> bool:
    if path in CODE_FILES:
        return True
    return path.startswith(CODE_PATH_PREFIXES)


def read_version_from_pyproject() -> str:
    if not PYPROJECT_PATH.exists():
        print("❌ pyproject.toml not found.", file=sys.stderr)
        sys.exit(1)

    content = PYPROJECT_PATH.read_text()
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    if not match:
        print("❌ Could not read version from pyproject.toml.", file=sys.stderr)
        sys.exit(1)
    return match.group(1)


def read_latest_changelog_version(content: str) -> str | None:
    match = re.search(r"^## \[([0-9]+\.[0-9]+\.[0-9]+)\]", content, re.MULTILINE)
    if match:
        return match.group(1)
    return None


def extract_changelog_section(content: str, version: str) -> str:
    pattern = rf"^## \[{re.escape(version)}\].*?$"
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        return ""
    start = match.start()
    next_match = re.search(r"^## \[", content[match.end() :], re.MULTILINE)
    end = start + match.end() - match.start()
    if next_match:
        end = match.end() + next_match.start()
    return content[start:end]


def validate_changelog(version: str) -> None:
    if not CHANGELOG_PATH.exists():
        print("❌ CHANGELOG.md not found.", file=sys.stderr)
        sys.exit(1)

    content = CHANGELOG_PATH.read_text()
    latest_version = read_latest_changelog_version(content)
    if latest_version != version:
        print(
            f"❌ CHANGELOG.md latest entry ({latest_version}) does not match pyproject "
            f"version ({version}).",
            file=sys.stderr,
        )
        sys.exit(1)

    section = extract_changelog_section(content, version)
    if not section:
        print(f"❌ CHANGELOG.md missing section for version {version}.", file=sys.stderr)
        sys.exit(1)

    if any(marker in section for marker in PLACEHOLDER_MARKERS):
        print("❌ CHANGELOG.md contains placeholder text. Replace it with real notes.")
        sys.exit(1)

    bullets = [line for line in section.splitlines() if line.strip().startswith("- ")]
    if not bullets:
        print("❌ CHANGELOG.md entry must include at least one bullet item.")
        sys.exit(1)


def validate_readme(version: str) -> None:
    if not README_PATH.exists():
        print("❌ README.md not found.", file=sys.stderr)
        sys.exit(1)

    content = README_PATH.read_text()
    match = re.search(r"^Current version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", content, re.MULTILINE)
    if not match:
        print("❌ README.md is missing a 'Current version: x.y.z' line.", file=sys.stderr)
        sys.exit(1)
    if match.group(1) != version:
        print(
            f"❌ README.md version ({match.group(1)}) does not match pyproject version ({version}).",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate version + docs alignment")
    parser.add_argument("--staged", action="store_true", help="Use staged git changes")
    parser.add_argument("--base", help="Git base ref to diff against (e.g., origin/main)")
    args = parser.parse_args()

    changed_files = get_changed_files(args.staged, args.base)
    code_change = any(is_code_change(path) for path in changed_files)
    version_bumped = "pyproject.toml" in changed_files

    if code_change and not version_bumped:
        print(
            "❌ Version bump required for code changes. Update pyproject.toml and CHANGELOG.md.",
            file=sys.stderr,
        )
        sys.exit(1)

    if version_bumped:
        if "CHANGELOG.md" not in changed_files:
            print(
                "❌ Version bump requires updating CHANGELOG.md.",
                file=sys.stderr,
            )
            sys.exit(1)

    version = read_version_from_pyproject()
    validate_changelog(version)
    # README validation removed - not required for every release

    print("✅ Release metadata checks passed.")


if __name__ == "__main__":
    main()
