import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from dotenv import load_dotenv

load_dotenv()

from firebase_admin import db

from sbm.utils.firebase_sync import is_firebase_available
from sbm.utils.tracker import _read_tracker


def get_user_id():
    return "nate-hart-di"


def check():
    print(f"User ID: {get_user_id()}")
    print("--- LOCAL ---")
    data = _read_tracker()
    runs = data.get("runs", [])
    found_local = [r for r in runs if r["slug"] == "albany"]
    print(f"Albany in local: {len(found_local)}")
    if found_local:
        r = found_local[-1]
        print(f"Status: {r.get('status')}")
        print(f"Sync: {r.get('sync_status')}")
        print(f"Command: {r.get('command')}")

    print("--- FIREBASE ---")
    if is_firebase_available():
        try:
            # Direct Access
            ref = db.reference(f"users/{get_user_id()}/runs")
            fb_runs = ref.get()

            if isinstance(fb_runs, dict):
                print(f"Total FB Runs: {len(fb_runs)}")
                print("First 5 Keys:")
                for k in list(fb_runs.keys())[:5]:
                    print(f"  {k}")

                fb_runs_list = list(fb_runs.values())
            elif isinstance(fb_runs, list):
                # This shouldn't happen with our new keys (lists are for int keys)
                print("Warning: Data returned as LIST (unexpected for string keys)")
                fb_runs_list = fb_runs
            else:
                fb_runs_list = []

            # Filter success
            success_fb = [r for r in fb_runs_list if r.get("status") == "success"]
            print(f"Success FB Runs: {len(success_fb)}")

            found_fb = [r for r in fb_runs_list if r.get("slug") == "albany"]
            print(f"Albany in Firebase: {len(found_fb)}")
        except Exception as e:
            print(f"FB Error: {e}")
    else:
        print("Firebase unavailable")


if __name__ == "__main__":
    check()
