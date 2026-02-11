#!/usr/bin/env python3
"""
Send scheduled Slack reports (daily/weekly/monthly) using the same data as CLI stats.

Schedule this at 9am CST (America/Chicago). Weekdays only. It will:
- Tue-Fri: Send daily report for the previous calendar day.
- Monday: Send weekly report for the previous calendar week (Mon-Sun) with leaderboard.
- 1st of the month (if weekday): Send monthly report with leaderboard and all-time report.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]

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
    filter_runs_by_previous_calendar_day,
    format_slack_payload,
    load_all_stats,
    send_slack_message_api,
)


def _get_run_timestamp(run: Dict[str, Any]) -> str | None:
    """Get the best available timestamp for a run."""
    return run.get("merged_at") or run.get("created_at") or run.get("timestamp")


def _filter_runs_previous_calendar_week(
    runs: List[Dict[str, Any]], tz_name: str = "America/Chicago"
) -> List[Dict[str, Any]]:
    """Filter runs from the previous calendar week (Monday 00:00 through Sunday 23:59).

    Args:
        runs: List of run dictionaries
        tz_name: Timezone name (default: America/Chicago for CST)

    Returns:
        List of runs from last Monday through last Sunday
    """
    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(tz_name)
    except ImportError:
        tz = timezone.utc

    now = datetime.now(tz)
    today_start = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=tz)
    # today is Monday (weekday=0). Last Monday = 7 days ago, last Sunday = 1 day ago.
    prev_monday = today_start - timedelta(days=7)
    prev_sunday_end = today_start  # midnight Monday = end of Sunday

    filtered = []
    for run in runs:
        ts_str = _get_run_timestamp(run)
        if not ts_str:
            continue
        try:
            if ts_str.endswith("+00:00Z"):
                ts_str = ts_str[:-1]
            elif ts_str.endswith("Z"):
                ts_str = ts_str[:-1] + "+00:00"
            run_dt = datetime.fromisoformat(ts_str)
            if run_dt.tzinfo is None:
                run_dt = run_dt.replace(tzinfo=timezone.utc)
            run_dt_local = run_dt.astimezone(tz)
            if prev_monday <= run_dt_local < prev_sunday_end:
                filtered.append(run)
        except ValueError:
            continue

    return filtered


def _parse_channels(raw: str | None) -> List[str]:
    if not raw:
        return []
    return [c.strip() for c in raw.split(",") if c.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Send scheduled Slack reports")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print payload without sending to Slack"
    )
    args = parser.parse_args()

    tz_name = os.environ.get("SBM_REPORT_TZ", "America/Chicago")
    if ZoneInfo is None:
        print("Error: zoneinfo not available; use Python 3.9+.", file=sys.stderr)
        sys.exit(1)
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)

    token = os.environ.get("SLACK_BOT_TOKEN") or os.environ.get("SLACK_BOT_OAUTH")
    channels = _parse_channels(os.environ.get("SLACK_CHANNELS") or os.environ.get("SLACK_CHANNEL"))

    if not args.dry_run and (not token or not channels):
        print(
            "Error: SLACK_BOT_TOKEN and SLACK_CHANNELS (or SLACK_CHANNEL) required.",
            file=sys.stderr,
        )
        sys.exit(1)

    all_runs, user_migrations = load_all_stats()

    weekday = now.weekday()  # Monday=0
    is_month_start = now.day == 1

    # Weekdays only (Mon-Fri). Skip weekends.
    if weekday >= 5:
        print(f"Skipping scheduled report on {now.strftime('%A')} (weekday-only mode).")
        return

    if weekday == 0:
        period = "week"
        context = "Auto-SBM Weekly report (prev week)"
        top_n = 3
    else:
        period = "day"
        context = "Auto-SBM Daily report (prev day)"
        top_n = None

    # Use calendar day filter for daily reports, calendar week (Mon-Sun) for weekly
    if period == "day":
        filtered_runs = filter_runs_by_previous_calendar_day(all_runs, tz_name)
    else:
        filtered_runs = _filter_runs_previous_calendar_week(all_runs, tz_name)
    metrics = calculate_metrics(filtered_runs, user_migrations, period == "all")
    payload = format_slack_payload(metrics, period, context_label=context, top_n=top_n)

    if args.dry_run:
        print("=== DRY RUN - Would send to Slack ===")
        print(f"Period: {period}")
        print(f"Filtered runs: {len(filtered_runs)}")
        print(f"Metrics: {json.dumps(metrics, indent=2, default=str)}")
        print("\n--- Payload Preview ---")
        print(f"Text: {payload.get('text', 'N/A')}")
        return

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
