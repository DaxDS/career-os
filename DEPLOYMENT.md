# Career OS V1 — Deployment Guide

---

## Requirements

| Component | Version |
|-----------|---------|
| Python | 3.12+ |
| PostgreSQL | 16 |
| Node.js | 20+ (desktop only) |
| Rust | Latest stable (desktop build only) |
| Docker | Recommended for production |

---

## Development (Docker Compose)

```bash
cd career-os
docker compose up -d
```

Starts PostgreSQL (`5432`) and API (`8000`) with hot-reload for development.

Verify:

```bash
career-os health
# or
curl http://127.0.0.1:8000/api/v1/health
```

---

## Production (Docker Compose)

### 1. Configure secrets

```bash
cp .env.example .env
```

Edit `.env`:

```bash
ENVIRONMENT=production
POSTGRES_PASSWORD=<strong-password>
SECRET_KEY=<openssl rand -hex 32>
DEFAULT_USER_PASSWORD=<strong-password>
CORS_ORIGINS=http://localhost:1420,https://your-domain.example
AI_ENABLED=true
OPENAI_API_KEY=sk-...
```

### 2. Deploy

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Production differences from dev compose:
- Immutable API image (`Dockerfile.prod`, no dev dependencies)
- No backend source bind mount
- `ENVIRONMENT=production` with startup validation
- JSON structured logging enabled
- Persistent `storage_data` and `postgres_data` volumes

### 3. Verify

```bash
career-os health --url http://127.0.0.1:8000
career-os migrate-check
```

---

## Manual Installation

```bash
cd backend
pip install -e .
cp ../.env.example .env   # edit values
career-os migrate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Career OS CLI

Installed via `pip install -e ./backend`:

| Command | Description |
|---------|-------------|
| `career-os version` | Print version and environment |
| `career-os migrate` | Run `alembic upgrade head` |
| `career-os migrate-check` | Verify migration head `014_layer10_scheduler` |
| `career-os health --url URL` | Check `/health` and `/ready` |
| `career-os backup --output backups` | Dump PostgreSQL + archive storage/prompts |
| `career-os restore --input file.tar.gz --yes` | Restore from backup |

**Backup requirements:** `pg_dump` and `psql` on PATH for PostgreSQL URLs.

---

## Desktop (Windows)

```bash
cd desktop
npm ci
npm run icons
npm run tauri:build
```

Installer: `desktop/src-tauri/target/release/bundle/`

The desktop expects the backend at the URL configured in app settings (default `http://127.0.0.1:8000`).

---

## Playwright (Browser Automation)

```bash
playwright install chromium
```

Set `BROWSER_STOP_BEFORE_SUBMIT=true` in production until automation is validated.

---

## Health Checks

| Endpoint | Use |
|----------|-----|
| `GET /api/v1/health` | Liveness |
| `GET /api/v1/ready` | Database readiness |
| `GET /api/v1/foundation/status` | Storage and prompts |

---

## Security Checklist

- [ ] `ENVIRONMENT=production`
- [ ] `SECRET_KEY` — 32+ random characters, not default
- [ ] `DEFAULT_USER_PASSWORD` changed from dev default
- [ ] `POSTGRES_PASSWORD` strong and unique
- [ ] `CORS_ORIGINS` limited to trusted clients
- [ ] API behind HTTPS reverse proxy if network-exposed
- [ ] AI keys in environment only, never committed
- [ ] Regular backups scheduled (`career-os backup`)

---

## Backup & Restore

**Backup:**

```bash
career-os backup --output backups
```

Creates `backups/career-os-backup-<timestamp>.tar.gz` containing:
- `database.sql` (PostgreSQL dump)
- `storage/` directory
- `prompts/` directory
- `manifest.json`

**Restore:**

```bash
career-os restore --input backups/career-os-backup-20260101T120000Z.tar.gz --yes
```

Stop the API before restoring. Restart after restore completes.

---

## CI/CD

GitHub Actions workflow (`.github/workflows/ci.yml`):
- Backend: ruff, migration check, pytest
- Desktop: npm test, vite build
- Docker: production image build

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Production startup fails on secrets | Check `ENVIRONMENT=production` validation messages |
| Migration fails | `career-os migrate-check`; verify `DATABASE_URL` |
| Desktop CORS errors | Add origin to `CORS_ORIGINS` |
| Scheduler not running | `SCHEDULER_ENABLED=true`; check logs |
| Backup fails | Install PostgreSQL client tools (`pg_dump`) |
