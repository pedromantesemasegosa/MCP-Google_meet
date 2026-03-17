#!/bin/bash
# scripts/install_launchd.sh
# Installs the daily sync job via macOS launchd.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PLIST_SRC="$SCRIPT_DIR/com.mcp-meet.sync.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.mcp-meet.sync.plist"
PYTHON_PATH="$(which python3)"

echo "MCP Meet Notes — launchd installer"
echo "===================================="
echo "Project dir: $PROJECT_DIR"
echo "Python path: $PYTHON_PATH"
echo ""

# Unload existing job if present
if launchctl list | grep -q "com.mcp-meet.sync"; then
    echo "Unloading existing job..."
    launchctl unload "$PLIST_DST" 2>/dev/null || true
fi

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Generate plist with actual paths
sed -e "s|__PYTHON_PATH__|$PYTHON_PATH|g" \
    -e "s|__PROJECT_DIR__|$PROJECT_DIR|g" \
    "$PLIST_SRC" > "$PLIST_DST"

# Load the job
launchctl load "$PLIST_DST"

echo ""
echo "Installed! Sync will run daily at 9:00 AM."
echo "To run manually: launchctl start com.mcp-meet.sync"
echo "To uninstall:    launchctl unload $PLIST_DST && rm $PLIST_DST"
