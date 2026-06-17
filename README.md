# MyDora Dashboard

Real-time activity dashboard for MyDora agents, sessions, and system resources with a staff office metaphor.

![Dashboard Screenshot](screenshots.png)

## Features

- **Office Floor** — 6 numbered desks showing active worker processes with CPU/memory stats
- **Sessions** — real-time task cards with state (thinking/running-tools/complete/error), cost, tokens, and agent details
- **Discussion Desk** — virtual staff collaborating on thinking/running-tools sessions
- **Rest Room** — 12 activity spots with dynamic state cycling for idle staff
- **Activity Log** — track transient commands, session cleanup events, and worker lifecycle
- **System Stats** — CPU, memory, disk usage, uptime, and total cost sidebar
- **Admin Panel** — full-screen modal with 6 tabs:
  - **Sessions** — sessions grouped by workspace, search/filter, View (metadata), Continue (last prompt + response + new instruction with model & mode dropdown)
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

Click the **Admin Panel** button in the sidebar or the **Manage** button on the Brandon card to sign in.

### Default Credentials

- **Email:** `brandon@kkbuddy.com`
- **Password:** `#Quidents64#`

## How It Works

- **Poller** (`poller.py`) collects `ps aux` data, queries `opencode session list --format json`, and enriches sessions via `opencode export` every 2 seconds
- **Unified Server** (`server.py`) serves static files and a JSON admin API (stop session, continue session, restart/kill daemon, ping) on a single port
- **Daemon** (`daemon.sh`) loops the poller indefinitely
- **Frontend** reads `data/status.json` and renders the dashboard with auto-refresh
- **Auth** uses SHA-256 hashed passwords in localStorage; login state persists in sessionStorage

## Architecture

```
daemon.sh ──→ poller.py ──→ data/status.json ──→ index.html (public)
                                                  ↑
server.py (port 5500) ── serves static files ─────┘
                    ── /api/* endpoints ──→ admin panel actions
```

## Data

The dashboard auto-refreshes every 2 seconds. No database required. All state is kept in `~/.opencode-dashboard/data/`.

## License

MIT
