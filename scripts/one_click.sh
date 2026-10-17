#!/bin/sh
# Refresh this Mac from the live VPS. Does not print passwords or the address.
set -eu
cd "$(dirname "$0")/.."
python3 scripts/check_server.py
python3 scripts/render_clients.py
plist="$HOME/Library/LaunchAgents/com.21zhao.personal-proxy.adblock.plist"
mkdir -p "$HOME/Library/LaunchAgents"
cp scripts/com.21zhao.personal-proxy.adblock.plist "$plist"
uid=$(id -u)
launchctl bootout "gui/$uid/com.21zhao.personal-proxy.adblock" 2>/dev/null || true
launchctl bootstrap "gui/$uid" "$plist"
echo "ADBLOCK_SCHEDULE 86400"
