#!/bin/bash
# PR Utilities Module
# Handles clipboard and browser operations

# Copy to clipboard or file
copy_to_clipboard() {
  local content="$1"
  local output_file="${2:-pr_description.txt}"
  if [[ "$OSTYPE" == "darwin"* ]] && command -v pbcopy >/dev/null; then
    echo -e "$content" | pbcopy
    echo -e "${GREEN}Copied to clipboard${NC}"
    return 0
  elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if command -v xclip >/dev/null; then
      echo -e "$content" | xclip -selection clipboard
      echo -e "${GREEN}Copied to clipboard${NC}"
      return 0
    elif command -v wl-copy >/dev/null; then
      echo -e "$content" | wl-copy
      echo -e "${GREEN}Copied to clipboard${NC}"
      return 0
    fi
  elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    if command -v clip.exe >/dev/null; then
      echo -e "$content" | clip.exe
      echo -e "${GREEN}Copied to clipboard${NC}"
      return 0
    fi
  fi
  echo -e "$content" > "$output_file"
  return 1
}

# Open URL in browser
open_in_browser() {
  local url="$1"
  if [[ "$OSTYPE" == "darwin"* ]]; then
    open "$url"
  elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open "$url" >/dev/null 2>&1
  elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    start "$url"
  else
    echo "Please visit: $url"
  fi
}