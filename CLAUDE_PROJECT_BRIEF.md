# Career OS — Complete Project Brief for Claude

**Purpose:** Single document to give Claude (or any AI) full context on Career OS V1.  
**Version:** 1.0.0  
**Layer:** 11-desktop  
**Migration head:** `014_layer10_scheduler`  
**Last updated:** June 2026  
**Workspace path:** `s:\cursor\AI - Job application\career-os`

---

## 1. Executive summary

Career OS is a **personal AI career operating system** for a single Canadian job seeker, built as a **monetizable B2C SaaS**. It automates job discovery, scoring, document generation, and application preparation — with **human-in-the-loop review** before anything is submitted.

**Primary user interface:** React web app at `web/` served at `http://localhost:8000/` (production) or `http://localhost:3000/` (dev).

**Not the user UI:** Swagger at `/docs` (developer only).

**Target market:** Active job seekers in Canada (AI/ML, IT, software); future Career Coach tier for agencies.

**Owner context:** Built for Daksh Patel — AI engineer profile, resume uploaded as "AI Resume".

---

## 2. Architecture overview

```
┌─────────────────────────────────────────────────────────────────┐
│  web/ (React + Vite)          desktop/ (Tauri 2, optional)      │
│  Landing, Login, Dashboard,   Notifications, system tray      │
│  Resumes, Jobs, Review,       Thin client only                │
│  Pipeline, Pricing                                            │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP /api/v1/*
┌────────────────────────────▼────────────────────────────────────┐
│  backend/ (FastAPI + Python 3.12+)                            │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐  │
│  │ API routes  │  │ Application  │  │ Infrastructure      │  │
│  │ (REST)      │→ │ services     │→ │ DB, AI, browser,    │  │
│  └─────────────┘  └──────────────┘  │ job search, storage │  │
│                                      └─────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  PostgreSQL 16  │  Local storage (resumes, docs)  │  OpenAI +   │
│                 │  prompts/ (YAML templates)       │  Anthropic  │
└─────────────────────────────────────────────────────────────────┘
```

**Design pattern:** Hexagonal / ports-and-adapters. Business logic in `application/services/`. Infrastructure in `infrastructure/`. API thin layer in `api/routes/`.

**Composition root:** `backend/app/dependencies.py` (FastAPI DI).

---

## 3. Layer model (Layers 0–11)

| Layer | Name | Key components |
|-------|------|----------------|
| 0 | Foundation | Users, audit log, prompt registry, system metadata |
| 1 | User profile | Immigration prefs, skills, salary, provinces |
| 2 | Resumes | 5 master resume labels, PDF/DOCX upload, parsing |
| 3 | Jobs | Sources, import, dedup, classification |
| 4 | AI infrastructure | Model router, capabilities.yaml, OpenAI + Anthropic |
| 5 | Intelligence | Immigration scoring, ATS, job scoring, resume selection |
| 6 | Documents | Tailored resume, cover letter, recruiter email |
| 7 | Tracking | Application status, approve, submit, screenshots |
| 8 | Review queue | Approve / reject / request revision |
| 9 | Browser automation | Playwright apply-page automation, CAPTCHA pause |
| 10 | Scheduler | Morning pipeline (APScheduler), notifications |
| 11 | Desktop + Web | Tauri shell + product web app |

---

## 4. Repository structure

