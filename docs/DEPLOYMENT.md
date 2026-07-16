# Career OS V1 — Deployment Guide

---

## Requirements

| Component | Version |
|-----------|---------|
| Python | 3.12+ |
| PostgreSQL | 16 |
| Node.js | 20+ (desktop only) |
| Rust | Latest stable (desktop build only) |
| Docker | Optional (recommended for backend) |

---

## Quick Start (Docker)

```bash
cd career-os
docker compose up -d
```

This starts:
- **PostgreSQL** on port `5432`
- **API** on port `8000` (runs migrations automatically)

Verify:
```bash
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:8000/api/v1/ready
```

---

## Manual Backend Setup

### 1. Database

```bash
createdb careeros
# or use PostgreSQL Docker:
docker run -d --name careeros-db \
  -e POSTGRES_USER=careeros \
  -e POSTGRES_PASSWORD=careeros \
  -e POSTGRES_DB=careeros \
  -p 5432:5432 postgres:16-alpine
```

### 2. Environment

Create `career-os/backend/.env`:

```bash
DATABASE_URL=postgresql://careeros:careeros@localhost:5432/careeros
SECRET_KEY=<generate-with-openssl-rand-hex-32>
AI_ENABLED=true
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
SCHEDULER_ENABLED=true
SCHEDULER_HOUR=7
SCHEDULER_MINUTE=0
SCHEDULER_TIMEZONE=America/Toronto
BROWSER_HEADLESS=true
BROWSER_STOP_BEFORE_SUBMIT=true
AUTOMATION_ENABLED=true
LOG_LEVEL=INFO
```

**Production:** Change `SECRET_KEY`, `default_user_password`, and database credentials.

### 3. Install & Migrate

```bash
cd career-os/backend
pip install -e ".[dev]"
alembic upgrade head
```

### 4. Run API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Bootstrap User

On first start, single-user mode auto-creates:
- Email: `user@careeros.local` (configurable via `DEFAULT_USER_EMAIL`)
- Password: `careeros-dev-password` (configurable via `DEFAULT_USER_PASSWORD`)

Or register via API if single-user mode is disabled.

---

## Playwright (Browser Automation)

```bash
playwright install chromium
```

Required only if using Layer 9 automation.

---

## Desktop App (Windows)

### Development

```bash
# Terminal 1: backend running on :8000

# Terminal 2: desktop
cd career-os/desktop
npm install
npm run icons
npm run tauri:dev
```

### Production Build

```bash
cd career-os/desktop
npm run tauri:build
```

Installer output: `desktop/src-tauri/target/release/bundle/`

### Desktop Configuration

In the app settings panel:
- **Backend URL:** `http://127.0.0.1:8000`
- **Email / Password:** match backend user
- **Auto-start:** optional Windows startup
- **Notifications:** poll interval for pipeline alerts

---

## Storage Layout

```
career-os/
  storage/
    resumes/           # Uploaded master resumes
    applications/      # Generated per-job artifacts
    browser_profiles/  # Playwright sessions
    browser_screenshots/
  prompts/             # AI prompt files (synced to DB)
```

Ensure write permissions for the API process.

---

## Health Checks

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/health` | Process alive |
| `GET /api/v1/ready` | Database connected |
| `GET /api/v1/foundation/status` | Storage + prompts wired |

---

## Scheduler

Morning pipeline runs automatically when `SCHEDULER_ENABLED=true`.

Manual trigger:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/scheduler/run \
  -H "Authorization: Bearer <token>"
```

---

## Security Checklist

- [ ] Change `SECRET_KEY` from default
- [ ] Change default user password
- [ ] Restrict API to localhost or VPN if single-user
- [ ] Set `AI_ENABLED=false` if not using LLM features
- [ ] Review CORS origins in `main.py` for your deployment
- [ ] Use HTTPS reverse proxy for remote access
- [ ] Back up PostgreSQL and `storage/` regularly

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Migration fails | Check `DATABASE_URL`; run `alembic current` |
| AI endpoints return 503 | Set `AI_ENABLED=true` and API keys |
| Automation fails | Run `playwright install chromium`; check `AUTOMATION_ENABLED` |
| Desktop can't connect | Verify backend URL; check CORS includes `localhost:1420` |
| Scheduler not running | Check `SCHEDULER_ENABLED`; see logs for `scheduler_started` |
| No jobs from pipeline | Populate `scheduled_search_jobs` in source config |

---

## Backup

```bash
pg_dump -U careeros careeros > backup.sql
tar -czf storage-backup.tar.gz storage/
```
