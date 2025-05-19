Global PR Creation Script
A standalone Bash script for creating GitHub pull requests (PRs) for any project, with support for Site Builder Migration (SBM) workflows.
Requirements

Git: v2.30+
GitHub CLI (gh): v2.0+, authenticated (gh auth login)
Shell: Bash or Zsh
Clipboard Tools (optional):
macOS: pbcopy
Linux: xclip (X11) or wl-copy (Wayland)
Windows: clip.exe

SBM: dealer-themes/<slug> directory structure

Setup

Place scripts in a directory (e.g., ~/scripts/pr):
create-pr-global.sh
pr_config.sh
pr_content.sh
pr_utils.sh

Make executable:chmod +x \*.sh

Add to .zshrc:alias pr="$HOME/scripts/pr/create-pr-global.sh"

Source .zshrc:source ~/.zshrc

Usage
Run: pr [options]
Options

-t, --title TITLE: PR title
-w, --what WHAT: Changes made
-y, --why WHY: Reason for changes
-r, --reviewers REVIEWERS: Comma-separated GitHub usernames or teams
-l, --labels LABELS: Comma-separated labels
-i, --instructions TEXT: Review instructions
-b, --base BRANCH: Base branch (default: main)
-e, --head BRANCH: Head branch (default: current)
-p, --publish: Create published PR
-s, --sbm: Enable SBM mode
-c, --configure: Save defaults
-T, --type TYPE: PR type (e.g., production)
-h, --help: Show help

Examples

General PR:pr --title "Add feature" --what "Added X" --why "Improves UX"

SBM PR:cd dealer-themes/<slug>
pr --sbm

Production Deploy PR:cd dealer-themes/<slug>
pr --type production

Save defaults:pr --reviewers "user1,user2" --configure

Configuration
Defaults are stored in ~/.pr-global-config. Example:
DEFAULT_BRANCH="main"
DEFAULT_REVIEWERS="user1,user2"
DEFAULT_LABELS="enhancement"
DEFAULT_INSTRUCTIONS="Review Files Changed tab."
DEFAULT_DRAFT=false

Notes

SBM mode auto-detects dealer slug and sets SBM-specific title, reviewers, and Salesforce update.
Production type auto-detects slug and sets predefined content for deploying to production.
PR description and Salesforce update (SBM) are copied to clipboard or files (pr_description.txt, salesforce_update.txt).
