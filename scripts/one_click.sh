#!/bin/sh
# Refresh this Mac from the live VPS. Does not print passwords or the address.
set -eu
cd "$(dirname "$0")/.."
python3 scripts/check_server.py
python3 scripts/render_clients.py
