# Changelog

All notable changes to Career OS are documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] - 2026-06-22

### Added — Foundation (Layers 0–3)
- PostgreSQL schema with Alembic migrations
- Audit logging and prompt versioning
- User profile and JWT authentication
- Master resume upload (5 labels) with file storage
- Job sources, import, deduplication, rule/LLM classification

### Added — Intelligence (Layers 4–6)
- Capability registry and model router with provider fallback
- LangGraph intelligence pipeline (immigration, scoring, ATS, resume selection)
- Document generation (tailoring, cover letter, email, ATS report)

### Added — Workflow (Layers 7–8)
- Application tracking: approve, submit, withdraw, screenshots
- Review queue with batch decisions and revision loop

### Added — Automation (Layers 9–10)
- Playwright browser automation with connector registry
- CAPTCHA pause/resume; stop-before-submit
- APScheduler morning pipeline with scoped runs and notifications

### Added — Desktop (Layer 11)
- Tauri 2 Windows desktop shell
- Native notifications, tray icon, auto-start, local settings

### Added — Production Readiness
- `career-os` CLI (`migrate`, `backup`, `restore`, `health`, `migrate-check`)
- `Dockerfile.prod` and `docker-compose.prod.yml`
- GitHub Actions CI workflow
- `ENVIRONMENT=production` security validation
- Configurable `CORS_ORIGINS`
- HTTP request logging middleware
- OpenAPI tag documentation
- Dependency version upper bounds
- Root `.gitignore` and expanded `.env.example`

### Fixed (V1 audit)
- APScheduler cron bootstrap dependency wiring
- CORS for Tauri desktop origins
- Auth on prompt sync, audit query, and job classify endpoints
- Duplicate job search in scheduler pipeline
- Stale health/foundation layer labels

[1.0.0]: https://github.com/your-org/career-os/releases/tag/v1.0.0
