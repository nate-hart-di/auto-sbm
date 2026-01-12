#!/usr/bin/env python3
"""
Report SBM statistics to Slack.

Usage:
    python scripts/stats/report_slack.py [--days 7] [--dry-run]

Environment Variables:
    SLACK_WEBHOOK_URL: Method 1 - Incoming Webhook.
    SLACK_BOT_TOKEN: Method 2 - Slack Bot User OAuth Token (xoxb-...).
    SLACK_CHANNEL: Required if using SLACK_BOT_TOKEN (e.g. #general or ID).
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

# Add project root to sys.path to ensure 'sbm' package is findable
REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Try to load environment variables from .env if python-dotenv is installed
try:
    from dotenv import load_dotenv

    # Force override to ensure we use .env values over stale shell vars
    load_dotenv(override=True)
except ImportError:
    pass

# Paths
REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
STATS_DIR = REPO_ROOT / "stats"


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Report SBM stats to Slack")
    parser.add_argument(
        "--period",
        type=str,
        default="1",
        help="Time period (daily, weekly, monthly, all or N days)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print payload instead of sending")
    parser.add_argument(
        "--webhook-url",
        type=str,
        default=os.environ.get("SLACK_WEBHOOK_URL"),
        help="Slack Webhook URL (override env var)",
    )
    parser.add_argument(
        "--token",
        type=str,
        # Support both standard naming and the specific OAUTH naming we used
        default=os.environ.get("SLACK_BOT_TOKEN") or os.environ.get("SLACK_BOT_OAUTH"),
        help="Slack Bot Token (override env var)",
    )
    parser.add_argument(
        "--channel",
        type=str,
        default=os.environ.get("SLACK_CHANNEL"),
        help="Slack Channel ID or name (required for token mode)",
    )
    parser.add_argument(
        "--username",
        type=str,
        default="SBM Stats Bot",
        help="Custom username for the Slack message",
    )
    parser.add_argument(
        "--icon-url",
        type=str,
        help="Custom icon URL for the Slack message",
    )
    return parser.parse_args()


def load_all_stats() -> tuple[List[Dict[str, Any]], Dict[str, set]]:
    """
    Load stats from the same sources as CLI stats.

    Returns:
        tuple: (all_runs_list, user_migrations_dict)
        user_migrations_dict maps user_id -> set of migrated slugs (for accurate site counts)
    """
    try:
        from sbm.utils.tracker import get_global_reporting_data

        return get_global_reporting_data()
    except Exception as e:
        print(f"Warning: Failed to load global reporting data: {e}", file=sys.stderr)

    all_runs = []
    user_migrations = {}

    fallback_dirs = [STATS_DIR, REPO_ROOT / "stats" / "archive"]
    if not any(d.exists() for d in fallback_dirs):
        return all_runs, user_migrations

    for stats_dir in fallback_dirs:
        for stats_file in stats_dir.glob("*.json"):
            if stats_file.name.startswith("."):
                continue

            try:
                with stats_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    user_id = data.get("user", stats_file.stem)
                    runs = data.get("runs", [])
                    migrations = set(data.get("migrations", []))

                    # Store total distinct migrations for this user
                    user_migrations[user_id] = migrations

                    # Tag runs with user_id for attribution
                    for run in runs:
                        run["_user"] = user_id

                    all_runs.extend(runs)
            except Exception as e:
                print(f"Warning: Failed to read {stats_file}: {e}", file=sys.stderr)

    return all_runs, user_migrations


def get_days_from_period(period: str) -> int:
    """Convert semantic period (daily, weekly, monthly, all) to days."""
    period = period.lower()
    if period in {"day", "daily"}:
        return 1
    elif period in {"week", "weekly"}:
        return 7
    elif period in {"month", "monthly"}:
        return 30
    elif period == "all":
        return 99999  # effectively "all"
    try:
        return int(period)
    except ValueError:
        return 1


def filter_runs_by_date(runs: List[Dict[str, Any]], days_or_period: str) -> List[Dict[str, Any]]:
    """Filter runs that occurred within a given period or number of days."""
    if days_or_period.lower() == "all":
        return runs

    days = get_days_from_period(days_or_period)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    filtered = []

    for run in runs:
        ts_str = run.get("timestamp")
        if not ts_str:
            continue

        try:
            # Handle ISO format with Z
            # Fix for malformed SBM timestamps: "2026-01-06...27+00:00Z" -> double offset
            if ts_str.endswith("+00:00Z"):
                ts_str = ts_str[:-1]  # Just remove the Z, leaving +00:00
            elif ts_str.endswith("Z"):
                ts_str = ts_str[:-1] + "+00:00"

            run_dt = datetime.fromisoformat(ts_str)
            if run_dt.tzinfo is None:
                # Assume UTC if naive, though SBM writes with timezone
                run_dt = run_dt.replace(tzinfo=timezone.utc)

            if run_dt >= cutoff:
                filtered.append(run)
        except ValueError as e:
            print(f"Warning: Skipping run with invalid timestamp '{ts_str}': {e}", file=sys.stderr)
            continue

    return filtered


def filter_runs_by_user(runs: List[Dict[str, Any]], username: str) -> List[Dict[str, Any]]:
    """Filter runs by user id or name (case-insensitive)."""
    if not username:
        return runs
    target = username.strip().lower()
    filtered = []
    for run in runs:
        run_user = str(run.get("_user", "")).strip().lower()
        if run_user == target:
            filtered.append(run)
    return filtered


def format_top_users_payload(
    user_migrations: Dict[str, set],
    top_n: int = 3,
    context_label: str | None = None,
) -> Dict[str, Any]:
    """Format a Slack payload for top users by total sites migrated (all time)."""
    if not user_migrations:
        return {
            "text": "No SBM stats found yet.",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*SBM Top Contributors*\nNo SBM stats found yet.",
                    },
                }
            ],
        }

    counts = [(user, len(slugs)) for user, slugs in user_migrations.items()]
    counts.sort(key=lambda x: x[1], reverse=True)
    total_users = len(counts)
    top_n = max(1, min(top_n, total_users))

    lines = []
    for idx, (user, sites) in enumerate(counts[:top_n], start=1):
        lines.append(f"{idx}. {user} — {sites} site(s)")

    text = "Top contributors:\n" + "\n".join(lines)
    context = context_label or "Auto-SBM"

    return {
        "text": text,
        "blocks": [
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": context}],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Top Contributors*\n" + "\n".join(lines)},
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"Showing top {top_n} of {total_users} users."},
                ],
            },
        ],
    }


def calculate_metrics(
    runs: List[Dict[str, Any]],
    user_migrations: Dict[str, set],
    is_all_time: bool = False,
) -> Dict[str, Any]:
    """Calculate aggregate metrics."""
    total_runs = len(runs)
    success_runs = [r for r in runs if r.get("status") == "success"]
    success_count = len(success_runs)

    lines_migrated = sum(r.get("lines_migrated", 0) for r in success_runs)
    automation_seconds = sum(r.get("automation_seconds", 0) for r in success_runs)

    # Calculate Sites Migrated (Unique Slugs)
    if is_all_time:
        # Use the preserved 'migrations' lists from files (accurate global count)
        all_unique_slugs = set()
        for slugs in user_migrations.values():
            all_unique_slugs.update(slugs)
        sites_migrated = len(all_unique_slugs)
    else:
        # For filtered periods, we must rely on the filtered runs
        sites_migrated = len({r.get("slug") for r in success_runs if r.get("slug")})

    # Mathematical time saved: 1 hour per 800 lines (SBM standard metric)
    time_saved_hours = lines_migrated / 800.0

    # Contributors Ranking
    contributors: Dict[str, Dict[str, Any]] = {}

    if is_all_time:
        # Rank by Sites Migrated (from full history) to match CLI
        for user, slugs in user_migrations.items():
            contributors[user] = {
                "sites": len(slugs),
                "lines": 0,  # We don't have accurate lines for all time due to truncation
                "runs": 0,
            }

        # Add run stats just for display if we have them
        for r in success_runs:
            u = r.get("_user", "unknown")
            if u in contributors:
                contributors[u]["lines"] += r.get("lines_migrated", 0)
    else:
        # Rank by Sites Migrated (within period)
        for r in success_runs:
            u = r.get("_user", "unknown")
            slug = r.get("slug")
            lines = r.get("lines_migrated", 0)

            if u not in contributors:
                contributors[u] = {"sites": set(), "lines": 0, "runs": 0}

            if slug:
                contributors[u]["sites"].add(slug)  # type: ignore
            contributors[u]["lines"] += lines
            contributors[u]["runs"] += 1

        # Convert sets to counts
        for data in contributors.values():
            if isinstance(data["sites"], set):
                data["sites"] = len(data["sites"])

    # Sort contributors by SITES (descending), then lines
    top_contributors = sorted(
        contributors.items(), key=lambda x: (x[1]["sites"], x[1]["lines"]), reverse=True
    )[:3]

    return {
        "total_runs": total_runs,
        "success_count": success_count,
        "success_rate": (success_count / total_runs * 100) if total_runs > 0 else 0,
        "sites_migrated": sites_migrated,
        "lines_migrated": lines_migrated,
        "time_saved_hours": round(time_saved_hours, 1),
        "automation_hours": round(automation_seconds / 3600, 2),
        "top_contributors": top_contributors,
    }


def calculate_global_metrics_all_time() -> Dict[str, Any]:
    """Calculate all-time global metrics using Firebase runs + legacy migrations."""
    all_runs, user_migrations = load_all_stats()
    return calculate_metrics(all_runs, user_migrations, is_all_time=True)


def format_slack_payload(
    metrics: Dict[str, Any],
    period: str,
    context_label: str | None = None,
    top_n: int | None = None,
) -> Dict[str, Any]:
    """Format metrics into a Slack Block Kit payload."""
    now = datetime.now(timezone.utc)

    if period.lower() == "all":
        period_label = "All Time"
        date_range_str = "Project Inception - Present"
    else:
        days = get_days_from_period(period)
        start_date = now - timedelta(days=days)
        # Format: "Dec 30 - Jan 06"
        date_range_str = f"{start_date.strftime('%b %d')} - {now.strftime('%b %d')}"
        period_label = "24 Hours" if days == 1 else f"{days} Days"

    has_activity = metrics.get("success_count", 0) > 0 or metrics.get("sites_migrated", 0) > 0
    if not has_activity:
        text = f"No SBM migrations recorded in the period ({period_label})."
        return {
            "text": text,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*No Activity*\n{text}",
                    },
                },
                {
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": f"Period: {date_range_str}"}],
                },
            ],
        }

    # Determine command label for display
    p_lower = period.lower()
    if p_lower in ["day", "daily", "1"]:
        cmd_label = "/sbm-stats day"
    elif p_lower in ["week", "weekly", "7"]:
        cmd_label = "/sbm-stats week"
    elif p_lower in ["month", "monthly", "30"]:
        cmd_label = "/sbm-stats month"
    elif p_lower == "all":
        cmd_label = "/sbm-stats all"
    else:
        cmd_label = f"/sbm-stats {period}"

    summary_text = (
        f"SBM Stats: {metrics['sites_migrated']} sites, "
        f"{metrics['time_saved_hours']}h saved ({date_range_str})."
    )

    blocks = []

    # 1. Main Header with Date Context
    blocks.append(
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"SBM Stats — {date_range_str}", "emoji": False},
        }
    )

    # 2. Command Context (Subtitle)
    blocks.append(
        {"type": "context", "elements": [{"type": "mrkdwn", "text": f"Command: `{cmd_label}`"}]}
    )

    blocks.append({"type": "divider"})

    # 3. Primary Metrics Grid
    # Using bold numbers for visual impact
    blocks.append(
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Sites Migrated*\n*{metrics['sites_migrated']}*"},
                {"type": "mrkdwn", "text": f"*Est. Time Saved*\n*{metrics['time_saved_hours']}h*"},
            ],
        }
    )

    # 4. Secondary Metrics Grid
    blocks.append(
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Lines of Code*\n{metrics['lines_migrated']:,}"},
                {"type": "mrkdwn", "text": f"*Success Rate*\n{metrics['success_rate']:.1f}%"},
            ],
        }
    )

    # 5. Top Contributors (Optional)
    if top_n and metrics["top_contributors"]:
        blocks.append({"type": "divider"})
        ranked = []
        for idx, (u, data) in enumerate(metrics["top_contributors"][:top_n], start=1):
            # E.g. "1. nate-hart-di (5 sites)"
            ranked.append(f"*{idx}. {u}* — {data['sites']} sites")

        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Top Contributors*\n" + "\n".join(ranked)},
            }
        )

    # Separation Divider (Bottom)
    blocks.append({"type": "divider"})

    return {
        "text": summary_text,
        "blocks": blocks,
    }


def send_slack_message_webhook(webhook_url: str, payload: Dict[str, Any]) -> None:
    """Send payload via Incoming Webhook."""
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url, data=data, headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                print(
                    f"Error sending to Slack (Webhook): {response.status} {response.read().decode()}",
                    file=sys.stderr,
                )
                sys.exit(1)
            else:
                print("Successfully sent report to Slack via Webhook.")

    except Exception as e:
        print(f"Exception sending to Slack (Webhook): {e}", file=sys.stderr)
        sys.exit(1)


def send_slack_message_api(token: str, channel: str, payload: Dict[str, Any]) -> None:
    """Send payload via Slack Web API (chat.postMessage)."""
    try:
        # Web API requires the 'channel' in the JSON body
        api_payload = payload.copy()
        api_payload["channel"] = channel

        data = json.dumps(api_payload).encode("utf-8")
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )

        with urllib.request.urlopen(req) as response:
            resp_data = json.loads(response.read().decode())
            if not resp_data.get("ok"):
                print(
                    f"Error sending to Slack (API): {resp_data.get('error')}",
                    file=sys.stderr,
                )
                if resp_data.get("error") == "not_in_channel":
                    print("Hint: Invite the bot to the channel first!", file=sys.stderr)
                sys.exit(1)
            else:
                print(f"Successfully sent report to Slack channel {channel} via Web API.")

    except Exception as e:
        print(f"Exception sending to Slack (API): {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Entry point."""
    args = parse_args()

    # 1. Load Data
    # 1. Load Data
    all_runs, user_migrations = load_all_stats()

    # 2. Filter
    filtered_runs = filter_runs_by_date(all_runs, args.period)

    # 3. Aggregate
    is_all_time = args.period.lower() == "all"
    if is_all_time:
        metrics = calculate_global_metrics_all_time()
    else:
        metrics = calculate_metrics(filtered_runs, user_migrations, is_all_time)

    # 4. Format
    payload = format_slack_payload(
        metrics,
        args.period,
        context_label="Auto-SBM report • CLI",
    )

    # 5. Branding
    if args.username:
        payload["username"] = args.username
    if args.icon_url:
        payload["icon_url"] = args.icon_url

    # 6. Send or Print
    if args.dry_run:
        print(json.dumps(payload, indent=2))
    elif args.token and args.channel:
        send_slack_message_api(args.token, args.channel, payload)
    elif args.webhook_url:
        send_slack_message_webhook(args.webhook_url, payload)
    else:
        print(
            "Error: No Slack credentials provided. Either:",
            file=sys.stderr,
        )
        print("  - Set SLACK_BOT_TOKEN and SLACK_CHANNEL", file=sys.stderr)
        print("  - OR set SLACK_WEBHOOK_URL", file=sys.stderr)
        print("\nUse --dry-run to test locally.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
