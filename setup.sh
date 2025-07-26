#!/bin/bash
# Main setup script - delegates to scripts/setup.sh
# This ensures backward compatibility for users expecting setup.sh in root

echo "🔄 Delegating to scripts/setup.sh for cleaner project organization..."
exec "$(dirname "$0")/scripts/setup.sh" "$@"