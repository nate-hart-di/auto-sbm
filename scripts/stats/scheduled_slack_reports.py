#!/usr/bin/env python3
"""
Send scheduled Slack reports (daily/weekly/monthly) using the same data as CLI stats.

Schedule this at 9am CST (America/Chicago). It will:
- Send daily report for the previous day (Tue-Fri, and other non-Mondays).
- On Mondays, send the weekly report for the previous week with a leaderboard.
- On the 1st of the month, send monthly report with leaderboard and an all-time report with leaderboard.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import List

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

try:
    from dotenv import load_dotenv

    load_dotenv(override=True)
except ImportError:
    pass

# Import report logic
from report_slack import (
    calculate_global_metrics_all_time,
    calculate_metrics,
    filter_runs_by_date,
    format_slack_payload,
    load_all_stats,
    send_slack_message_api,
)


def _parse_channels(raw: str | None) -> List[str]:
    if not raw:
        return []
    return [c.strip() for c in raw.split(",") if c.strip()]


def main() -> None:
    tz_name = os.environ.get("SBM_REPORT_TZ", "America/Chicago")
    if ZoneInfo is None:
        print("Error: zoneinfo not available; use Python 3.9+.", file=sys.stderr)
        sys.exit(1)
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)

    token = os.environ.get("SLACK_BOT_TOKEN") or os.environ.get("SLACK_BOT_OAUTH")
    channels = _parse_channels(os.environ.get("SLACK_CHANNELS") or os.environ.get("SLACK_CHANNEL"))
    if not token or not channels:
        print("Error: SLACK_BOT_TOKEN and SLACK_CHANNELS (or SLACK_CHANNEL) required.", file=sys.stderr)
        sys.exit(1)

    all_runs, user_migrations = load_all_stats()

    weekday = now.weekday()  # Monday=0
    is_month_start = now.day == 1

    if weekday == 0:
        period = "week"
        context = "Auto-SBM Weekly report (prev week)"
        top_n = 3
    else:
        period = "day"
        context = "Auto-SBM Daily report (prev day)"
        top_n = None

    filtered_runs = filter_runs_by_date(all_runs, period)
    metrics = calculate_metrics(filtered_runs, user_migrations, period == "all")
    payload = format_slack_payload(metrics, period, context_label=context, top_n=top_n)

    for channel in channels:
        send_slack_message_api(token, channel, payload)

    if is_month_start:
        # Monthly report + leaderboard (top 3)
        month_metrics = calculate_metrics(
            filter_runs_by_date(all_runs, "month"),
            user_migrations,
            False,
        )
        month_payload = format_slack_payload(
            month_metrics,
            "month",
            context_label="Auto-SBM Monthly report (prev month)",
            top_n=3,
        )
        # All-time report + leaderboard reminder
        all_metrics = calculate_global_metrics_all_time()
        all_payload = format_slack_payload(
            all_metrics,
            "all",
            context_label="Auto-SBM All-time leaderboard",
            top_n=3,
        )
        for channel in channels:
            send_slack_message_api(token, channel, month_payload)
            send_slack_message_api(token, channel, all_payload)


if __name__ == "__main__":
    main()
