# MyDora Dashboard

Real-time activity dashboard for MyDora agents, sessions, and system resources with a staff office metaphor.

![Dashboard Screenshot](screenshots.png)

## Features

### Active Nodes (Main View)
- **Content Tabs** — Sessions (case cards with state badges, cost, tokens, 💬 comment icon for logged-in users) / **Virtual Office** (Office Floor + Discussion Desk + Rest Room) / Others (standalone processes)
- **Brandon Card** — always visible boss card with CPU, memory, staff count, configurable name, and **Manage** button
- **💬 Comment Icon** — visible on session cards when logged in (hidden on thinking state; opens Continue modal for completed sessions)

### Sidebar
- **Overview** — Staffs/Workers, session count, CPU, memory, active tasks, load, total cost used overall
- **System Resources** — CPU usage, System Memory (renamed), disk free, uptime (human-readable format, row hidden when N/A)
- **Session List** — active sessions with quick preview
- **Activity Log** — transient commands, session cleanup, worker lifecycle
- **Admin Panel** — 🔑 login button

### Admin Panel
Click the **Admin Panel** button in the sidebar or **Manage** on the Brandon card. Full-screen modal with 6 tabs:

| Tab | Contents |
|---|---|
| **Sessions** | Sessions grouped by workspace, search/filter, View (metadata modal), Continue (full last prompt + full last response with mode badge + new instruction with model/mode dropdowns), **+ New Case** button (start a new session with title, instructions, mode, model, workspace) |
| **System** | Daemon status, restart/kill controls |
| **Users** | Manage dashboard users (admin role only) |
| **Settings** | Poll interval, session retention, max log lines, **Boss Name** (configurable) |
| **Security** | Change password |
| **Logs** | Full activity log viewer with search |

### Notifications
- Browser notifications for case updates: new case, case completed, state change (thinking → complete, etc.)

## Usage

```bash
bash start.sh
# Opens http://localhost:5500
```

### Default Credentials

- **Email:** `brandon@kkbuddy.com`
- **Password:** `#Quidents64#`

## How It Works

- **Poller** (`poller.py`) collects `ps aux` data, queries `opencode session list --format json`, enriches sessions via `opencode export` (full last_text and last_user_prompt), and gathers available models (opencode + Ollama) every 2 seconds
- **Unified Server** (`server.py`) serves static files and a JSON admin API (start/stop/continue session, restart/kill daemon, ping) on a single port — no cross-origin issues
- **Daemon** (`daemon.sh`) loops the poller indefinitely
- **Frontend** reads `data/status.json` and renders the dashboard with 2-second auto-refresh
- **Auth** uses SHA-256 hashed passwords in localStorage; login state persists in sessionStorage

## Architecture

```
daemon.sh ──→ poller.py ──→ data/status.json ──→ index.html (public)
                                                    ↑
server.py (port 5500) ── serves static files ───────┘
                    ── /api/* endpoints ──→ admin panel actions
```

## Key Implementation Details

- **Send button** closes modal immediately and shows "Sending..." on the card badge and admin table button, reverting on error
- **Toast notifications** stay visible until manually dismissed (close button)
- **Continue modal** calls `opencode run -s <id> --attach <server_url>` (no --fork) to continue sessions without creating duplicates
- **Model dropdown** includes opencode models (deepseek, openai, opencode) and Ollama models from `ollama.brandon.my`
- **Workspace dropdown** populated from unique directories across all sessions

## Data

The dashboard auto-refreshes every 2 seconds. No database required. All state is kept in `~/.opencode-dashboard/data/`.

## License

MIT
