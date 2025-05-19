#!/bin/bash
# PR Content Module
# Builds PR description and handles interactive input

# Generate default title
generate_default_title() {
  if [ -z "$TITLE" ]; then
    if [ "$PR_TYPE" = "production" ] && [ -n "$SLUG" ]; then
      TITLE="[$SLUG] - New Site"
    else
      TITLE="$CURRENT_BRANCH"
    fi
    echo -e "${YELLOW}No title provided. Using: \"$TITLE\"${NC}"
  fi
}

# Interactive input
get_interactive_input() {
  local prompt="$1"
  local var_name="$2"
  local default_value="$3"
  local content=""
  local line
  echo -e "${BLUE}${prompt} (Enter for default, Ctrl+C to skip):${NC}"
  if [ -n "$default_value" ]; then
    echo "Default:"
    echo "$default_value"
  fi
  echo "---------------------------------------"
  read -r line
  if [ -z "$line" ]; then
    eval "$var_name=\"\$default_value\""
  else
    content="$line"
    eval "$var_name=\"\$content\""
  fi
}

# Build PR content
build_pr_content() {
  if [ "$PR_TYPE" = "production" ] && [ -n "$SLUG" ]; then
    WHAT="Deploying $SLUG to Production"
    WHY="New Site"
    INSTRUCTIONS="[staging link]"
  else
    WHAT=""
    WHY=""
    INSTRUCTIONS="Review the changes in the Files Changed tab."
  fi

  generate_default_title
  REVIEWERS=${REVIEWERS:-$DEFAULT_REVIEWERS}
  LABELS=${LABELS:-$DEFAULT_LABELS}
  INSTRUCTIONS=${INSTRUCTIONS:-$DEFAULT_INSTRUCTIONS}

  if [ -z "$WHAT" ]; then
    local default_what="No changes specified"
    if [ "$SBM_MODE" = true ]; then
      default_what="Transferred vrp styles to sb-vrp.scss\nTransferred vdp styles to sb-vdp.scss\nAdded interior page styles to sb-inside.scss"
    fi
    get_interactive_input "Enter changes made" WHAT "$default_what"
  fi
  WHAT=${WHAT:-"No changes specified"}

  if [ -z "$WHY" ]; then
    get_interactive_input "Enter reason for changes" WHY "No reason specified"
  fi
  WHY=${WHY:-"No reason specified"}

  PR_CONTENT="## What
$WHAT
## Why
$WHY
## Steps to Validate/Verify
$INSTRUCTIONS
## Branch Info
- Branch: \`$CURRENT_BRANCH\`
- Repository: $REPO_NAME"
}
