"""
Versioning utilities for auto-sbm.
Parses pyproject.toml to get the source of truth for the version.
"""

from __future__ import annotations

import functools
import re
from pathlib import Path


@functools.lru_cache(maxsize=1)
def get_version() -> str:
    """
    Get the project version from pyproject.toml.

    Returns:
        The version string (e.g., "2.0.0")
    """
    # Find the root directory (where pyproject.toml lives)
    # Strategy: look for pyproject.toml from the current file's parent
    current = Path(__file__).resolve().parent
    while current.parent != current:
        pyproject_path = current / "pyproject.toml"
        if pyproject_path.exists():
            break
        current = current.parent
    else:
        # Fallback to home directory if not found in parent hierarchy
        pyproject_path = Path.home() / "auto-sbm" / "pyproject.toml"

    if not pyproject_path.exists():
        return "Unknown"

    try:
        content = pyproject_path.read_text()
        # Simple regex to extract version from [project] section
        # More robust than full toml parsing for a single field
        version_match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
        if version_match:
            return version_match.group(1)
    except Exception:
        pass

    return "Unknown"


def get_changelog(since_version: str | None = None) -> str:
    """
    Generate or read a changelog.
    Prioritizes CHANGELOG.md if it exists, otherwise falls back to git history.

    Args:
        since_version: Optional version tag to start from.

    Returns:
        A formatted changelog string.
    """
    import subprocess

    repo_root = Path(__file__).resolve().parent.parent.parent

    # Try reading from CHANGELOG.md first
    changelog_path = repo_root / "CHANGELOG.md"
    if changelog_path.exists():
        try:
            content = changelog_path.read_text()
            # If limited entries requested, just return the first few versions
            if not since_version:
                # Get everything up to the first few ## versions
                versions = re.split(r"\n(?=## \[)", content)
                return "\n".join(versions[:3]).strip()
            return content.strip()
        except Exception:
            pass

    # Fallback to git log
    try:
        # Get commit history since the beginning or a specific point
        cmd = ["git", "log", "--oneline", "--no-decorate"]
        if since_version:
            cmd.append(f"{since_version}..HEAD")
        else:
            cmd.append("-n 10")  # Last 10 changes by default

        result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        return f"Could not retrieve changelog: {e}"

    return "No changelog entries found."
