#!/bin/bash
# Site Builder Migration script wrapper

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Function to check if a command exists
command_exists() {
  command -v "$1" &> /dev/null
}

# Check if Python 3 is installed
if ! command_exists python3; then
  echo "Error: Python 3 is required but not installed."
  exit 1
fi

# Check for required Python modules
python3 -c "import subprocess, argparse, re, datetime, os, sys" 2>/dev/null
if [ $? -ne 0 ]; then
  echo "Error: One or more required Python modules are missing."
  echo "Required modules: subprocess, argparse, re, datetime, os, sys"
  exit 1
fi

# Check if DI_WEBSITES_PLATFORM_DIR is set or use --platform-dir flag
PLATFORM_DIR_ARG=""
if [ -z "$DI_WEBSITES_PLATFORM_DIR" ]; then
  # Try to set a default if not set
  if [ -d ~/di-websites-platform ]; then
    export DI_WEBSITES_PLATFORM_DIR=~/di-websites-platform
    echo "Set DI_WEBSITES_PLATFORM_DIR to ~/di-websites-platform"
  else
    # Check if --platform-dir is provided in arguments
    PLATFORM_DIR=""
    for arg in "$@"; do
      if [[ $arg == --platform-dir=* ]]; then
        PLATFORM_DIR="${arg#*=}"
        break
      elif [[ $PREV_ARG == "--platform-dir" ]]; then
        PLATFORM_DIR="$arg"
        break
      fi
      PREV_ARG="$arg"
    done
    
    if [ -z "$PLATFORM_DIR" ]; then
      echo "WARNING: DI_WEBSITES_PLATFORM_DIR environment variable is not set."
      echo "Please set it to the path of your DI Websites Platform directory."
      echo "Example: export DI_WEBSITES_PLATFORM_DIR=/path/to/di-websites-platform"
      echo "Alternatively, use the --platform-dir flag:"
      echo "Example: $0 --platform-dir=/path/to/di-websites-platform slug1 slug2"
    fi
  fi
fi

# Execute the Python script
python3 "$SCRIPT_DIR/site_builder_migration.py" "$@" 
