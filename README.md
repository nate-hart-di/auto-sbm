# Auto-SBM

Current version: 2.8.0
Auto-SBM automates DealerInspire Site Builder migrations. It converts legacy SCSS themes
to Site Builder format, validates output, and tracks migration stats with optional Slack
reporting.

## Highlights

- End-to-end theme migration with validation and reporting
- Stats tracking for runs, lines migrated, and time saved
- Slack reporting (webhook, bot token, or Socket Mode)
- Built-in update and environment repair flows

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

Restart your terminal or run:

```bash
source ~/.zshrc
```

## Quick Start

Run a migration:

```bash
sbm <theme-slug>
```

Example:

```bash
sbm fiatofportland
```

## Common Commands

```bash
# Run full automation mode (default)
# Note: Now supports automated retry for failed slugs!
sbm auto

# Show migration stats
sbm stats
sbm stats --history --limit 10
sbm stats --history --since 2024-01-01 --until 2024-02-01
sbm stats --history --user nate

# Check version and recent changes
sbm version
sbm version --changelog

# Update auto-sbm manually
sbm update

# Control auto-update behavior
sbm auto-update status
sbm auto-update disable
sbm auto-update enable
```

## Firebase Team Stats

Migration runs sync to Firebase for team-wide statistics.

### Team Members (Default)

Anonymous auth is used for reads/writes. Add the database URL and API key to your `.env`
or let `sbm setup` store them in your system keychain:

```bash
FIREBASE__DATABASE_URL=https://auto-sbm-default-rtdb.firebaseio.com
FIREBASE__API_KEY=your-firebase-web-api-key
```

Stats commands work automatically:

```bash
sbm stats          # Personal stats from Firebase
sbm stats --team   # Team leaderboard
sbm stats --history  # Run history
```

## Migration Reports

Successful migrations generate markdown reports in `.sbm-reports/` and update
`.sbm-reports/index.md`. Run history shows the report path.

```bash
ls .sbm-reports
```

## Bulk Duplicate Prevention

Bulk migrations (`sbm @input.txt`) warn about slugs already migrated by teammates
and let you skip duplicates before running.

### Admin Setup

Admins with full access need the service account credentials (API key optional):

```bash
FIREBASE__DATABASE_URL=https://auto-sbm-default-rtdb.firebaseio.com
FIREBASE__CREDENTIALS_PATH=/path/to/firebase-adminsdk.json
```

> ⚠️ Never commit the credentials JSON file to git.


## Slack Reporting

Channel report via webhook:

```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
python3 scripts/stats/report_slack.py --period week
```

Channel report via bot token:

```bash
export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_CHANNEL="C0123456789"
python3 scripts/stats/report_slack.py --period week
```

Slash command listener (Socket Mode):

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

Scheduled reports (9am CST):

```bash
export SLACK_CHANNELS="C0123456789,C0987654321"
python3 scripts/stats/scheduled_slack_reports.py
```

Behavior:
- Tue–Fri: daily report for previous day
- Mon: weekly report for previous week + leaderboard
- 1st of month: monthly report + all-time leaderboard

## Troubleshooting

`sbm` command not found:

```bash
cd ~/auto-sbm
rm -f .sbm_setup_complete
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
bash setup.sh
```

## Development

See `docs/DEVELOPMENT.md` for dev workflow and testing.

## Changelog

See `CHANGELOG.md`.
