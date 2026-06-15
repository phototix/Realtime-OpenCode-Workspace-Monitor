#!/bin/bash
echo "Starting OpenCode Activity Dashboard..."

# Kill old instances
kill $(lsof -t -i:5000) 2>/dev/null
pkill -f "opencode-dashboard-daemon" 2>/dev/null
sleep 0.5

# Start daemon
nohup bash "$HOME/.opencode-dashboard/daemon.sh" > /dev/null 2>&1 &
echo "Daemon started (PID: $!)"

# Generate initial status
sleep 1

# Start HTTP server
cd "$HOME/.opencode-dashboard"
python3 -m http.server 5000 &
SERVER_PID=$!
echo "HTTP server running on http://localhost:5000 (PID: $SERVER_PID)"

echo ""
echo "Dashboard: http://localhost:5000"
echo "Press Ctrl+C to stop"

trap "echo 'Stopping...'; kill $SERVER_PID 2>/dev/null; pkill -f 'opencode-dashboard-daemon' 2>/dev/null; exit 0" INT TERM

wait $SERVER_PID
