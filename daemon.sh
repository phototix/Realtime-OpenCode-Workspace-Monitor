#!/bin/bash
DATA_DIR="$HOME/.opencode-dashboard/data"
STATUS_FILE="$DATA_DIR/status.json"
ACTIVITY_FILE="$DATA_DIR/activity.log"
PID_FILE="$DATA_DIR/daemon.pid"

mkdir -p "$DATA_DIR"
echo $$ > "$PID_FILE"
touch "$ACTIVITY_FILE"

log_activity() {
  echo "[$(date '+%H:%M:%S')] $1" >> "$ACTIVITY_FILE"
  tail -100 "$ACTIVITY_FILE" > "$ACTIVITY_FILE.tmp" && mv "$ACTIVITY_FILE.tmp" "$ACTIVITY_FILE"
}

log_activity "Dashboard daemon started"

SCRIPT_DIR="$HOME/.opencode-dashboard"

while true; do
  python3 "$SCRIPT_DIR/poller.py"
  sleep 2
done
