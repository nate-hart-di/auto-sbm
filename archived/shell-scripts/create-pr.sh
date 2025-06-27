#!/bin/bash
# Create PR script for SBM projects

# Check if slug argument is provided
if [ -z "$1" ]; then
  echo "Usage: ./create-pr.sh <dealer-slug> <branch-name>"
  exit 1
fi

# Accept branch name as second parameter or use default naming convention
if [ -z "$2" ]; then
  # Fallback to default naming convention if branch name not provided
  CURRENT_DATE=$(date +"%m%y")
  BRANCH_NAME="${SLUG}-sbm${CURRENT_DATE}"
else
  BRANCH_NAME="$2"
fi

# Ensure slug is lowercase
SLUG=$(echo "$1" | tr '[:upper:]' '[:lower:]')

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

# PR title follows standard format
PR_TITLE="${SLUG} SBM FE Audit"

# Generate PR description
PR_CONTENT="## What

Transferred vrp styles to sb-vrp.scss
Transferred vdp styles to sb-vdp.scss
Added interior page styles to sb-inside.scss

## Why

Site Builder Migration

## Instructions for Reviewers

To review this PR:

\`\`\`bash
git checkout main
git pull
git checkout ${BRANCH_NAME}
just start ${SLUG} prod
\`\`\`

After starting the site:

- Review all code found in \"Files Changed\"
- Open up a browser, go to localhost
- Verify that homepage loads properly and no errors occur.
- Request changes as needed"

# Set default reviewers and label
ALL_REVIEWERS="evantritt,abondDealerInspire,messponential,tcollier-di,sarahsargent,nate-hart-di,brandonstranc"
LABELS="fe-dev"

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

# Check if GitHub CLI is available
if ! command -v gh &> /dev/null; then
  echo "Error: GitHub CLI (gh) is not installed."
  echo "Please install it first: https://cli.github.com/manual/installation"
  exit 1
fi

# Get current GitHub user
CURRENT_USER=$(gh api user --jq '.login' 2>/dev/null || echo "")
if [ -n "$CURRENT_USER" ]; then
  echo "Creating PR as user: $CURRENT_USER"
  REVIEWERS=$(echo "$ALL_REVIEWERS" | tr ',' '\n' | grep -v "^$CURRENT_USER$" | tr '\n' ',' | sed 's/,$//')
else
  echo "Warning: Could not determine current GitHub user."
  REVIEWERS="$ALL_REVIEWERS"
fi

echo "Creating PR with reviewers: $REVIEWERS"

# Create PR using GitHub CLI and capture the URL
echo "Creating PR..."
PR_URL=$(gh pr create --title "$PR_TITLE" --body "$PR_CONTENT" --draft --reviewer "$REVIEWERS" --label "$LABELS")

if [ $? -ne 0 ]; then
  echo "Error creating PR. Please check the error message above."
  exit 1
fi

echo "PR created: $PR_URL"

# Format content for Salesforce update and copy to clipboard
if [[ "$OSTYPE" == "darwin"* ]]; then
  # Extract the ##What section from PR_CONTENT
  WHAT_CONTENT=$(echo "$PR_CONTENT" | sed -n '/^## What/,/^## Why/p' | sed '$d' | tail -n +2)
  
  # Create the formatted Salesforce update text
  SALESFORCE_UPDATE="Site Builder Migration Notes:
$WHAT_CONTENT

Pull Request Link: $PR_URL"
  
  # Copy to clipboard
  echo -e "$SALESFORCE_UPDATE" | pbcopy
  echo "Salesforce update text copied to clipboard!"
  echo "======================================"
  echo "Salesforce Update Text:"
  echo "======================================"
  echo "$SALESFORCE_UPDATE"
  echo "======================================"
fi

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
