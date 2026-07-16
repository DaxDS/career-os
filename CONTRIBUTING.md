# Contributing to Career OS

Thank you for contributing. Career OS V1 is complete; future changes should preserve the layered architecture and avoid duplicating business logic in the desktop client.

---

## Development Setup

```bash
# Backend
cd backend
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload

# Desktop (optional)
cd desktop
npm ci
npm run tauri:dev
```

Copy `.env.example` to `backend/.env` for local configuration.

---

## Project Structure

```
career-os/
  backend/          FastAPI application (Layers 0–10)
  desktop/          Tauri thin client (Layer 11)
  prompts/          AI prompt files (synced to DB)
  storage/          Runtime file storage (gitignored)
  docs/             Supplemental audit documentation
```

---

## Architecture Rules

1. **Hexagonal boundaries** — Application services depend on ports, not infrastructure directly.
2. **AI routing** — Use `ModelRouter.complete_for_capability()`; never call OpenAI/Anthropic from services.
3. **Additive layers** — New features should extend via new modules; avoid rewriting prior layers.
4. **Desktop is thin** — No business logic in `desktop/`; call backend APIs only.
5. **No auto-submit** — Application submission requires explicit user approval.

---

## Code Style

- Python: `ruff check app tests` (line length 100)
- TypeScript: strict mode, Vitest for unit tests
- Logging: `get_logger(__name__)` with structured key/value fields

---

## Testing

```bash
# Backend
cd backend
pytest tests/ -v --ignore=tests/integration/test_database.py
ruff check app tests
career-os migrate-check

# Desktop
cd desktop
npm test
npm run build
```

CI runs automatically on push/PR via GitHub Actions.

---

## Migrations

1. Create revision: `cd backend && alembic revision -m "description"`
2. Update `EXPECTED_MIGRATION_HEAD` in `app/cli.py` if adding a new head
3. Update `tests/unit/test_migrations_chain.py` expectations
4. Register new models in `alembic/env.py`

---

## Pull Request Checklist

- [ ] Tests pass locally
- [ ] No secrets committed
- [ ] Migration chain remains linear (if DB changes)
- [ ] API changes reflected in `API_REFERENCE.md`
- [ ] Production settings unaffected unless intentional

---

## Reporting Issues

Include:
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs (`LOG_JSON=true` output)
- Environment (`ENVIRONMENT`, Python/Node versions)
