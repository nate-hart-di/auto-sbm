import logging
import os
import sys
from datetime import datetime

# Ensure sbm module is in path
sys.path.append(os.getcwd())

from sbm.config import get_settings
from sbm.utils.firebase_sync import (
    _initialize_firebase,
    get_firebase_db,
)

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("verify_live")


def run_verification():
    print("Locked and Loaded: Verifying Firebase Connection...")

    settings = get_settings()

    # 1. Check Configuration
    print("\n[1] Configuration Check:")
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
    print("\n[2] Initialization:")
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
    print("\n[3] Connection Test:")
    timestamp = datetime.now().isoformat()

    if settings.firebase.is_admin_mode():
        try:
            db = get_firebase_db()
            ref = db.reference("verification_ping")

            # Write Test
            print("    -> [ADMIN] Attempting WRITE to /verification_ping...")
            try:
                ref.set({"timestamp": timestamp, "agent": "Antigravity", "mode": "admin"})
                print("    ✅ WRITE Successful")
            except Exception as e:
                print(f"    ❌ WRITE Failed: {e}")

            # Read Test
            print("    -> [ADMIN] Attempting READ from /verification_ping...")
            try:
                data = ref.get()
                print(f"    ✅ READ Successful: {data}")
            except Exception as e:
                print(f"    ❌ READ Failed: {e}")

        except Exception as e:
            print(f"    ❌ Admin Connection/Reference failed: {e}")

    elif settings.firebase.is_user_mode():
        import requests

        from sbm.utils.firebase_sync import get_user_mode_identity

        print("    -> [USER] Using REST API (Anonymous Auth)")
        base_url = settings.firebase.database_url

        # Authenticate first
        print("    -> [USER] Authenticating via Identity Toolkit...")
        identity = get_user_mode_identity()

        if not identity:
            print("    ❌ Authentication Failed: Could not get anonymous token.")
            print("       Check FIREBASE__API_KEY in .env and internet connection.")
            return

        uid, token = identity
        print(f"    ✅ Authenticated as: {uid}")

        # Test READ (Public/User writable)
        # Try reading /verification_ping.json with auth
        print("    -> [USER] Attempting REST READ from /verification_ping.json...")
        try:
            resp = requests.get(f"{base_url}/verification_ping.json?auth={token}", timeout=10)
            if resp.status_code == 200:
                print(f"    ✅ REST READ Successful: {resp.json()}")
            elif resp.status_code == 401:
                print("    ⚠️ REST READ Permission Denied (Expected if rules block root).")
            else:
                print(f"    ⚠️ REST READ Status: {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"    ❌ REST READ Failed: {e}")

        # Try Writing to user's own run node (should succeed if rules allow runs)
        print(f"    -> [USER] Attempting REST WRITE to users/{uid}/runs/ping.json...")
        try:
            payload = {
                "timestamp": timestamp,
                "agent": "Antigravity",
                "mode": "user_verified",
                "slug": "verification-ping",
                "status": "success",
            }
            url = f"{base_url}/users/{uid}/runs/ping.json?auth={token}"
            resp = requests.put(url, json=payload, timeout=10)

            if resp.status_code == 200:
                print(f"    ✅ REST WRITE Successful: {resp.json()}")
            else:
                print(f"    ❌ REST WRITE Status: {resp.status_code} {resp.text}")

        except Exception as e:
            print(f"    ❌ REST WRITE Failed: {e}")

    else:
        print("    ℹ️  Skipping Connection Test (Not Configured)")


if __name__ == "__main__":
    run_verification()
