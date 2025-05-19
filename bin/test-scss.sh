#!/bin/bash
# SCSS Syntax Validator
# A simple utility to test SCSS files for syntax errors
# Uses the validator function from sbm.scss.validator

# Import path setup
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PARENT_DIR="$( dirname "$SCRIPT_DIR" )"

# Check if a file was provided
if [ -z "$1" ]; then
  echo "Usage: $0 <scss-file> [scss-file2 scss-file3 ...]"
  echo "Example: $0 dealer-themes/somedealer/sb-inside.scss"
  exit 1
fi

# Process each file provided as an argument
for file in "$@"; do
  if [ ! -f "$file" ]; then
    echo "Error: File $file not found"
    continue
  fi
  
  echo "Testing syntax for: $file"
  
  # Use the Python module to validate the SCSS syntax
  cd "$PARENT_DIR"
  python3 -c "from sbm.scss.validator import validate_scss_syntax; validate_scss_syntax('$file')"
  
  echo "----------------------------------------"
done

echo "Syntax testing complete." 