```
career-os/
├── web/                    # PRODUCT UI (primary)
│   ├── src/pages/          # Landing, Login, Dashboard, Resumes, Jobs, Review, Pipeline, Pricing
│   ├── src/api/client.ts   # API client
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI app, CORS, serves web/dist
│   │   ├── config.py       # Settings from .env
│   │   ├── cli.py          # career-os CLI (doctor, migrate, backup, upload-resume)
│   │   ├── dependencies.py # DI wiring
│   │   ├── api/routes/     # REST endpoints
│   │   ├── api/schemas/    # Pydantic request/response models
│   │   ├── application/    # services + ports
│   │   ├── domain/         # enums, presets, constants
│   │   └── infrastructure/ # DB, AI, browser, job search, prompts
│   ├── alembic/versions/   # 001–014 migrations
│   ├── tests/              # unit + integration (172+ tests)
│   ├── Dockerfile.prod
│   └── pyproject.toml
├── desktop/                # Tauri 2 Windows shell (optional)
├── prompts/                # AI prompt template files
├── storage/                # User files (resumes, applications) — gitignored
├── inbox/                  # Drop zone for resume upload via CLI
├── docs/                   # Internal audit docs
├── .github/workflows/ci.yml
├── docker-compose.yml      # Dev
├── docker-compose.prod.yml # Production
├── PRODUCT.md              # Monetization & GTM
├── CLAUDE_PROJECT_BRIEF.md # This file
└── README.md
```

---

## 5. Tech stack

| Component | Technology |
|-----------|------------|
| Backend API | FastAPI, Uvicorn, Pydantic v2 |
| Database | PostgreSQL 16, SQLAlchemy 2, Alembic |
| AI | OpenAI (gpt-4o, gpt-4o-mini), Anthropic (claude-sonnet-4-20250514) |
| AI routing | `capabilities.yaml` + `ModelRouter` |
| Job search | Live HTTP scrape: Job Bank Canada, Indeed Canada |
| Browser automation | Playwright (apply forms only, Layer 9) |
| Scheduler | APScheduler (default 7:00 America/Toronto) |
| Product UI | React 19, React Router 7, Vite 6 |
| Desktop | Tauri 2, React (thin client) |
| CI | GitHub Actions: ruff, pytest, desktop build, web build, Docker |
| Auth | JWT bearer tokens, bcrypt passwords |

---

## 6. Environment variables

**Files:** `backend/.env` and/or `career-os/.env` (backend overrides root).

| Variable | Purpose |
|----------|---------|
| `ENVIRONMENT` | development / production |
| `SECRET_KEY` | JWT signing (required strong in production) |
| `DATABASE_URL` | PostgreSQL connection |
| `DEFAULT_USER_EMAIL` | `user@example.com` (must be valid email for API) |
| `DEFAULT_USER_PASSWORD` | Bootstrap user password |
| `AI_ENABLED` | true/false |
| `OPENAI_API_KEY` | OpenAI API |
| `ANTHROPIC_API_KEY` | Anthropic API |
| `SCHEDULER_ENABLED` | Morning cron on/off |
| `SCHEDULER_HOUR`, `SCHEDULER_MINUTE`, `SCHEDULER_TIMEZONE` | Cron schedule |
| `STORAGE_PATH`, `PROMPTS_PATH` | File paths |
| `CORS_ORIGINS` | Comma-separated origins |
| `AUTOMATION_ENABLED`, `BROWSER_HEADLESS` | Playwright settings |

**Never commit:** `.env`, API keys, `storage/`, backups.

---

## 7. Default login (development)

- **Email:** `user@example.com`
- **Password:** `careeros-dev-password`

Note: `user@careeros.local` was replaced — `.local` TLD fails Pydantic EmailStr validation.

---

## 8. Complete API reference (`/api/v1`)

### Health
- `GET /health` — liveness
- `GET /ready` — DB connected

### Auth
- `POST /auth/register` — blocked in single-user mode if user exists
- `POST /auth/login` → `{ access_token, token_type }`
- `GET /auth/me` — current user (auth required)

### Profile
- `GET /profile`, `PATCH /profile`

### Resumes
- `GET /resumes/labels` — allowed labels
- `GET /resumes/master`, `POST /resumes/master` (multipart: label + file)
- `GET /resumes/master/{id}`, `DELETE /resumes/master/{id}`
- `GET /resumes/master/{id}/versions`, `GET /resumes/master/{id}/download`

**Resume labels (exact strings):**
- `AI Resume`
- `IT Resume`
- `General Resume`
- `Construction Resume`
- `Production Resume`

