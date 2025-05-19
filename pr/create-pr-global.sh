#!/bin/bash
# Global PR Creation Script
# Creates GitHub PRs for any project, with support for Site Builder Migration (SBM).
# Usage: ./create-pr-global.sh [options]
# Alias: pr (assumed from .zshrc)

# Requirements:
# - Git (v2.30+)
# - GitHub CLI (gh, v2.0+)
# - Optional: pbcopy (macOS), xclip/wl-copy (Linux), clip.exe (Windows)
# - For SBM: dealer-themes/<slug> directory structure

# Source modules
source "$(dirname "$0")/pr_config.sh"
source "$(dirname "$0")/pr_content.sh"
source "$(dirname "$0")/pr_utils.sh"

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# Default settings
DEFAULT_BRANCH="main"
DEFAULT_HEAD=""
DEFAULT_TITLE=""
DEFAULT_REVIEWERS="carsdotcom/fe-dev"
DEFAULT_LABELS="fe-dev"
DEFAULT_INSTRUCTIONS="Review the changes in the Files Changed tab."
DEFAULT_DRAFT=true
SBM_MODE=false
CONFIG_FILE="$HOME/.pr-global-config"
PR_TYPE=""

# Load config
load_config

# Display help
show_help() {
  echo -e "${BLUE}Global PR Creation Script${NC}"
  echo "Creates GitHub PRs for any project, with SBM support."
  echo ""
  echo "Usage: $0 [options]"
  echo ""
  echo "Options:"
  echo "  -t, --title TITLE           Set PR title"
  echo "  -w, --what WHAT             Set 'What' section content"
  echo "  -y, --why WHY               Set 'Why' section content"
  echo "  -r, --reviewers REVIEWERS   Set reviewers (comma-separated)"
  echo "  -l, --labels LABELS         Set labels (comma-separated)"
  echo "  -i, --instructions TEXT     Set review instructions"
  echo "  -b, --base BRANCH           Set base branch (default: main)"
  echo "  -e, --head BRANCH           Set head branch (default: current)"
  echo "  -p, --publish               Create as published PR (not draft)"
  echo "  -s, --sbm                   Enable SBM mode (auto-detects slug)"
  echo "  -c, --configure             Save defaults to ~/.pr-global-config"
  echo "  -T, --type TYPE             PR type (e.g., production)"
  echo "  -h, --help                  Show this help"
  echo ""
  echo "Examples:"
  echo "  $0 --title 'Add feature' --what 'Added X' --why 'Improves UX'"
  echo "  $0 --sbm --reviewers 'user1,user2' --labels 'fe-dev'"
  echo "  $0 --type production --title 'example-site - New Site'"
  echo "  $0 --configure"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -t | --title)
      TITLE="$2"
      shift 2
      ;;
    -w | --what)
      WHAT="$2"
      shift 2
      ;;
    -y | --why)
      WHY="$2"
      shift 2
      ;;
    -r | --reviewers)
      REVIEWERS="$2"
      shift 2
      ;;
    -l | --labels)
      LABELS="$2"
      shift 2
      ;;
    -i | --instructions)
      INSTRUCTIONS="$2"
      shift 2
      ;;
    -b | --base)
      DEFAULT_BRANCH="$2"
      shift 2
      ;;
    -e | --head)
      DEFAULT_HEAD="$2"
      shift 2
      ;;
    -p | --publish)
      DEFAULT_DRAFT=false
      shift
      ;;
    -s | --sbm)
      SBM_MODE=true
      shift
      ;;
    -c | --configure)
      SAVE_CONFIG=true
      shift
      ;;
    -T | --type)
      PR_TYPE="$2"
      shift 2
      ;;
    -h | --help)
      show_help
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      show_help
      exit 1
      ;;
  esac
done

# Validate environment
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  echo -e "${RED}Error: Not in a Git repository${NC}"
  exit 1
