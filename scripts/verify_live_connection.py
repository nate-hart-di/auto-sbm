import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Ensure sbm module is in path
sys.path.append(os.getcwd())

from sbm.config import get_settings
from sbm.utils.firebase_sync import (
    _initialize_firebase,
    get_firebase_db,
    FirebaseInitializationError,
)

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("verify_live")


def run_verification():
    print("Locked and Loaded: Verifying Firebase Connection...")

    settings = get_settings()

    # 1. Check Configuration
    print(f"\n[1] Configuration Check:")
    print(f"    - Database URL: {settings.firebase.database_url}")
    print(f"    - Credentials Path: {settings.firebase.credentials_path}")

    if settings.firebase.is_admin_mode():
        print("    -> MODE: ADMIN (Full Access)")
    elif settings.firebase.is_user_mode():
        print("    -> MODE: USER (Anonymous Read/Own-Write)")
    else:
        print("    -> MODE: NOT CONFIGURED")
        print("    ❌ ERROR: No valid Firebase configuration found.")
        return

    # 2. Initialize
    print(f"\n[2] Initialization:")
    try:
        success = _initialize_firebase()
        if success:
            print("    ✅ Firebase App Initialized Successfully")
        else:
            print("    ❌ Failed to initialize Firebase App")
            return
    except Exception as e:
        print(f"    ❌ Initialization crashed: {e}")
        return

    # 3. Connection Test
    print(f"\n[3] Connection Test:")
    timestamp = datetime.now().isoformat()

    if settings.firebase.is_admin_mode():
        try:
            db = get_firebase_db()
            ref = db.reference("verification_ping")

            # Write Test
            print(f"    -> [ADMIN] Attempting WRITE to /verification_ping...")
            try:
                ref.set({"timestamp": timestamp, "agent": "Antigravity", "mode": "admin"})
                print("    ✅ WRITE Successful")
            except Exception as e:
                print(f"    ❌ WRITE Failed: {e}")

            # Read Test
            print(f"    -> [ADMIN] Attempting READ from /verification_ping...")
            try:
                data = ref.get()
                print(f"    ✅ READ Successful: {data}")
            except Exception as e:
                print(f"    ❌ READ Failed: {e}")

        except Exception as e:
            print(f"    ❌ Admin Connection/Reference failed: {e}")

    elif settings.firebase.is_user_mode():
        import requests

        print(f"    -> [USER] Using REST API (Anonymous Auth)")
        base_url = settings.firebase.database_url

        # Test READ (Public/User writable)
        # Note: /verification_ping might be protected by rules?
        # Assuming we can read/write it for now or we test /users/{user}/ping

        # Try reading /verification_ping.json
        print(f"    -> [USER] Attempting REST READ from /verification_ping.json...")
        try:
            resp = requests.get(f"{base_url}/verification_ping.json", timeout=10)
            if resp.status_code == 200:
                print(f"    ✅ REST READ Successful: {resp.json()}")
            else:
                print(f"    ⚠️ REST READ Status: {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"    ❌ REST READ Failed: {e}")

        # Try Writing (likely fails if rules block anon write to root)
        # But we can try validation!
        # Retrospective: "User Mode ... non-admin users can operate without service account"
        # Usually checking if we can READ /users.json (shallow) or specific user node.
        pass

    else:
        print("    ℹ️  Skipping Connection Test (Not Configured)")


if __name__ == "__main__":
    run_verification()
