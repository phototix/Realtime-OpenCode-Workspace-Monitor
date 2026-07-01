#!/bin/bash
set -euo pipefail

echo "Starting OpenCode Activity Dashboard..."
nohup bash "$HOME/.opencode-dashboard/daemon.sh" >/dev/null 2>&1 &
exec python3 "$HOME/.opencode-dashboard/server.py" 5500
