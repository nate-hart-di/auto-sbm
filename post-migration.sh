#!/bin/bash
# Post-migration helper script for SBM projects
#
# Note: This script works best with GitHub CLI (gh) installed.
# To install GitHub CLI, follow the instructions at https://cli.github.com/
# You'll need to authenticate with 'gh auth login' before using this script.

# Check if slug argument is provided
if [ -z "$1" ]; then
  echo "Usage: ./post-migration.sh <dealer-slug>"
  exit 1
fi

# Ensure slug is lowercase
SLUG=$(echo "$1" | tr '[:upper:]' '[:lower:]')
# Simple dealer name conversion - capitalize first letter
DEALER_NAME=$(echo "${SLUG^}")

# Make sure platform directory exists
PLATFORM_DIR=${DI_WEBSITES_PLATFORM_DIR:-"/Users/nathanhart/di-websites-platform"}
if [ ! -d "$PLATFORM_DIR" ]; then
  echo "Error: Platform directory not found at $PLATFORM_DIR"
  echo "Please ensure DI_WEBSITES_PLATFORM_DIR is set correctly"
  exit 1
fi

# Define and verify dealer directory exists
DEALER_DIR="${PLATFORM_DIR}/dealer-themes/${SLUG}"
if [ ! -d "$DEALER_DIR" ]; then
  echo "Error: Dealer directory not found at $DEALER_DIR"
  echo "Please ensure the dealer slug is correct"
  exit 1
fi

echo "Changing to dealer directory: $DEALER_DIR"
cd "$DEALER_DIR"

# Verify we're in a git repository
if [ ! -d "$PLATFORM_DIR/.git" ]; then
  echo "Error: Not a git repository at $PLATFORM_DIR"
  echo "Please ensure you're in the correct directory"
  exit 1
fi

# Get the current branch name directly from git
BRANCH_NAME=$(git branch --show-current)
if [ -z "$BRANCH_NAME" ] || [ "$BRANCH_NAME" = "main" ]; then
  # Create a new branch if we're on main or can't detect branch
  CURRENT_DATE=$(date +"%m%y")
  BRANCH_NAME="${SLUG}-sbm${CURRENT_DATE}"
  echo "Creating new branch: $BRANCH_NAME"
  git checkout -b "$BRANCH_NAME"
  if [ $? -ne 0 ]; then
    echo "Warning: Failed to create new branch. Attempting to use existing branch or create with force..."
    git checkout -B "$BRANCH_NAME"
    if [ $? -ne 0 ]; then
      echo "Error: Could not create branch $BRANCH_NAME"
      exit 1
    fi
  fi
fi

echo "Working on branch: $BRANCH_NAME"

# Check the status to confirm changes
echo "Checking git status..."
git status

# Show the commands that will be executed
echo ""
echo "The following commands will be executed:"
echo "  git add ."
echo "  git commit -m \"${DEALER_NAME} SBM FE Audit\""
echo "  git push origin ${BRANCH_NAME}"
echo ""

# Ask for confirmation
echo -n "Are you sure you want to commit and push all changes for ${DEALER_NAME}? (y/n) "
read confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
  echo "Operation cancelled"
  exit 0
fi

# Proceed with commit and push
echo "Executing: git add ."
git add .
echo "Executing: git commit -m \"${DEALER_NAME} SBM FE Audit\""
git commit -m "${DEALER_NAME} SBM FE Audit"

# Check if branch exists on remote
REMOTE_EXISTS=$(git ls-remote --heads origin $BRANCH_NAME | wc -l | tr -d ' ')
PUSH_COMMAND="git push origin $BRANCH_NAME"

# If branch doesn't exist on remote, use --set-upstream
if [ "$REMOTE_EXISTS" -eq "0" ]; then
  echo "Branch doesn't exist on remote, setting upstream..."
  PUSH_COMMAND="git push --set-upstream origin $BRANCH_NAME"
fi

echo "Executing: $PUSH_COMMAND"
PUSH_OUTPUT=$(eval $PUSH_COMMAND 2>&1)
PUSH_EXIT_CODE=$?
echo "$PUSH_OUTPUT"

# Check if push failed for any reason
if [ $PUSH_EXIT_CODE -ne 0 ]; then
  echo "Push failed. PR creation will be skipped."
  echo "Please manually push your changes and create a PR."
  exit 1
fi

# Extract PR link from git push output if successful
PR_LINK=$(echo "$PUSH_OUTPUT" | grep -o 'https://github.com/[^ ]*' | head -1)

echo "Changes committed and pushed to ${BRANCH_NAME}"

# Generate PR description
PR_CONTENT="## What
Added interior page styles to sb-inside.scss
  - Migrated sitemap styles
  - Added menu item styles
  - Integrated map component styles
  - Added cookie banner styles

## Why
Site Builder Migration

