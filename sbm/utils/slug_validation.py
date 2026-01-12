import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional

from sbm.utils.helpers import is_valid_slug

_CACHE_PATH = Path.home() / ".sbm_slug_validation.json"
_CACHE_TTL_DAYS = 30
_DEFAULT_DEVTOOLS_DIR = Path(
    "/Users/nathanhart/code/dealerinspire/feature-dev-shared-scripts/devtools-cli"
)


def _normalize_slug(slug: str) -> str:
    return slug.strip().lower()


def _find_devtools_script() -> Optional[Path]:
    env_value = os.environ.get("DEVTOOLS_CLI_PATH")
    if env_value:
        try:
            env_path = Path(env_value).expanduser()
            if env_path.is_dir():
                candidate = env_path / "devtools"
                if candidate.exists():
                    return candidate
            elif env_path.exists():
                return env_path
        except Exception:
            pass

    if (_DEFAULT_DEVTOOLS_DIR / "devtools").exists():
        return _DEFAULT_DEVTOOLS_DIR / "devtools"

    try:
        import shutil

        found = shutil.which("devtools")
        if found:
            return Path(found)
    except Exception:
        return None

    return None


def _load_cache() -> dict:
    if not _CACHE_PATH.exists():
        return {"version": 1, "slugs": {}}
    try:
        return json.loads(_CACHE_PATH.read_text())
    except Exception:
        return {"version": 1, "slugs": {}}


def _save_cache(cache: dict) -> None:
    try:
        _CACHE_PATH.write_text(json.dumps(cache, indent=2))
    except Exception:
        return


def _is_cache_fresh(entry: dict) -> bool:
    try:
        checked_at = datetime.fromisoformat(entry["checked_at"])
    except Exception:
        return False
    return checked_at >= datetime.now(timezone.utc) - timedelta(days=_CACHE_TTL_DAYS)


def _parse_devtools_output(output: str) -> list[dict]:
    lines = output.split("\n")
    json_lines = []
    in_json = False
    for line in lines:
        clean_line = re.sub(r"\x1b\[[0-9;]*m", "", line)
        if clean_line.strip().startswith("[") or clean_line.strip().startswith("{"):
            in_json = True
        if in_json:
            json_lines.append(clean_line)

    if not json_lines:
        return []

    try:
        data = json.loads("\n".join(json_lines))
    except json.JSONDecodeError:
        return []

    if isinstance(data, dict) and "message" in data:
        return []
    if not isinstance(data, list):
        return []
    return data


def _devtools_slug_valid(slug: str) -> Optional[bool]:
    devtools_script = _find_devtools_script()
    if not devtools_script:
        return None

    try:
        result = subprocess.run(
            ["bash", str(devtools_script), "search", slug],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(devtools_script.parent),
        )
    except Exception:
        return None

    if result.returncode != 0:
        return None

    data = _parse_devtools_output(result.stdout)
    if not data:
        return False

    slug_norm = _normalize_slug(slug)
    for item in data:
        item_slug = item.get("slug")
        if item_slug and _normalize_slug(item_slug) == slug_norm:
            return True
    return False


def is_official_slug(slug: str) -> Optional[bool]:
    """Return True/False if verified, or None if verification unavailable."""
    if not slug:
        return False
    slug_norm = _normalize_slug(slug)
    if not is_valid_slug(slug_norm):
        return False

    cache = _load_cache()
    entry = cache.get("slugs", {}).get(slug_norm)
    if entry and _is_cache_fresh(entry):
        return bool(entry.get("valid"))

    valid = _devtools_slug_valid(slug_norm)
    if valid is None:
        return None

    cache.setdefault("slugs", {})[slug_norm] = {
        "valid": bool(valid),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_cache(cache)
    return bool(valid)


def filter_valid_slugs(slugs: Iterable[str]) -> list[str]:
    """Filter to slugs validated by devtools when available."""
    slugs_list = [s for s in slugs if s]
    if not slugs_list:
        return []

    has_devtools = _find_devtools_script() is not None
    if not has_devtools:
        return slugs_list

    valid_slugs = []
    for slug in slugs_list:
        valid = is_official_slug(slug)
        if valid:
            valid_slugs.append(slug)
    return valid_slugs


def filter_valid_runs(runs: Iterable[dict]) -> list[dict]:
    """Filter run list to only official slugs when verification is available."""
    runs_list = list(runs)
    if not runs_list:
        return []

    has_devtools = _find_devtools_script() is not None
    if not has_devtools:
        return runs_list

    filtered = []
    for run in runs_list:
        slug = run.get("slug")
        if is_official_slug(slug):
            filtered.append(run)
    return filtered
