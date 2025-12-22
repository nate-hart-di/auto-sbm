#!/usr/bin/env python3
"""
Slack Socket Mode Listener for SBM Stats.

This script listens for the /sbm-stats slash command and returns
reports in real-time without requiring a public endpoint.

Requirements:
    pip install slack-bolt slack-sdk

Environment Variables:
    SLACK_BOT_TOKEN: xoxb-... (Bot User OAuth Token)
    SLACK_APP_TOKEN: xapp-... (App-Level Token with connections:write)
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict

# Try to load environment variables
try:
    from dotenv import load_dotenv

    # Load .env file (force override of system env vars to ensure we get the correct tokens)
    load_dotenv(override=True, verbose=True)

    # FORCE SINGLE WORKSPACE MODE:
    # If SLACK_CLIENT_ID is present, Bolt attempts OAuth flow and ignores SLACK_BOT_TOKEN.
    # We remove these to ensure we use the provided tokens for Socket Mode.
    if "SLACK_CLIENT_ID" in os.environ:
        os.environ.pop("SLACK_CLIENT_ID", None)
    if "SLACK_CLIENT_SECRET" in os.environ:
        os.environ.pop("SLACK_CLIENT_SECRET", None)
except ImportError:
    pass

try:
    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler
except ImportError:
    print("Error: slack-bolt or slack-sdk not installed.")
    print("Run: pip install slack-bolt slack-sdk")
    sys.exit(1)

# Import the reporting logic from report_slack.py
# We add the script directory to path to ensure imports work
sys.path.append(str(Path(__file__).parent.resolve()))
import report_slack

# Initialize the Bolt App
# Initialize the Bolt App
# 2025-12-22: Support SLACK_BOT_OAUTH fallback
token = os.environ.get("SLACK_BOT_TOKEN") or os.environ.get("SLACK_BOT_OAUTH")
app = App(token=token)


@app.command("/sbm-stats")
def handle_sbm_stats(ack, body, say, logger):
    """Handle /sbm-stats [period]"""
    # Acknowledge the command request immediately
    ack()

    user_id = body.get("user_id")
    text = body.get("text", "1").strip().lower()

    # Map friendly names to the periods report_slack understands
    if not text:
        text = "1"

    logger.info(f"Received /sbm-stats command from {user_id} with text: {text}")

    try:
        # 1. Load Data
        all_runs, user_migrations = report_slack.load_all_stats()

        # 2. Filter
        filtered_runs = report_slack.filter_runs_by_date(all_runs, text)

        # 3. Aggregate
        is_all_time = text == "all"
        metrics = report_slack.calculate_metrics(filtered_runs, user_migrations, is_all_time)

        # 4. Format
        payload = report_slack.format_slack_payload(metrics, text)

        # 5. Branding
        payload["username"] = "SBM Stats Bot"

        # 6. Respond
        # By default, slash command responses are ephemeral (visible only to user)
        # We can use say() to post to the channel or just return the blocks
        say(blocks=payload["blocks"], text=payload["text"])

    except Exception as e:
        logger.error(f"Error handling slash command: {e}")
        say(f"⚠️ Error generating report: {str(e)}")


if __name__ == "__main__":
    # Support both naming conventions
    app_token = os.environ.get("SLACK_APP_TOKEN")

    # Try SLACK_BOT_TOKEN first, then SLACK_BOT_OAUTH
    bot_token = os.environ.get("SLACK_BOT_TOKEN") or os.environ.get("SLACK_BOT_OAUTH")

    if not app_token:
        print("Error: SLACK_APP_TOKEN not found in environment.")
        print("Ensure you have created an App-Level Token with 'connections:write' scope.")
        sys.exit(1)

    if not bot_token:
        print("Error: SLACK_BOT_TOKEN (or SLACK_BOT_OAUTH) not found in environment.")
        sys.exit(1)

    try:
        # Use the global 'app' instance which has the command handlers registered!

        # Get bot user info to verify identity
        auth_test = app.client.auth_test()
        bot_user_id = auth_test["user_id"]
        bot_name = auth_test["user"]

        print(f"⚡️ SBM Stats Socket Mode listener is running!")
        print(f"   Authenticated as: {bot_name} ({bot_user_id})")
        print(f"   Listening for command: /sbm-stats")

        handler = SocketModeHandler(app, app_token)
        handler.start()
    except Exception as e:
        print(f"❌ Error starting listener: {e}")
