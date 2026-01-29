import subprocess
import json
import sys
import os
from sbm.utils.firebase_sync import _initialize_firebase, get_firebase_db, _get_user_mode_identity


def debug_update():
    print("Locked and Loaded: Debugging PR Status Update...")

    # 1. Initialize Firebase
    try:
        _initialize_firebase()
        db = get_firebase_db()
        print("✅ Firebase Initialized")
    except Exception as e:
        print(f"❌ Firebase Init Failed: {e}")
        return

    # 2. Get User ID
    user_auth = _get_user_mode_identity()
    if not user_auth:
        print("❌ Could not get user identity")
        return

    uid = user_auth[0]
    print(f"✅ User ID: {uid}")

    # 3. Find the stale run
    print("-> Searching for 'quality-preowned-vehicles-of-watertown-sd'...")
    users_ref = db.reference(f"/users/{uid}/runs")
    runs = users_ref.get() or {}

    target_run = None
    target_key = None

    for key, data in runs.items():
        if data.get("slug") == "quality-preowned-vehicles-of-watertown-sd":
            target_run = data
            target_key = key
            break

    if not target_run:
        print("❌ Could not find run with slug 'quality-preowned-vehicles-of-watertown-sd'")
        # Try finding ANY open run as fallback
        print("-> Fallback: Searching for ANY 'OPEN' run...")
        for key, data in runs.items():
            if data.get("pr_state") == "OPEN" and data.get("pr_url"):
                target_run = data
                target_key = key
                print(f"-> Found alternative: {data.get('slug')}")
                break

    if not target_run:
        print("❌ No suitable runs found for debugging.")
        return

    print(f"✅ Found Run: {target_run.get('slug')} (Key: {target_key})")
    print(f"   Current PR State: {target_run.get('pr_state')}")
    print(f"   PR URL: {target_run.get('pr_url')}")

    pr_url = target_run.get("pr_url")
    if not pr_url:
        print("❌ No PR URL to check.")
        return

    # 4. Test 'gh' CLI directly
    print(f"\n-> Testing 'gh' CLI for {pr_url}...")
    try:
        cmd = ["gh", "pr", "view", pr_url, "--json", "createdAt,mergedAt,closedAt,state,author"]
        print(f"   Running: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

        if result.returncode == 0:
            print("✅ 'gh' command SUCCESS")
            print(f"   STDOUT: {result.stdout}")
            try:
                data = json.loads(result.stdout)
                print(f"   Parsed State: {data.get('state')}")
            except:
                print("   Failed to parse JSON")
        else:
            print("❌ 'gh' command FAILED")
            print(f"   Return Code: {result.returncode}")
            print(f"   STDERR: {result.stderr}")
            print(f"   STDOUT: {result.stdout}")

    except FileNotFoundError:
        print("❌ 'gh' executable not found in PATH")
    except Exception as e:
        print(f"❌ Exception running 'gh': {e}")


if __name__ == "__main__":
    debug_update()
