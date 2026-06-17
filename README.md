# Realtime OpenCode Workspace Monitor

Real-time activity dashboard for OpenCode agents, sessions, and system resources with a staff office metaphor.

![Dashboard Screenshot](screenshots.png)

## Features

- **Office Floor** — 6 numbered desks showing active worker processes with CPU/memory stats
- **Sessions** — real-time task cards with state (thinking/running-tools/complete/error), cost, tokens, and agent details
- **Discussion Desk** — virtual staff collaborating on thinking/running-tools sessions
- **Rest Room** — 12 activity spots with dynamic state cycling for idle staff
- **Activity Log** — track transient commands, session cleanup events, and worker lifecycle
- **System Stats** — CPU, memory, disk usage, uptime, and total cost sidebar
- **Admin Panel** — 🔑 full-screen modal with 6 tabs:
  - **Sessions** — searchable table, stop sessions via OpenCode CLI
  - **System** — daemon status, restart/kill controls
  - **Users** — manage dashboard users (admin role only)
  - **Settings** — poll interval, session retention, max log entries
  - **Security** — change password
  - **Logs** — full activity log viewer with search

## Usage

```bash
bash start.sh
# Opens http://localhost:5500
```

Click the 🔑 **Admin Panel** button in the sidebar to sign in.

### Default Credentials

- **Email:** `brandon@kkbuddy.com`
- **Password:** `#Quidents64#`

## How It Works

- **Poller** (`poller.py`) collects `ps aux` data, queries `opencode session list --format json`, and enriches sessions via `opencode export` every 2 seconds
- **Admin API** (`admin_api.py`) runs on port 5001 for privileged actions (stop session, restart daemon)
- **Daemon** (`daemon.sh`) loops the poller and launches the admin API
- **Frontend** reads `data/status.json` and renders the dashboard with auto-refresh
- **Auth** uses SHA-256 hashed passwords in localStorage; login state persists in sessionStorage

## Architecture

```
daemon.sh ──┬── poller.py ──→ data/status.json ──→ index.html (public)
            └── admin_api.py (port 5001) ←── index.html (admin actions)
```

## Data

The dashboard auto-refreshes every 2 seconds. No database required. All state is kept in `~/.opencode-dashboard/data/`.

## License

MIT
