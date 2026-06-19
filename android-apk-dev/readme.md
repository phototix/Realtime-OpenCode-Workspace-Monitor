# Android APK — Realtime OpenCode Workspace Monitor

A native Android companion app for the **Realtime OpenCode Workspace Monitor** dashboard. Built with Kotlin and Jetpack Compose, it consumes the same HTTP API exposed by the Python dashboard server (`server.py`) running on your local machine or remote host.

---

## Overview

The web dashboard (`index.html` + `server.py`) exposes a set of JSON REST endpoints. This Android app is the mobile client for those endpoints, allowing you to monitor sessions, send instructions, manage Super Staff agents, and control cron jobs from an Android device.

---

## Prerequisites

| Tool | Required Version |
|---|---|
| Java | 17 |
| Android SDK Platform | 35 |
| Android Build Tools | 35.x |
| Gradle (wrapper) | 8.7 |
| Android Gradle Plugin | 8.5.2 |
| Kotlin | 2.0.21 |

Recommended tools: Android Studio, Android SDK Command-line Tools, Git.

---

## Environment Setup

### 1. Install Java 17

```bash
brew install openjdk@17
export JAVA_HOME="$(brew --prefix openjdk@17)/libexec/openjdk.jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"
java -version
```

### 2. Install Android SDK Components

```bash
sdkmanager "platforms;android-35" "build-tools;35.0.0" "platform-tools" "cmdline-tools;latest"
```

### 3. Create `local.properties`

Create `local.properties` in the Android project root (next to `build.gradle`):

```properties
sdk.dir=/Users/<your-user>/Library/Android/sdk
```

### 4. Make Gradle Wrapper Executable

```bash
chmod +x gradlew
```

---

## Build Configuration

```
Namespace / App ID : com.waha.apk
compileSdk         : 35
minSdk             : 26
targetSdk          : 35
JVM target         : 17
```

Version is read from `app-version.txt`:

```text
version:2026-06-14-BUILD-001
```

The numeric build suffix becomes `versionCode`; the full string after `version:` becomes `versionName`.

---

## Build Commands

```bash
./gradlew --version       # verify toolchain
./gradlew clean
./gradlew assembleDebug   # primary build target
```

Debug APK output:

```text
app/build/outputs/apk/debug/app-debug.apk
```

Additional commands:

```bash
./gradlew tasks
./gradlew dependencies
./gradlew assembleRelease
./gradlew installDebug
```

---

## API Integration

The Android app communicates with the dashboard server. Configure the base URL and any required credentials in `DataStore` or a local config file — never hardcode production values in source.

### Server Endpoints
Endpoint URL: https://mydora.brandon.my/

All endpoints accept `POST` with `Content-Type: application/json` unless noted.

#### Status & Health

| Endpoint | Method | Description |
|---|---|---|
| `GET /api/ping` | GET/POST | Health check. Returns `{ ok, daemon_alive, timestamp }` |
| `GET /api/status` | GET | Returns full dashboard status JSON from `status.json` |

#### Session Management

| Endpoint | Body Fields | Description |
|---|---|---|
| `POST /api/new-session` | `title`, `message`, `directory`, `model`, `mode` | Start a new OpenCode session |
| `POST /api/session-instruct` | `id`, `message`, `directory`, `model`, `mode`, `fork` | Send instruction to an existing session |
| `POST /api/session-answer` | `id`, `answers[]`, `directory` | Send tool-use answers to a waiting session |
| `POST /api/stop-session` | `id`, `directory` | Stop/delete a session |
| `POST /api/rename-session` | `id`, `title` | Rename a session |

#### Super Staff (AI Agents)

| Endpoint | Body Fields | Description |
|---|---|---|
| `POST /api/super-staff` | — | List all Super Staff agents |
| `POST /api/super-staff-create` | `name`, `description`, `gender`, `mode`, `model`, `path` | Create a new agent |
| `POST /api/super-staff-update` | `originalName`, `name`, `description`, `gender`, `mode`, `model`, `path` | Update an existing agent |
| `POST /api/super-staff-delete` | `name` | Delete an agent |
| `POST /api/super-staff-assign` | `sessionId`, `staffName` | Assign agent to a session |
| `POST /api/super-staff-assignments` | — | List current session–agent assignments |

#### Cron Jobs

| Endpoint | Body Fields | Description |
|---|---|---|
| `POST /api/cron-jobs` | — | List all cron jobs |
| `POST /api/cron-jobs/create` | `name`, `interval_sec`, `action` | Create a new cron job |
| `POST /api/cron-jobs/update` | `id`, fields | Update an existing cron job |
| `POST /api/cron-jobs/delete` | `id` | Delete a cron job |
| `POST /api/cron-jobs/toggle` | `id` | Enable/disable a cron job |
| `POST /api/cron-jobs/run` | `id` | Trigger a cron job immediately |

#### AI Providers & Models