### Jobs
- `GET /jobs/sources/presets`, `GET /jobs/sources`, `POST /jobs/sources`, `PATCH /jobs/sources/{id}`
- `GET /jobs`, `POST /jobs/import`, `GET /jobs/{id}`, `PATCH /jobs/{id}`, `DELETE /jobs/{id}`

### AI
- `GET /ai/status` — providers configured, capabilities
- `POST /ai/jobs/classify`, `POST /ai/jobs/{job_id}/score`
- `POST /foundation/prompts/sync` (auth)

### Agents (Layer 5)
- `POST /agents/jobs/{job_id}/analyze`
- `POST /agents/pipeline/run`
- `GET /agents/jobs/{job_id}/scores`, `GET /agents/jobs/ranked`, `GET /agents/jobs/{job_id}/runs`

### Documents (Layer 6)
- `POST /documents/jobs/{job_id}/generate`
- `GET /documents/jobs/{job_id}`, `GET /documents/jobs/{job_id}/artifacts/{type}`

### Tracking (Layer 7)
- `GET /tracking/applications`, `GET /tracking/jobs/{job_id}`
- `POST /tracking/jobs/{job_id}/approve|submit|withdraw`
- `POST /tracking/jobs/{job_id}/screenshots`

### Review (Layer 8)
- `GET /review/queue`, `GET /review/stats`
- `GET /review/jobs/{job_id}`, `POST /review/jobs/{job_id}/decide`
- `POST /review/batch`

**Review decisions:** `approve`, `reject`, `request_revision`

### Automation (Layer 9)
- `POST /automation/jobs/{job_id}/submit`
- `POST /automation/sessions/{session_id}/resume` (after CAPTCHA)
- `GET /automation/runs/{id}`, `GET /automation/jobs/{job_id}/runs`

### Scheduler (Layer 10)
- `POST /scheduler/run` — full morning pipeline
- `POST /scheduler/run/source/{id}`, `/company`, `/job/{job_id}`
- `GET /scheduler/status`, `GET /scheduler/runs`, `GET /scheduler/runs/{id}`
- `GET /scheduler/notifications`, `POST /scheduler/notifications/{id}/read`

### Billing
- `GET /billing/overview` — plan, limits, usage (monetization foundation)

### Foundation
- `GET /foundation/status`, `GET /foundation/audit` (auth)

---

## 9. Morning pipeline flow

Triggered by `POST /scheduler/run` or daily cron.

```
1. search_jobs     → Live search Job Bank + Indeed (skip manual source)
2. import_jobs     → Dedupe + classify on import
3. deduplicate     → (during import)
4. classification  → (during import)
5. immigration_scoring
6. ats_analysis
7. resume_selection
8. resume_tailoring
9. cover_letter
10. recruiter_email
11. application_package
12. review_queue
13. notify_user    → "Today's applications are ready for review." (if any ready)
```

**Does NOT auto-submit.** User approves in Review queue.

---

## 10. Live job search (implemented)

**File:** `backend/app/infrastructure/jobs/search/live_adapters.py`

| Source | connector_key | Status | Method |
|--------|---------------|--------|--------|
| Job Bank Canada | `job_bank_canada` | **Live** | HTTP scrape jobbank.gc.ca |
| Indeed Canada | `indeed` | **Live** | HTTP scrape ca.indeed.com |
| WorkPEI | `workpei` | Not implemented | — |
| Company Career Pages | `company_career_pages` | Not implemented | — |
| Manual URL Import | `manual_url_import` | Skipped in pipeline | User import API |

**Default search keywords:** `AI engineer`, `machine learning engineer`, `data scientist`

**Config per source** (in `job_sources.config` JSON):
- `search_keywords`: list or comma-separated string
- `location_string`: e.g. `Canada`, `Toronto, ON`
- `max_results`: default 25 (Job Bank), 15 (Indeed)

**Registry wired in:** `dependencies.get_job_search_registry()`

---

## 11. AI capability routing

**File:** `backend/app/infrastructure/ai/capabilities.yaml`