fi
if ! command -v gh > /dev/null 2>&1; then
  echo -e "${RED}Error: GitHub CLI (gh) not installed${NC}"
  echo "Install: https://cli.github.com/manual/installation"
  exit 1
fi
if ! gh auth status > /dev/null 2>&1; then
  echo -e "${RED}Error: Not authenticated with GitHub CLI${NC}"
  echo "Run: gh auth login"
  exit 1
fi

# Get repository info
REPO_NAME=$(basename "$(git rev-parse --show-toplevel)")
CURRENT_BRANCH=$(git branch --show-current)
if [ -z "$CURRENT_BRANCH" ]; then
  echo -e "${RED}Error: Not on a Git branch${NC}"
  exit 1
fi
HEAD_BRANCH=${DEFAULT_HEAD:-$CURRENT_BRANCH}

# Set PR_TYPE to production if in dealer-themes directory
CURRENT_DIR=$(pwd)
if [[ "$CURRENT_DIR" == *"dealer-themes"* ]]; then
  PR_TYPE="production"
  SLUG=$(basename "$CURRENT_DIR")
fi

# Build PR content
build_pr_content

# Save config if requested
if [ "$SAVE_CONFIG" = true ]; then
  save_config
fi

# Copy PR description
copy_to_clipboard "$PR_CONTENT" || echo -e "${YELLOW}Copied to pr_description.txt${NC}"

# Display PR details
echo "======================================"
echo -e "${BLUE}PR Title:${NC} ${TITLE}"
echo "======================================"
echo -e "${BLUE}PR Description:${NC}"
echo "======================================"
echo "$PR_CONTENT"
echo "======================================"

# SBM: Salesforce update
if [ "$SBM_MODE" = true ]; then
  SALESFORCE_UPDATE="Site Builder Migration Notes:
${WHAT}
Pull Request Link: (created PR URL)"
  copy_to_clipboard "$SALESFORCE_UPDATE" || echo -e "${YELLOW}Salesforce update copied to salesforce_update.txt${NC}"
  echo "======================================"
  echo -e "${BLUE}Salesforce Update:${NC}"
  echo "======================================"
  echo "$SALESFORCE_UPDATE"
  echo "======================================"
fi

# Confirm creation
read -p "Create PR with these details? [Y/n] " confirm
if [[ "$confirm" =~ ^[Nn]$ ]]; then
  echo -e "${YELLOW}PR creation cancelled${NC}"
  exit 0
fi

# Create PR
REVIEWERS=${REVIEWERS:-$DEFAULT_REVIEWERS}
LABELS=${LABELS:-$DEFAULT_LABELS}
GH_CMD="gh pr create --title '$TITLE' --body \"$(echo -e "$PR_CONTENT")\" --base '$DEFAULT_BRANCH' --head '$HEAD_BRANCH'"
if [ "$DEFAULT_DRAFT" = true ]; then
  GH_CMD="$GH_CMD --draft"
fi
if [ -n "$REVIEWERS" ]; then
  GH_CMD="$GH_CMD --reviewer '$REVIEWERS'"
fi
if [ -n "$LABELS" ]; then
  GH_CMD="$GH_CMD --label '$LABELS'"
fi

echo -e "${BLUE}Creating PR...${NC}"
PR_URL=$(bash -c "$GH_CMD" 2>&1)
if [ $? -ne 0 ]; then
  echo -e "${RED}Error creating PR: $PR_URL${NC}"
  exit 1
fi

# Update Salesforce content with PR URL
if [ "$SBM_MODE" = true ]; then
  SALESFORCE_UPDATE="Site Builder Migration Notes:
${WHAT}
Pull Request Link: $PR_URL"
  copy_to_clipboard "$SALESFORCE_UPDATE" || echo -e "${YELLOW}Salesforce update copied to salesforce_update.txt${NC}"
fi

# Open PR in browser
open_in_browser "$PR_URL"

echo -e "${GREEN}PR created: $PR_URL${NC}"
echo -e "${GREEN}PR opened in browser. Review before publishing.${NC}"
