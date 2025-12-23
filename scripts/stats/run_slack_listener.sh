#!/bin/sh
set -eu

# Ensure OAuth env vars don't force Bolt into OAuth mode.
unset SLACK_CLIENT_ID
unset SLACK_CLIENT_SECRET

exec /Users/nathanhart/auto-sbm/.venv/bin/python3 -u /Users/nathanhart/auto-sbm/scripts/stats/slack_listener.py
