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
import re
import sys
from pathlib import Path
from typing import Any, Dict

# Add project root to sys.path to ensure 'sbm' package is findable
REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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

# Initialize the Bolt App
# 2025-12-22: Support SLACK_BOT_OAUTH fallback
# NOTE: app init must happen before report_slack loads .env again, or OAuth envs can
#       force Bolt into OAuth mode and ignore the bot token.
token = os.environ.get("SLACK_BOT_TOKEN") or os.environ.get("SLACK_BOT_OAUTH")
app = App(token=token)

import report_slack


@app.command("/sbm-stats")
def handle_sbm_stats(ack, body, say, logger):
    """Handle /sbm-stats [period]"""
    # Acknowledge the command request immediately
    ack()

    user_id = body.get("user_id")
    text = body.get("text", "").strip()
    command_str = "/sbm-stats" + (f" {text}" if text else "")
    context_label = f"Auto-SBM {command_str} received"

    # Parse optional args: [period/date/range] [username]
    period = "week"
    username = None
    top_n = None
    top_flag = False
    tokens = text.split() if text else []

    if tokens:
        lower_tokens = [t.lower() for t in tokens]

        # 1. Handle "top N"
        if "top" in lower_tokens:
            top_flag = True
            idx = lower_tokens.index("top")
            if idx + 1 < len(lower_tokens) and lower_tokens[idx + 1].isdigit():
                top_n = int(lower_tokens[idx + 1])
                del tokens[idx : idx + 2]
            else:
                top_n = 3
                del tokens[idx : idx + 1]
            lower_tokens = [t.lower() for t in tokens]

        # 2. Extract Period/Date/Range
        # We look for:
        # - Named periods: day, week, month, all
        # - Date ranges: "1/1/25 to 2/1/25"
        # - Duration ranges: "14 1/1/25"
        # - Specific dates: "1/25", "1/1/25"

        full_text = " ".join(tokens)

        # Regex for common patterns
        # Range: date to date
        range_match = re.search(
            r"(\d{1,2}/\d{1,2}(?:/\d{2,4})?\s+to\s+\d{1,2}/\d{1,2}(?:/\d{2,4})?)", full_text, re.I
        )
        # Duration: N date
        duration_match = re.search(r"(\d+\s+\d{1,2}/\d{1,2}(?:/\d{2,4})?)", full_text, re.I)
        # Specific date: MM/DD/YY or MM/YY
        date_match = re.search(r"(\d{1,2}/\d{1,2}(?:/\d{2,4})?|\d{1,2}/\d{2,4})", full_text, re.I)
        # Named period
        period_tokens = {"day", "daily", "week", "weekly", "month", "monthly", "all"}
        found_period = None
        for t in lower_tokens:
            if t in period_tokens or t.isdigit():
                found_period = t
                break

        if range_match:
            period = range_match.group(1)
            # Remove from tokens to find username
            remaining_text = full_text.replace(period, "").strip()
            username = remaining_text if remaining_text else None
        elif duration_match:
            period = duration_match.group(1)
            remaining_text = full_text.replace(period, "").strip()
            username = remaining_text if remaining_text else None
        elif date_match:
            # Important: specific dates might be part of a larger string
            # We only treat it as the period if it matches a token exactly or is the start
            period = date_match.group(1)
            remaining_text = full_text.replace(period, "").strip()
            username = remaining_text if remaining_text else None
        elif found_period:
            period = found_period
            # Find the original token to remove
            idx = lower_tokens.index(found_period)
            del tokens[idx]
            username = " ".join(tokens).strip() if tokens else None
        else:
            # No clear period, assume text is username and period is 'week' (default)
            username = full_text.strip() if full_text else None
            if username:
                period = "week"
            else:
                period = "week"  # Fallback just in case

    logger.info(
        f"Received /sbm-stats command from {user_id} with period: {period} user: {username or 'all'} top: {top_n}"
    )

    try:
        # 1. Load Data
        all_runs, user_migrations = report_slack.load_all_stats()

        # 2. Parse date range for header
        from datetime import datetime, timedelta, timezone
        from sbm.utils.tracker import _parse_date_input, _parse_period_to_days
        import re

        start_date = None
        end_date = None
        is_month_only = False

        if period != "all":
            # Detect month-only format: M/YY or MM/YY (no day component)
            month_only_match = re.match(r"^(\d{1,2})/(\d{2,4})$", period.strip())
            if month_only_match:
                is_month_only = True

            # Try new flexible formats first
            parsed = _parse_date_input(period)
            if parsed:
                start_date, end_date = parsed
            else:
                # Try period-based ("7", "week", etc)
                days = _parse_period_to_days(period)
                if days:
                    end_date = datetime.now(timezone.utc)
                    start_date = end_date - timedelta(days=days)
                else:
                    # Fallback to ISO date
                    try:
                        dt = datetime.fromisoformat(period)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        start_date = dt
                    except (ValueError, TypeError):
                        pass

        # 3. Filter
        if top_flag and period == "all" and not username and not tokens:
            payload = report_slack.format_top_users_payload(user_migrations, top_n, context_label)
            payload["username"] = "SBM Stats Bot"
            say(blocks=payload["blocks"], text=payload["text"])
            return

        filtered_runs = report_slack.filter_runs_by_date(all_runs, period)
        if username:
            filtered_runs = report_slack.filter_runs_by_user(filtered_runs, username)

        # 4. Aggregate
        is_all_time = period == "all"
        if is_all_time and not username:
            metrics = report_slack.calculate_global_metrics_all_time()
        else:
            metrics = report_slack.calculate_metrics(filtered_runs, user_migrations, is_all_time)

        # 5. Format
        current_in_review_count = len(
            [r for r in all_runs if report_slack._get_completion_state(r) == "in_review"]
        )

        payload = report_slack.format_slack_payload(
            metrics,
            period,
            context_label,
            top_n if top_flag else None,
            current_in_review_count=current_in_review_count,
            start_date=start_date,
            end_date=end_date,
            is_month_only=is_month_only,
        )

        # 6. Branding
        payload["username"] = "SBM Stats Bot"

        # 7. Respond
        # By default, slash command responses are ephemeral (visible only to user)
        # We can use say() to post to the channel or just return the blocks
        if username and not filtered_runs:
            known_users = sorted(user_migrations.keys())
            preview = ", ".join(known_users[:10]) if known_users else "none"
            say(
                f"⚠️ No stats found for user '{username}'. "
                f"Known users: {preview}. Try /sbm-stats top."
            )
            return
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
