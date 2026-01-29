"""
Firebase Realtime Database synchronization module for SBM.

Provides initialization and utility functions for Firebase Admin SDK.
Part of Epic 2: Robust Team-Wide Synchronization.

Usage:
    from sbm.utils.firebase_sync import get_firebase_db, is_firebase_available

    if is_firebase_available():
        db = get_firebase_db()
        # Use db.reference() for database operations
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from sbm.config import get_settings
from sbm.utils.logger import logger

if TYPE_CHECKING:
    from firebase_admin import App
    from firebase_admin import db as firebase_db

# Module-level state for lazy initialization
_firebase_app: App | None = None
_firebase_initialized: bool = False
_firebase_user_mode: bool = False
_initialization_lock = threading.Lock()
_auth_lock = threading.Lock()
_auth_cache_path = Path.home() / ".sbm_firebase_auth.json"
_user_auth_state = {
    "id_token": None,
    "refresh_token": None,
    "local_id": None,
    "expires_at": 0.0,
    "api_key": None,
}


class FirebaseInitializationError(Exception):
    """Raised when Firebase initialization fails."""


def _initialize_firebase() -> bool:
    """
    Initialize Firebase Admin SDK with appropriate authentication mode.

    Story 2.7: Two authentication modes:
    - Admin Mode: Service account credentials (full read/write access)
    - User Mode: Anonymous Auth via database URL only (runs can still be written)

    Returns:
        True if initialization successful, False otherwise.

    This function is thread-safe and idempotent - multiple calls are safe.
    """
    global _firebase_app, _firebase_initialized, _firebase_user_mode

    # Quick check without lock
    if _firebase_initialized:
        return _firebase_user_mode or _firebase_app is not None

    with _initialization_lock:
        # Double-check after acquiring lock
        if _firebase_initialized:
            return _firebase_user_mode or _firebase_app is not None

        try:
            settings = get_settings()

            # Check if Firebase is configured (database_url is required)
            if not settings.firebase.is_configured():
                logger.debug("Firebase not configured - database_url missing")
                _firebase_initialized = True
                return False

            # Determine authentication mode
            if settings.firebase.is_user_mode():
                # User Mode: No SDK initialization needed for REST usage
                # We return True to indicate "connection" is ready (via REST)
                logger.debug("Initializing Firebase in USER MODE (REST API) - No SDK required")
                _firebase_app = None  # Explicitly None
                _firebase_initialized = True
                _firebase_user_mode = True
                return True

            # Admin Mode: Use service account credentials -> Requires firebase-admin SDK
            try:
                import firebase_admin
                from firebase_admin import credentials
            except ImportError as e:
                logger.warning(
                    "firebase-admin package not installed. Install with: pip install firebase-admin"
                )
                _firebase_initialized = True
                # Only raise if we are in Admin Mode where it is required
                raise FirebaseInitializationError(
                    "firebase-admin package not installed (required for Admin Mode)"
                ) from e

            # Check if already initialized (happens during testing or reload)
            if firebase_admin._apps:
                _firebase_app = firebase_admin.get_app()
                _firebase_initialized = True
                logger.debug("Firebase already initialized, reusing existing app")
                return True

            # Admin Mode: Use service account credentials
            if settings.firebase.is_admin_mode():
                cred = credentials.Certificate(str(settings.firebase.credentials_path))
                _firebase_app = firebase_admin.initialize_app(
                    cred,
                    {
                        "databaseURL": settings.firebase.database_url,
                    },
                )
                logger.debug("Firebase initialized (Admin Mode: full access)")
                _firebase_user_mode = False

            _firebase_initialized = True
            return True

        except FirebaseInitializationError:
            # Re-raise initialization errors (e.g. missing package)
            raise
        except FileNotFoundError as e:
            logger.warning(f"Firebase credentials file not found: {e}")
            _firebase_initialized = True
            return False
        except ValueError as e:
            logger.warning(f"Invalid Firebase credentials: {e}")
            _firebase_initialized = True
            return False
        except Exception as e:
            logger.warning(f"Firebase initialization failed: {e}")
            _firebase_initialized = True
            return False


def _load_auth_cache() -> dict:
    if not _auth_cache_path.exists():
        return {}
    try:
        return json.loads(_auth_cache_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_auth_cache(cache: dict) -> None:
    try:
        _auth_cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except Exception:
        return


def _get_user_mode_identity() -> tuple[str, str] | None:
    """
    Return (uid, id_token) for user mode using anonymous auth.

    Persists refresh token to avoid creating a new UID each run.
    """
    settings = get_settings()
    api_key = settings.firebase.api_key
    if not api_key:
        logger.warning("Firebase API key missing; anonymous auth is unavailable.")
        return None

    now = time.time()
    with _auth_lock:
        if (
            _user_auth_state["id_token"]
            and _user_auth_state["api_key"] == api_key
            and now < _user_auth_state["expires_at"] - 60
            and _user_auth_state["local_id"]
        ):
            return _user_auth_state["local_id"], _user_auth_state["id_token"]

        cache = _load_auth_cache()
        if cache and cache.get("api_key") == api_key:
            expires_at = cache.get("expires_at", 0.0)
            if cache.get("id_token") and now < expires_at - 60 and cache.get("local_id"):
                _user_auth_state.update(cache)
                return cache["local_id"], cache["id_token"]

            refresh_token = cache.get("refresh_token")
            if refresh_token:
                try:
                    import requests

                    resp = requests.post(
                        f"https://securetoken.googleapis.com/v1/token?key={api_key}",
                        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
                        timeout=10,
                    )
                    if resp.ok:
                        data = resp.json()
                        expires_in = int(data.get("expires_in", "3600"))
                        _user_auth_state.update(
                            {
                                "id_token": data.get("id_token"),
                                "refresh_token": data.get("refresh_token"),
                                "local_id": data.get("user_id"),
                                "expires_at": now + expires_in,
                                "api_key": api_key,
                            }
                        )
                        _save_auth_cache(_user_auth_state)
                        return _user_auth_state["local_id"], _user_auth_state["id_token"]
                    else:
                        logger.warning(
                            "Firebase token refresh failed: %s %s",
                            resp.status_code,
                            resp.text[:200],
                        )
                except Exception as e:
                    logger.debug(f"Firebase token refresh failed: {e}")

        try:
            import requests

            resp = requests.post(
                f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={api_key}",
                json={"returnSecureToken": True},
                timeout=10,
            )
            if resp.ok:
                data = resp.json()
                expires_in = int(data.get("expiresIn", "3600"))
                _user_auth_state.update(
                    {
                        "id_token": data.get("idToken"),
                        "refresh_token": data.get("refreshToken"),
                        "local_id": data.get("localId"),
                        "expires_at": now + expires_in,
                        "api_key": api_key,
                    }
                )
                _save_auth_cache(_user_auth_state)
                return _user_auth_state["local_id"], _user_auth_state["id_token"]
            else:
                logger.warning(
                    "Firebase anonymous auth failed: %s %s",
                    resp.status_code,
                    resp.text[:200],
                )
        except Exception as e:
            logger.debug(f"Firebase anonymous auth failed: {e}")

    return None


def get_user_mode_identity() -> tuple[str, str] | None:
    """Public accessor for user-mode auth identity."""
    return _get_user_mode_identity()


def is_firebase_available() -> bool:
    """
    Check if Firebase is available and properly configured.

    Returns:
        True if Firebase can be used for sync operations, False otherwise.

    This function will attempt to initialize Firebase if not already done.
    It's safe to call repeatedly - initialization only happens once.
    """
    try:
        return _initialize_firebase()
    except FirebaseInitializationError:
        return False


def get_firebase_db() -> "firebase_db":
    """
    Get the Firebase Realtime Database reference module.
    Only available in Admin Mode.

    Returns:
        The firebase_admin.db module for database operations.

    Raises:
        FirebaseInitializationError: If Firebase is not available or not in Admin Mode.
    """
    if not is_firebase_available():
        # ... logic ...
        msg = "Firebase not available."
        raise FirebaseInitializationError(msg)

    settings = get_settings()
    if not settings.firebase.is_admin_mode():
        raise FirebaseInitializationError("get_firebase_db() is only available in Admin Mode")

    # Import db module (guaranteed to work if initialization succeeded for Admin)
    from firebase_admin import db

    return db


def check_for_firebase_admin_package() -> bool:
    try:
        import firebase_admin

        return True
    except ImportError:
        return False


class FirebaseSync:
    """Singleton class for Firebase Realtime Database sync."""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._ensure_initialized()
            self._initialized = True

    def _ensure_initialized(self):
        """Ensure Firebase is initialized."""
        if not is_firebase_available():
            raise FirebaseInitializationError("Firebase not available")

    def push_run(self, user_id: str, run_data: dict) -> bool:
        """
        Push run data to Firebase.

        Args:
            user_id: The ID of the user.
            run_data: The dictionary containing run details.

        Returns:
            True if successful, False otherwise.
        """
        try:
            settings = get_settings()

            # Remove internal fields
            data_to_push = run_data.copy()
            if "sync_status" in data_to_push:
                del data_to_push["sync_status"]
            if not data_to_push.get("user_id"):
                data_to_push["user_id"] = user_id
            if not data_to_push.get("pr_author"):
                data_to_push["pr_author"] = user_id

            # Generate readable key
            slug = data_to_push.get("slug", "unknown")
            timestamp = data_to_push.get("timestamp", datetime.now().isoformat())

            # Clean timestamp for key
            ts_clean = timestamp.strip()
            if ts_clean.endswith("Z"):
                ts_clean = ts_clean[:-1]
            try:
                dt = datetime.fromisoformat(ts_clean.replace("Z", "+00:00"))
                ts_str = dt.strftime("%Y-%m-%d_%H-%M-%S")
            except ValueError:
                # Fallback if timestamp is weird
                ts_str = str(int(time.time()))

            key = f"{slug}_{ts_str}"

            # Default to provided user_id (GitHub login)
            target_user_id = user_id

            if settings.firebase.is_admin_mode():
                # Admin Mode: SDK
                # Use github_login as key (preferred for readability if admin)
                db = get_firebase_db()
                ref = db.reference(f"users/{target_user_id}/runs")
                ref.child(key).set(data_to_push)
            else:
                # User Mode: REST
                import requests

                identity = _get_user_mode_identity()
                if not identity:
                    return False
                local_id, token = identity  # Unpack local_id (UID)

                # CRITICAL FIX: Use local_id (UID) as the key in the database path
                # This aligns with Firebase Security Rules allow-write owner check
                target_user_id = local_id

                # Use requests.put for custom ID
                url = f"{settings.firebase.database_url}/users/{target_user_id}/runs/{key}.json?auth={token}"
                resp = requests.put(url, json=data_to_push, timeout=10)
                if not resp.ok:
                    logger.debug(f"Firebase REST put failed: {resp.status_code} {resp.text}")
                    return False

            logger.debug(f"Synced run stats to Firebase for users/{target_user_id}/runs/{key}")
            return True
        except Exception as e:
            logger.debug(f"Firebase push failed: {e}")
            return False

    def fetch_team_stats(self) -> dict | None:
        """Fetch aggregated team statistics from Firebase."""
        if not is_firebase_available():
            return None

        try:

            def is_complete_run(run: dict) -> bool:
                """Return True if a run represents a merged PR."""
                if run.get("status") != "success":
                    return False
                if run.get("merged_at"):
                    return True
                return run.get("pr_state", "").upper() == "MERGED"

            def _run_sort_key(run: dict) -> datetime:
                ts = run.get("merged_at") or run.get("timestamp") or ""
                if ts.endswith("+00:00Z"):
                    ts = ts[:-1]
                elif ts.endswith("Z"):
                    ts = ts[:-1] + "+00:00"
                try:
                    parsed = datetime.fromisoformat(ts)
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    return parsed
                except ValueError:
                    return datetime.min.replace(tzinfo=timezone.utc)

            settings = get_settings()
            users_data = None

            if settings.firebase.is_admin_mode():
                db = get_firebase_db()
                ref = db.reference("users")
                users_data = ref.get()
            else:
                # User Mode: REST
                import requests

                identity = _get_user_mode_identity()
                if not identity:
                    return None
                _, token = identity

                url = f"{settings.firebase.database_url}/users.json?auth={token}"
                resp = requests.get(url, timeout=10)
                if resp.ok:
                    users_data = resp.json()
                else:
                    logger.warning(
                        "Firebase REST fetch failed: %s %s",
                        resp.status_code,
                        resp.text[:200],
                    )
                    return None

            if not users_data:
                return None

            total_runs = 0
            total_migrations = 0
            total_lines_migrated = 0
            total_time_saved_h = 0.0
            total_automation_seconds = 0.0
            author_migrations: dict[str, set] = {}
            global_best_by_slug: dict[str, dict] = {}

            for user_id, user_node in users_data.items():
                if not isinstance(user_node, dict):
                    continue
                runs_node = user_node.get("runs", {})
                # migrations_node = user_node.get("migrations", []) # Ignored in strict mode
                if not runs_node:
                    runs_node = {}

                # Strict Mode: Do NOT backfill from migrations node
                # if isinstance(migrations_node, list): ...

                unique_complete_by_slug: dict[str, dict] = {}
                for _, run in runs_node.items():
                    if is_complete_run(run):
                        slug = run.get("slug")
                        if not slug or slug == "verification-ping":
                            continue
                        existing = unique_complete_by_slug.get(slug)
                        if not existing or _run_sort_key(run) > _run_sort_key(existing):
                            unique_complete_by_slug[slug] = run

                for slug, run in unique_complete_by_slug.items():
                    existing_global = global_best_by_slug.get(slug)
                    if not existing_global or _run_sort_key(run) > _run_sort_key(existing_global):
                        global_best_by_slug[slug] = run

                for slug, run in unique_complete_by_slug.items():
                    author = (
                        run.get("pr_author") or run.get("user_id") or run.get("_user") or user_id
                    )
                    author_migrations.setdefault(author, set()).add(slug)

            user_counts = {author: len(slugs) for author, slugs in author_migrations.items()}

            if global_best_by_slug:
                total_runs = len(global_best_by_slug)
                total_migrations = len(global_best_by_slug)
                for run in global_best_by_slug.values():
                    total_lines_migrated += run.get("lines_migrated", 0)
                    total_automation_seconds += run.get("automation_seconds", 0)

                if total_lines_migrated > 0:
                    total_time_saved_h = total_lines_migrated / 800.0

            return {
                "total_users": len(user_counts),
                "total_migrations": total_migrations,
                "total_lines_migrated": total_lines_migrated,
                "total_runs": total_runs,
                "total_time_saved_h": round(total_time_saved_h, 1),
                "total_automation_time_h": round(total_automation_seconds / 3600, 2),
                "top_contributors": sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[
                    :3
                ],
                "source": "firebase",
            }
        except Exception as e:
            logger.debug(f"Failed to fetch team stats from Firebase: {e}")
            return None

    def get_all_migrated_slugs(self) -> dict[str, str]:
        """Fetch a mapping of all migrated slugs to the user who migrated them."""
        if not is_firebase_available():
            return {}

        try:

            def is_complete_run(run: dict) -> bool:
                if run.get("status") != "success":
                    return False
                if run.get("merged_at"):
                    return True
                return run.get("pr_state", "").upper() == "MERGED"

            settings = get_settings()
            users_data = None

            if settings.firebase.is_admin_mode():
                db = get_firebase_db()
                ref = db.reference("users")
                users_data = ref.get()
            else:
                # User Mode: REST
                import requests

                identity = _get_user_mode_identity()
                if not identity:
                    return {}
                _, token = identity

                url = f"{settings.firebase.database_url}/users.json?auth={token}"
                resp = requests.get(url, timeout=10)
                if resp.ok:
                    users_data = resp.json()
                else:
                    return {}

            if not users_data:
                return {}

            migrated_map = {}
            for user_id, user_node in users_data.items():
                if not isinstance(user_node, dict):
                    continue
                runs_node = user_node.get("runs", {})
                if not runs_node:
                    runs_node = {}

                for _, run in runs_node.items():
                    if is_complete_run(run):
                        slug = run.get("slug")
                        if slug and slug not in migrated_map:
                            author = (
                                run.get("pr_author")
                                or run.get("user_id")
                                or run.get("_user")
                                or user_id
                            )
                            migrated_map[slug] = author
            return migrated_map
        except Exception as e:
            logger.debug(f"Failed to fetch global history: {e}")
            return {}

    def fetch_user_runs(self, user_id: str | None = None) -> dict:
        """
        Fetch runs for a specific user.

        Args:
            user_id: The user ID to fetch runs for. If None, tries to use current User Mode identity.

        Returns:
            Dictionary of runs, or empty dict if not found/error.
        """
        if not is_firebase_available():
            return {}

        try:
            settings = get_settings()

            # Determine target user ID
            target_uid = user_id
            token = None
            if not target_uid:
                if settings.firebase.is_admin_mode():
                    raise ValueError("Must provide user_id in Admin Mode")

                identity = _get_user_mode_identity()
                if not identity:
                    return {}
                target_uid, token = identity
            elif not settings.firebase.is_admin_mode() and not token:
                # If user_id provided in User Mode, check if it matches current identity
                # User Mode can only read self via authenticated endpoint,
                # OR read public nodes if rules allow.
                # We assume we want to read "users/{uid}/runs" which is generally readable.
                identity = _get_user_mode_identity()
                if identity:
                    current_uid, current_token = identity
                    # If fetching self, use auth token
                    if current_uid == target_uid:
                        token = current_token
                    else:
                        # Fetching others: try anonymous/public read (token not strictly needed if rules allow)
                        # But we'll try to use the token if we have it, as it adds "auth != null" context
                        token = current_token

            if settings.firebase.is_admin_mode():
                db = get_firebase_db()
                ref = db.reference(f"users/{target_uid}/runs")
                data = ref.get()
                return data if isinstance(data, dict) else {}

            # User Mode: REST
            import requests

            url = f"{settings.firebase.database_url}/users/{target_uid}/runs.json"
            if token:
                url += f"?auth={token}"

            resp = requests.get(url, timeout=10)
            if resp.ok:
                data = resp.json()
                return data if isinstance(data, dict) else {}
            else:
                logger.debug(f"REST fetch failed for {target_uid}: {resp.status_code}")
                return {}

        except Exception as e:
            logger.debug(f"Failed to fetch user runs: {e}")
            return {}

    def fetch_all_users_raw(self) -> dict:
        """
        Fetch ALL users and their runs.

        Used for global stats update (scanning everyone's runs for PR status changes).
        """
        if not is_firebase_available():
            return {}

        try:
            settings = get_settings()

            if settings.firebase.is_admin_mode():
                db = get_firebase_db()
                ref = db.reference("users")
                data = ref.get()
                return data if isinstance(data, dict) else {}

            # User Mode: REST
            import requests

            # We need an identity to read, even if rules are public,
            # but usually 'users' is readable by auth users.
            identity = _get_user_mode_identity()
            token = identity[1] if identity else None

            url = f"{settings.firebase.database_url}/users.json"
            if token:
                url += f"?auth={token}"

            resp = requests.get(url, timeout=15)
            if resp.ok:
                data = resp.json()
                return data if isinstance(data, dict) else {}
            else:
                logger.debug(f"Global REST fetch failed: {resp.status_code}")
                return {}

        except Exception as e:
            logger.debug(f"Failed to fetch all users: {e}")
            return {}

    def update_run(self, user_id: str | None, run_key: str, updates: dict) -> bool:
        """
        Update specific fields of a run.

        Args:
            user_id: Owner of the run. If None, infers from current identity.
            run_key: The key of the run to update.
            updates: Dictionary of fields to update.

        Returns:
            True if successful.
        """
        try:
            settings = get_settings()

            target_uid = user_id
            token = None

            if not target_uid:
                if settings.firebase.is_admin_mode():
                    raise ValueError("Must provide user_id in Admin Mode")
                identity = _get_user_mode_identity()
                if not identity:
                    return False
                target_uid, token = identity

            # If User Mode, we explicitly need the token to write
            if not settings.firebase.is_admin_mode() and not token:
                identity = _get_user_mode_identity()
                if identity:
                    current_uid, current_token = identity
                    if current_uid == target_uid:
                        token = current_token
                    else:
                        # Trying to update someone else's run in User Mode?
                        # Only works if Rules allow it (e.g. Universal Admin)
                        token = current_token

            if settings.firebase.is_admin_mode():
                db = get_firebase_db()
                ref = db.reference(f"users/{target_uid}/runs/{run_key}")
                ref.update(updates)
                return True

            # User Mode: REST
            import requests

            if not token:
                logger.debug("Cannot update run in User Mode without auth token")
                return False

            url = f"{settings.firebase.database_url}/users/{target_uid}/runs/{run_key}.json?auth={token}"
            resp = requests.patch(url, json=updates, timeout=10)

            if resp.ok:
                return True
            else:
                logger.debug(f"REST update failed: {resp.status_code} {resp.text}")
                return False

        except Exception as e:
            logger.debug(f"Failed to update run: {e}")
            return False


def get_firebase_app() -> App | None:
    """
    Get the initialized Firebase app instance.

    Returns:
        The Firebase app instance if initialized, None otherwise.
    """
    if not _firebase_initialized:
        _initialize_firebase()
    return _firebase_app


def reset_firebase() -> None:
    """
    Reset Firebase state for testing or reconfiguration.

    WARNING: This deletes the Firebase app instance. Only use in tests
    or when reconfiguration is explicitly required.
    """
    global _firebase_app, _firebase_initialized, _firebase_user_mode

    with _initialization_lock:
        if _firebase_app is not None:
            try:
                import firebase_admin

                firebase_admin.delete_app(_firebase_app)
            except Exception as e:
                logger.debug(f"Error deleting Firebase app: {e}")

        _firebase_app = None
        _firebase_initialized = False
        _firebase_user_mode = False
