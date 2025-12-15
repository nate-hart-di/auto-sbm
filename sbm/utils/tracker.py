"""
Simple migration tracking for SBM.

Persists a list of migrated slugs in the user's home directory to avoid
double-counting reruns. Provides helpers to record completions and read stats.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Tuple

from .logger import logger


TRACKER_FILE = Path.home() / ".sbm_migrations.json"


def _read_tracker() -> dict:
    """Read tracker data from disk, returning a default structure on failure."""
    if not TRACKER_FILE.exists():
        return {"migrations": [], "last_updated": None}

    try:
        with TRACKER_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            migrations = data.get("migrations", [])
            if not isinstance(migrations, list):
                migrations = []
            return {
                "migrations": migrations,
                "last_updated": data.get("last_updated"),
            }
    except Exception as e:
        logger.warning(f"Could not read migration tracker; resetting. Error: {e}")
        return {"migrations": [], "last_updated": None}


def _write_tracker(data: dict) -> None:
    """Persist tracker data to disk."""
    try:
        with TRACKER_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to write migration tracker to {TRACKER_FILE}: {e}")


def record_migration(slug: str) -> Tuple[bool, int]:
    """
    Record a completed migration. Returns (added, total_count).

    Args:
        slug: Dealer theme slug that completed migration
    """
    slug = (slug or "").strip()
    if not slug:
        return False, 0

    data = _read_tracker()
    migrations = set(data.get("migrations", []))

    added = slug not in migrations
    migrations.add(slug)

    updated = {
        "migrations": sorted(migrations),
        "last_updated": datetime.utcnow().isoformat() + "Z",
    }

    _write_tracker(updated)
    return added, len(migrations)


def get_migration_stats() -> dict:
    """Return tracker stats with count and slug list."""
    data = _read_tracker()
    migrations = data.get("migrations", [])
    return {
        "count": len(migrations),
        "migrations": migrations,
        "last_updated": data.get("last_updated"),
        "path": str(TRACKER_FILE),
    }
