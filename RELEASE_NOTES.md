# Career OS V1 — Release Notes

**Version:** 1.0.0  
**Release date:** June 2026  
**Status:** Production-ready

---

## Overview

Career OS V1 is a personal AI career operating system for a single Canadian job seeker. It automates job discovery, scoring, document generation, review, and optional browser-assisted submission — with a Windows desktop companion.

---

## What's Included

### Backend (Layers 0–10)
- User profile, authentication, and audit logging
- Five master resume labels with versioning
- Job import, deduplication, and classification
- Capability-based AI routing (OpenAI + Anthropic)
- Intelligence pipeline: immigration, scoring, ATS, resume selection
- Document generation: tailored resume, cover letter, recruiter email
- Review queue with approve / reject / revision workflow
- Application tracking with manual submission and screenshots
- Playwright browser automation with CAPTCHA pause/resume
- APScheduler morning pipeline with notifications

### Desktop (Layer 11)
- Tauri 2 Windows shell
- Native notifications for pipeline completion
- Local settings and auth token storage
- System tray with auto-start option

### Operations (Production Readiness)
- `career-os` CLI: migrate, backup, restore, health checks
- Production Docker image (`Dockerfile.prod`)
- GitHub Actions CI (backend, desktop, Docker)
- Environment-based security validation
- Comprehensive documentation

---

## Upgrade Notes

1. Copy `.env.example` to `.env` and set production secrets
2. Set `ENVIRONMENT=production` for deployed instances
3. Run `career-os migrate` before starting the API
4. Use `docker compose -f docker-compose.prod.yml up -d` for production

---

## Known Limitations

- Job search uses `scheduled_search_jobs` config until live scrapers are added
- Desktop is a dashboard shell, not a full web UI replacement
- Single-user mode by default
- `redis_url` is reserved for future use

---

## Documentation

| Document | Purpose |
|----------|---------|
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design |
| [API_REFERENCE.md](API_REFERENCE.md) | REST API |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Install and operate |
| [USER_GUIDE.md](USER_GUIDE.md) | End-user manual |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development guide |