| Endpoint | Body Fields | Description |
|---|---|---|
| `POST /api/providers` | — | List configured AI providers and Ollama connections |
| `POST /api/provider-login` | `url` | Initiate provider login |
| `POST /api/provider-logout` | `provider` | Log out from a provider |
| `POST /api/ollama-add` | `url` | Add an Ollama server URL |
| `POST /api/ollama-remove` | `url` | Remove an Ollama server URL |
| `POST /api/models` | — | List available AI models |

#### Settings & Profile

| Endpoint | Body Fields | Description |
|---|---|---|
| `POST /api/save-boss-name` | `name` | Save the display name shown in the UI |
| `POST /api/upload-photo` | `dataUrl` | Upload a profile photo (base64 data URL) |
| `POST /api/remove-photo` | — | Remove the profile photo |

#### Daemon Control

| Endpoint | Description |
|---|---|
| `POST /api/restart-daemon` | Restart the background poller daemon |
| `POST /api/kill-daemon` | Kill the daemon process |

### Response Format

All endpoints return JSON. Success:

```json
{ "ok": true, "message": "..." }
```

Failure:

```json
{ "ok": false, "message": "Human-readable error", "code": "engine_unreachable" }
```

Notable error codes: `engine_unreachable`, `engine_restarted`.

---

## Recommended Architecture

```
app/
  navigation/          # NavHost, bottom nav
  core/
    common/            # constants, API key config
    designsystem/      # theme, typography, colors
  data/
    remote/            # Retrofit interfaces, DTOs
    local/             # Room entities and DAOs
    repository/        # combines remote + local
  feature/
    dashboard/         # session list, status overview
    sessions/          # session detail, message bubbles
    staff/             # Super Staff CRUD
    cron/              # Cron job management
    providers/         # AI provider & Ollama settings
    settings/          # boss name, profile photo, daemon control
```

Each feature owns a `ViewModel` with an immutable UI state:

```kotlin
data class DashboardUiState(
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val sessions: List<SessionDto> = emptyList()
)
```

---

## Key Libraries

### Networking
- `com.squareup.retrofit2:retrofit:2.11.0`
- `com.squareup.retrofit2:converter-gson:2.11.0`
- `com.squareup.okhttp3:okhttp:4.12.0`
- `com.squareup.okhttp3:logging-interceptor:4.12.0`

### UI
- `androidx.compose:compose-bom:2024.09.00`
- `androidx.compose.material3:material3`
- `androidx.compose.material:material-icons-extended`
- `androidx.navigation:navigation-compose:2.8.2`
- `androidx.lifecycle:lifecycle-viewmodel-compose:2.8.6`

### Persistence
- `androidx.room:room-runtime:2.6.1` + `room-ktx` + KSP compiler
- `androidx.datastore:datastore-preferences:1.1.1`

### Background & Media
- `androidx.work:work-runtime-ktx:2.9.1`
- `io.coil-kt:coil-compose:2.7.0`
- `androidx.camera:camera-core:1.3.4` + `camera2`, `lifecycle`, `view`
- `com.google.mlkit:barcode-scanning:17.3.0`

---

## DataStore Keys

Lightweight persistent config recommended for:

| Key | Type | Description |
|---|---|---|
| `base_url` | String | Dashboard server base URL, e.g. `http://192.168.1.x:5500` |
| `api_key` | String | Optional auth header value |
| `boss_name` | String | Display name for the dashboard owner |

---

## Suggested Implementation Order

1. Gradle project setup with dependencies and `local.properties`.
2. App theme, navigation shell, bottom nav (Dashboard, Staff, Cron, Settings).
3. Retrofit client with configurable base URL from DataStore.
4. Dashboard screen — poll `/api/ping` and load status JSON.
5. Session list and session detail (instruct, answer, stop, rename).
6. Super Staff list, create, update, delete.
7. Cron job list, create, toggle, run.
8. Providers and Ollama management screen.
9. Settings screen (boss name, profile photo upload, daemon control).
10. WorkManager background sync for periodic status refresh.
11. Run `./gradlew assembleDebug` and validate all flows.

---

## Security Notes

- Store the base URL and API key in `DataStore` (encrypted if sensitive).
- Do not commit production credentials to source control.
- Use OkHttp `HttpLoggingInterceptor` in `DEBUG` builds only.
- For release APKs, inject secrets via CI/CD environment variables and `BuildConfig`.

---

## Build Validation Checklist

- [ ] `java -version` reports Java 17
- [ ] `local.properties` points to a valid Android SDK path
- [ ] Gradle sync completes without errors
- [ ] `./gradlew assembleDebug` exits with code 0
- [ ] APK exists at `app/build/outputs/apk/debug/app-debug.apk`
- [ ] App launches on emulator or physical device
- [ ] `/api/ping` call succeeds against the running dashboard server
- [ ] Session list loads and instruct flow works end-to-end

---

## Final Build Target

```bash
./gradlew assembleDebug
```

If this command fails on a clean machine with Java 17 and Android SDK 35 installed, the project is incomplete.
