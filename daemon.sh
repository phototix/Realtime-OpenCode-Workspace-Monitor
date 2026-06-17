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

# Start admin API on port 5001 if not already running
ADMIN_PORT=5001
if ! lsof -i:$ADMIN_PORT >/dev/null 2>&1; then
  python3 "$SCRIPT_DIR/admin_api.py" "$ADMIN_PORT" &
  ADMIN_PID=$!
  log_activity "Admin API started on port $ADMIN_PORT (PID: $ADMIN_PID)"
else
  ADMIN_PID=""
fi

while true; do
  python3 "$SCRIPT_DIR/poller.py"
  sleep 2
done
