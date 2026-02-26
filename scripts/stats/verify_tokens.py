import os
import sys

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Load env manually to be super sure
env_path = os.path.join(os.getcwd(), ".env")
print(f"Loading .env from: {env_path}")

vars = {}
try:
    with open(env_path) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                vars[key] = value
except FileNotFoundError:
    print("❌ .env file not found!")
    sys.exit(1)

bot_token = vars.get("SLACK_BOT_TOKEN") or vars.get("SLACK_BOT_OAUTH")
app_token = vars.get("SLACK_APP_TOKEN")

print("\n--- Token Check ---")
if bot_token:
    print(f"BOT TOKEN: {bot_token[:10]}... (Length: {len(bot_token)})")
else:
    print("❌ BOT TOKEN MISSING (SLACK_BOT_TOKEN or SLACK_BOT_OAUTH)")

if app_token:
    print(f"APP TOKEN: {app_token[:10]}... (Length: {len(app_token)})")
else:
    print("❌ APP TOKEN MISSING (SLACK_APP_TOKEN)")

if not app_token:
    print("❌ Critical: SLACK_APP_TOKEN is missing.")
    sys.exit(1)

client = WebClient(token=app_token)

print("\n--- Attempting apps.connections.open ---")
try:
    # This is the exact call failing in local logs
    response = client.apps_connections_open(app_token=app_token)
    print("✅ Success! Connection URL received.")
    print(f"   URL: {response.get('url')[:30]}...")
except SlackApiError as e:
    print(f"❌ API Error: {e.response['error']}")
    print("   Full Response:", e.response.data)

print("\n--- Checking Bot Identity ---")
bot_client = WebClient(token=bot_token)
try:
    auth = bot_client.auth_test()
    print(f"✅ Authenticated as: {auth['user']} ({auth['user_id']})")
    print(f"   Team: {auth['team']} ({auth['team_id']})")
    print(f"   App ID from Token: {auth.get('app_id', 'Unknown')}")

    env_app_id = vars.get("SLACK_APP_ID")
    token_app_id = auth.get("app_id")
    if env_app_id:
        if token_app_id:
            if token_app_id != env_app_id:
                print(f"❌ MISMATCH: Token belongs to {token_app_id}, but .env has {env_app_id}")
            else:
                print(f"✅ App ID matches .env: {env_app_id}")
        else:
            print("ℹ️  Slack did not return app_id for this bot token; skipping app ID match.")
except SlackApiError as e:
    print(f"❌ Bot Token Error: {e.response['error']}")
