#!/bin/bash
echo "Starting OpenCode Activity Dashboard..."

# Kill old instances
kill $(lsof -t -i:5500) 2>/dev/null
pkill -f "opencode-dashboard-daemon" 2>/dev/null
pkill -f "admin_api.py" 2>/dev/null
sleep 0.5

# Start daemon (poller loop)
nohup bash "$HOME/.opencode-dashboard/daemon.sh" > /dev/null 2>&1 &
echo "Daemon started (PID: $!)"

sleep 1

# Start unified server (static files + admin API)
cd "$HOME/.opencode-dashboard"
python3 server.py 5500 &
SERVER_PID=$!
echo "Dashboard server running on http://localhost:5500 (PID: $SERVER_PID)"

echo ""
echo "Dashboard: http://localhost:5500"
echo "Press Ctrl+C to stop"

trap "echo 'Stopping...'; kill $SERVER_PID 2>/dev/null; pkill -f 'opencode-dashboard-daemon' 2>/dev/null; pkill -f 'admin_api.py' 2>/dev/null; exit 0" INT TERM

wait $SERVER_PID
