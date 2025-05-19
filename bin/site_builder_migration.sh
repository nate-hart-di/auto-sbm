#!/bin/bash
# Simple wrapper for site_builder_migration.py
# For compatibility with existing usage

# Set up environment
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PARENT_DIR="$( dirname "$SCRIPT_DIR" )"
export PYTHONPATH="$PARENT_DIR:$PYTHONPATH"

# Forward all arguments to the Python module
cd "$PARENT_DIR"
python3 -m sbm.cli "$@" 