| Capability | Primary provider | Model |
|------------|------------------|-------|
| resume_tailoring | Anthropic | claude-sonnet-4-20250514 |
| cover_letter_generation | Anthropic | claude-sonnet-4-20250514 |
| email_generation | Anthropic | claude-sonnet-4-20250514 |
| job_classification | OpenAI | gpt-4o-mini |
| job_scoring | OpenAI | gpt-4o |
| ats_analysis | OpenAI | gpt-4o |
| immigration_scoring | OpenAI | gpt-4o-mini |
| resume_selection | OpenAI | gpt-4o-mini |
| embedding | OpenAI | text-embedding-3-small |

**Rule:** Services call `ModelRouter.complete_for_capability()` — never call providers directly (except in provider adapters).

---

## 12. Database migrations (Alembic)

| Revision | Layer |
|----------|-------|
| 001_layer0_foundation | System metadata |
| 002_audit_prompts_foundation | Audit + prompts |
| 003_layer1_user_profile | Users, profiles |
| 004_profile_job_preferences | Job prefs |
| 005_layer2_resumes | Master resumes |
| 006_layer3_jobs | Jobs, sources |
| 007_job_source_presets | Preset keys |
| 008_layer4_ai | AI tables |
| 009_layer5_intelligence | Scores, agent runs |
| 010_layer6_documents | Application documents |
| 011_layer7_tracking | Tracking, screenshots |
| 012_layer8_review | Review workflow |
| 013_layer9_browser_automation | Browser sessions, automation runs |
| 014_layer10_scheduler | Pipeline runs, notifications |

**Head:** `014_layer10_scheduler`

---

## 13. Key database models

- `users`, `user_profiles`
- `master_resumes`, `resume_versions`
- `job_sources`, `job_postings`
- `job_scores`, `agent_runs`
- `application_documents`, `applications`, `application_screenshots`
- `audit_logs`, `prompt_versions`
- `browser_sessions`, `automation_runs`, `automation_action_logs`
- `pipeline_runs`, `pipeline_notifications`

---

## 14. Product web app (`web/`)

**Routes:**
- `/` — Landing (marketing)
- `/login` — Sign in
- `/pricing` — Public pricing
- `/app` — Dashboard
- `/app/resumes` — Upload/list resumes (friendly labels → API labels)
- `/app/jobs` — Add jobs, run per-job pipeline
- `/app/review` — Review queue, approve/reject
- `/app/pipeline` — Run full pipeline + recent runs log
- `/app/pricing` — Plan + usage (authenticated)

**Auth:** JWT in localStorage (`career_os_token`).

**Build:** `cd web && npm install && npm run build` → served by FastAPI from `web/dist/`.

---

## 15. Desktop app (`desktop/`)

Tauri 2 thin client — **not** full product UI.

Features: login, review stats, manual pipeline trigger, Windows notifications, system tray, auto-start.

Requires: Node 20+, Rust, WebView2.

---

## 16. CLI (`career-os` command)

```bash
pip install -e ./backend
career-os version
career-os doctor          # Friendly health check
career-os migrate
career-os migrate-check
career-os health
career-os backup --output ./backups
career-os restore --input ./backups/file.tar.gz --yes
career-os upload-resume --file ../inbox/resume.pdf --type ai
```

---

## 17. Monetization (current state)

**Plans defined** in `backend/app/api/routes/billing.py`:

| Plan | Price CAD/mo | Pipeline runs | Jobs/mo | Resumes |
|------|--------------|---------------|---------|---------|
| Starter (free) | $0 | 5 | 10 | 2 |
| Pro | $29 | 50 | 100 | 5 |
| Career Coach | $99 | Unlimited | Unlimited | 20 |

**Stripe:** Not integrated yet — UI shows "Upgrade — coming soon".

**Usage tracking:** Counts pipeline runs + jobs imported this month from DB.

See `PRODUCT.md` for full GTM strategy.

---

## 18. How to run locally (Windows)