## Instructions for Reviewers
Within the di-websites-platform directory:
\`\`\`bash
git checkout main
git pull
git checkout ${BRANCH_NAME}
just start ${SLUG} prod
\`\`\`
- Review all code found in \"Files Changed\"
- Open up a browser, go to localhost
- Verify that homepage and interior pages load properly
- Request changes as needed"

# PR title
PR_TITLE="${SLUG} SBM FE Audit"

# Copy PR description to clipboard based on OS
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS
  echo -e "$PR_CONTENT" | pbcopy
  echo "PR description copied to clipboard!"
else
  echo "PR description not automatically copied to clipboard on this OS."
fi

echo "======================================"
echo "PR Title: ${PR_TITLE}"
echo "======================================"
echo "PR Description (also copied to clipboard on macOS):"
echo "======================================"
echo "$PR_CONTENT"
echo "======================================"

# Open PR link in browser with prefilled title and body if available
if [ -n "$PR_LINK" ]; then
  # Set default reviewers and label
  ALL_REVIEWERS="evantritt,abondDealerInspire,messponential,tcollier-di,sarahsargent,nate-hart-di"
  LABELS="fe-dev"
  
  # Get current GitHub user if GitHub CLI is available
  CURRENT_USER=""
  if command -v gh &> /dev/null; then
    CURRENT_USER=$(gh api user --jq '.login' 2>/dev/null || echo "")
  fi
  
  # Remove current user from reviewers list if found
  if [ -n "$CURRENT_USER" ]; then
    REVIEWERS=$(echo "$ALL_REVIEWERS" | tr ',' '\n' | grep -v "^$CURRENT_USER$" | tr '\n' ',' | sed 's/,$//')
  else
    REVIEWERS="$ALL_REVIEWERS"
  fi
  
  # Check if GitHub CLI is available
  if command -v gh &> /dev/null; then
    echo "GitHub CLI detected. Creating PR with CLI and opening in browser..."
    
    # Debug info
    echo "Using head branch: $BRANCH_NAME for PR creation"
    echo "Command: gh pr create --title \"$PR_TITLE\" --body \"$PR_CONTENT\" --draft --reviewer \"$REVIEWERS\" --label \"$LABELS\" --head \"$BRANCH_NAME\""
    
    # Check if PR already exists
    EXISTING_PR=$(gh pr list --head "$BRANCH_NAME" --json number,url,title --state "open" --jq '.[0].url')
    
    if [ -n "$EXISTING_PR" ]; then
      echo "PR already exists for branch $BRANCH_NAME"
      echo "Opening existing PR in browser..."
      PR_URL="$EXISTING_PR"
    else
      # Create PR using GitHub CLI with explicit head branch and capture the URL
      PR_URL=$(gh pr create --title "$PR_TITLE" --body "$PR_CONTENT" --draft --reviewer "$REVIEWERS" --label "$LABELS" --head "$BRANCH_NAME" 2>&1)
      # Check if PR creation was successful
      if [ $? -ne 0 ]; then
        echo "Error creating PR: $PR_URL"
        echo "You may need to create the PR manually at: https://github.com/carsdotcom/di-websites-platform/pull/new/$BRANCH_NAME"
        # Try to extract URL from error message if possible
        MANUAL_PR_URL=$(echo "$PR_URL" | grep -o 'https://github.com/[^ ]*' | head -1)
        if [ -n "$MANUAL_PR_URL" ]; then
          PR_URL="$MANUAL_PR_URL"
        else
          PR_URL="https://github.com/carsdotcom/di-websites-platform/pull/new/$BRANCH_NAME"
        fi
      fi
    fi
    
    echo "PR created: $PR_URL"
    
    # Open the created PR in browser
    if [[ "$OSTYPE" == "darwin"* ]]; then
      open "$PR_URL"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
      xdg-open "$PR_URL" &> /dev/null
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
      start "$PR_URL"
    else
      echo "Please visit the PR URL manually: $PR_URL"
    fi
    
    echo "PR created and opened in browser. Please review before publishing."
  else
    echo "GitHub CLI not detected. Opening PR creation page in your browser..."
    
    # URL encode the PR description and title for query parameters
    # This is a simplified URL encoding, more complex content might need a more robust approach
    URL_ENCODED_TITLE=$(echo "$PR_TITLE" | sed 's/ /%20/g')
    
    # For macOS, we can use Python to handle URL encoding of the body
    if [[ "$OSTYPE" == "darwin"* ]]; then
      URL_ENCODED_BODY=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$PR_CONTENT'''))")
      FULL_PR_URL="${PR_LINK}?title=${URL_ENCODED_TITLE}&body=${URL_ENCODED_BODY}"
      open "$FULL_PR_URL"
    else
      # For other platforms, just open the base URL and let user paste the description
      echo "Opening PR creation page without prefilled fields. Please paste the description manually."
      if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open "$PR_LINK" &> /dev/null
      elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        start "$PR_LINK"
      else
        echo "Couldn't automatically open the browser. PR creation link: $PR_LINK"
      fi
    fi
    
    echo "Please add the following manually:"
    echo "- Reviewers: $REVIEWERS"
    echo "- Label: $LABELS"
    echo "- Set as draft PR if needed"
  fi
else
  echo "No PR link detected. Please create the PR manually at GitHub."
  echo "Use this title: ${PR_TITLE}"
  echo "Suggested reviewers: @evantritt, @abondDealerInspire, @messponential, @tcollier-di, @sarahsargent, @nate-hart-di"
  echo "Suggested label: fe-dev"
fi
