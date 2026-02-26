import os
import sys
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, db

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbm.config import get_settings


def recover_run():
    settings = get_settings()
    user_id = "nate-hart-di"
    slug = "rontonkinchryslercjdrf"

    print(f"Recovering missing run for: {slug}")

    if settings.firebase.is_admin_mode():
        cred = credentials.Certificate(str(settings.firebase.credentials_path))
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {"databaseURL": settings.firebase.database_url})

        # Create recovery payload
        now_ts = datetime.now()
        ts_str = now_ts.strftime("%Y-%m-%d_%H-%M-%S")

        run_data = {
            "slug": slug,
            "timestamp": now_ts.isoformat(),
            "status": "success",
            "lines_migrated": 0,  # Unknown, safe default
            "automation_seconds": 0,
            "command": "recovery",
            "files_created": [],
            "version": "1.0.0",
        }

        key = f"{slug}_{ts_str}"

        ref = db.reference(f"users/{user_id}/runs")
        ref.child(key).set(run_data)

        print(f"Successfully recovered run: {key}")

    else:
        print("Admin mode required.")


if __name__ == "__main__":
    recover_run()