```powershell
# 1. PostgreSQL
Start-Service postgresql-x64-16

# 2. API
cd career-os/backend
pip install -e ".[dev]"
py -m alembic upgrade head
py -m uvicorn app.main:app --reload --port 8000

# 3. Product UI (option A — dev)
cd career-os/web
npm install
npm run dev
# Open http://localhost:3000

# 3. Product UI (option B — built-in)
cd career-os/web && npm run build
# Open http://localhost:8000
```

---

## 19. Production deployment

- `docker-compose.prod.yml` + `Dockerfile.prod`
- Set `ENVIRONMENT=production`, strong secrets
- `career-os migrate` on startup (entrypoint)
- See `DEPLOYMENT.md`

---

## 20. CI pipeline (`.github/workflows/ci.yml`)

Jobs: backend (ruff, migrate-check, pytest), desktop (npm test, build), web (npm build), docker-prod (image build).

---

## 21. Known limitations & gaps

1. **Indeed** may block/rate-limit scrapers (CAPTCHA)
2. **WorkPEI, company career pages** — search not implemented
3. **Stripe** — not wired
4. **Multi-user signup** — single-user mode default
5. **Production Docker** — Playwright browsers not installed in image (automation may fail in prod container)
6. **Desktop** — thin dashboard only, not full UI replacement
7. **Email** `user@careeros.local` deprecated — use `user@example.com`

---

## 22. User's current setup state

- PostgreSQL 16 installed locally (Windows)
- API keys configured (OpenAI + Anthropic) in `backend/.env`
- Resume uploaded: `Daksh Patel.pdf` as `AI Resume`
- Live job search implemented and tested (Job Bank returns real listings)
- Docker Desktop attempted but WSL setup was needed; user runs local PostgreSQL instead

---

## 23. Important code paths

| Task | Entry point |
|------|-------------|
| Pipeline orchestration | `scheduler_pipeline_service.py` |
| Live job search | `live_adapters.py` → `JobSearchRegistry` |
| Job import + dedup | `job_service.py` |
| AI routing | `infrastructure/ai/router.py` |
| Document generation | `document_generation_service.py` |
| Review decisions | `review_queue_service.py` |
| Browser submit | `application_automation_service.py` |
| Web UI API calls | `web/src/api/client.ts` |
| FastAPI app + static UI | `main.py` |

---

## 24. Testing

```bash
cd backend
pytest tests/ --ignore=tests/integration/test_database.py  # 172+ tests
cd ../web && npm run build
cd ../desktop && npm test
```

---

## 25. Documentation index

| File | Content |
|------|---------|
| `CLAUDE_PROJECT_BRIEF.md` | This file — full context for AI |
| `PRODUCT.md` | Monetization & GTM |
| `README.md` | Quick start |
| `ARCHITECTURE.md` | System design |
| `API_REFERENCE.md` | REST API |
| `DEPLOYMENT.md` | Production ops |
| `USER_GUIDE.md` | End-user manual |
| `RELEASE_NOTES.md`, `CHANGELOG.md`, `CONTRIBUTING.md` | Release & dev |

---

## 26. Design principles for future work

1. **Human-in-the-loop** — never auto-submit without explicit approval
2. **API-first** — web/desktop are thin clients
3. **Ports & adapters** — swap scrapers, LLM providers without changing services
4. **Single-user → multi-tenant** — schema ready, `single_user_mode` flag
5. **Monetization** — usage limits enforced at pipeline layer (V1.1)
6. **Canadian focus** — Job Bank, provinces, immigration scoring

---

## 27. For Claude: suggested use

When helping with Career OS:
- Prefer extending `web/` for user-facing features
- Use existing API routes — don't duplicate business logic in frontend
- New job sources → implement `JobSearchPort` + register in `get_job_search_registry()`
- New AI tasks → add to `capabilities.yaml` + agent in `application/services/agents/`
- Database changes → new Alembic migration, update `EXPECTED_MIGRATION_HEAD` in `cli.py`
- Do not expose secrets; `.env` is gitignored

---

*End of Career OS project brief.*
