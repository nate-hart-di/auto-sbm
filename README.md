# Auto-SBM

Automated migration tool for DealerInspire sites. Converts legacy SCSS themes to Site Builder format and tracks migration stats.

## Features

- Automated SCSS migration with rich terminal progress
- Background updates and stats tracking
- Slack reporting (webhook or Socket Mode)

## Requirements

- macOS with Terminal access
- GitHub access to this repo
- DI Websites Platform cloned to `~/di-websites-platform`

## Install

```bash
cd ~
git clone git@github.com:nate-hart-di/auto-sbm.git
cd auto-sbm
bash setup.sh
```

After install, restart your terminal or run:

```bash
source ~/.zshrc
```

## Run a Migration

```bash
sbm {theme-slug}
```

Example:

```bash
sbm fiatofportland
```

## Stats (CLI)

```bash
sbm stats
```

## Slack Reporting

### Channel Report (Webhook or Bot Token)

```bash
# Webhook
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
python3 scripts/stats/report_slack.py --period week

# Bot token
export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_CHANNEL="C0123456789"
python3 scripts/stats/report_slack.py --period week
```

### Slash Command (Socket Mode)

Run the listener (must stay up):

```bash
python3 scripts/stats/slack_listener.py
```

Usage:

```
/sbm-stats
/sbm-stats day
/sbm-stats week
/sbm-stats month
/sbm-stats 14
/sbm-stats week nate
/sbm-stats top
/sbm-stats week top 5
```

### Slack App Description (copy/paste)

Auto SBM Stats keeps migration progress visible without leaving Slack.
Track sites migrated, lines moved, and estimated time saved, plus lightweight leaderboards.
Built to stay in sync with the Auto-SBM CLI so your numbers always match.

### Scheduled Reports (9am CST)

Set `SLACK_CHANNELS` (comma-separated channel IDs) and schedule the daily job at 9am CST:

```bash
export SLACK_CHANNELS="C0123456789,C0987654321"
python3 scripts/stats/scheduled_slack_reports.py
```

Behavior:
- Tue–Fri: daily report for previous day
- Mon: weekly report for previous week + leaderboard
- 1st of month: monthly report + all-time leaderboard

Note: launchd runs only when the Mac is awake and logged in.

## Launch Agent (Optional)

If you want the listener to stay up on your Mac:

```bash
launchctl bootout gui/$UID "/Users/nathanhart/Library/LaunchAgents/com.dealerinspire.sbm-stats.plist" || true
launchctl bootstrap gui/$UID "/Users/nathanhart/Library/LaunchAgents/com.dealerinspire.sbm-stats.plist"
launchctl list | rg sbm
```

Logs:

```bash
tail -n 50 /tmp/sbm-stats.out
tail -n 50 /tmp/sbm-stats.err
```

## Changelog

See `CHANGELOG.md`.
