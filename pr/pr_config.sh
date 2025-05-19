#!/bin/bash
# PR Configuration Module
# Handles loading and saving defaults to ~/.pr-global-config

# Load config file
load_config() {
  if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
  fi
}

# Save config
save_config() {
  echo "# PR Global Config" > "$CONFIG_FILE"
  echo "DEFAULT_BRANCH=\"$DEFAULT_BRANCH\"" >> "$CONFIG_FILE"
  echo "DEFAULT_REVIEWERS=\"$REVIEWERS\"" >> "$CONFIG_FILE"
  echo "DEFAULT_LABELS=\"$LABELS\"" >> "$CONFIG_FILE"
  echo "DEFAULT_INSTRUCTIONS=\"$INSTRUCTIONS\"" >> "$CONFIG_FILE"
  echo "DEFAULT_DRAFT=$DEFAULT_DRAFT" >> "$CONFIG_FILE"
  echo -e "${GREEN}Configuration saved to $CONFIG_FILE${NC}"
}