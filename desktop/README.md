# Career OS Desktop (Layer 11)

Windows desktop shell built with **Tauri 2**. The desktop app is a thin client: it stores local preferences and auth tokens, shows native notifications, and calls the existing FastAPI backend over HTTP. No business logic is duplicated here.

## Prerequisites

1. **Backend running** — see `../backend` (`uvicorn` on `http://127.0.0.1:8000` by default)
2. **Node.js 20+**
3. **Rust toolchain** — required to build/run Tauri (`rustup`, MSVC build tools on Windows)
4. **WebView2** — preinstalled on Windows 11; install runtime on older Windows if needed

## Quick start

```bash
cd desktop
npm install
npm run icons
npm run tauri:dev
```

Production installer:

```bash
npm run tauri:build
```

Artifacts are written under `src-tauri/target/release/bundle/`.

## Features

| Feature | Implementation |
|---------|----------------|
| Desktop shell | Tauri window + React UI |
| Notifications | Polls `GET /api/v1/scheduler/notifications`, shows Windows toast via `tauri-plugin-notification` |
| Local settings | `tauri-plugin-store` — backend URL, email, notification/auto-start preferences |
| Auto-start | `tauri-plugin-autostart` — Windows startup registry |
| Tray icon | Rust tray menu — show, hide, quit; close button hides to tray |
| Local storage | Auth token + desktop settings only; backend owns resumes/applications |

## Local settings (desktop only)

Stored under the Tauri app data directory:

- `settings.json` — backend URL, notification poll interval, auto-start, launch minimized
- `auth.json` — bearer token after sign-in

Clear from the app: **Clear local data** (does not delete backend data).

## Backend contract

The shell calls existing API routes only:

- `GET /api/v1/health`
- `POST /api/v1/auth/login`
- `GET /api/v1/review/stats`
- `GET /api/v1/scheduler/notifications`
- `POST /api/v1/scheduler/notifications/{id}/read`
- `POST /api/v1/scheduler/run` (manual pipeline trigger)

## Tests

```bash
npm test
```

Vitest covers the API client, settings helpers, and notification polling logic without requiring Rust or the backend.

## Tray behavior

- Closing the window hides to tray (app keeps running for notification polling)
- Use tray **Quit** to exit fully
- `--minimized` launch flag hides the main window (used by auto-start)
