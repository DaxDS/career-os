# Career OS V1 — API Reference

**Base URL:** `http://127.0.0.1:8000/api/v1`  
**Auth:** Bearer JWT (`Authorization: Bearer <token>`)  
**OpenAPI:** `GET /docs` (Swagger UI)

---

## Authentication

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | No | Register user (blocked in single-user mode if user exists) |
| POST | `/auth/login` | No | Login; returns `access_token` |
| GET | `/auth/me` | Yes | Current user |

---

## Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | App status, version, layer |
| GET | `/ready` | No | Database connectivity check |

---

## Foundation

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/foundation/status` | No | Storage paths, prompt registry status |
| GET | `/foundation/audit` | Yes | Query audit log (`entity_type`, `entity_id`, `action`, `limit`) |

---

## Profile

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/profile` | Yes | User profile |
| PATCH | `/profile` | Yes | Update profile |

---

## Resumes

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/resumes/labels` | No | Valid resume labels |
| GET | `/resumes/master` | Yes | List master resumes |
| POST | `/resumes/master` | Yes | Upload resume (multipart) |
| GET | `/resumes/master/{id}` | Yes | Get resume metadata |
| GET | `/resumes/master/{id}/versions` | Yes | Version history |
| GET | `/resumes/master/{id}/download` | Yes | Download file |
| DELETE | `/resumes/master/{id}` | Yes | Deactivate resume |

---

## Jobs

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/jobs/sources/presets` | No | Built-in source presets |
| GET | `/jobs/sources` | Yes | User job sources |
| POST | `/jobs/sources` | Yes | Create source |
| PATCH | `/jobs/sources/{id}` | Yes | Update source |
| GET | `/jobs` | Yes | List jobs (filters: province, role_family, status, source_id) |
| POST | `/jobs/import` | Yes | Import job payloads |
| GET | `/jobs/{id}` | Yes | Get job |
| PATCH | `/jobs/{id}` | Yes | Update job |
| DELETE | `/jobs/{id}` | Yes | Archive job |

---

## AI

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/ai/status` | No | AI enabled, providers, capabilities |
| POST | `/foundation/prompts/sync` | Yes | Sync prompts from filesystem to DB |
| POST | `/ai/jobs/classify` | Yes | Classify job posting (rule-based or LLM) |
| POST | `/ai/jobs/{id}/score` | Yes | Score single job (requires AI enabled) |

---

## Agents (Layer 5)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/agents/jobs/{id}/analyze` | Yes | Full intelligence pipeline |
| POST | `/agents/pipeline/run` | Yes | Batch analyze unscored jobs |
| GET | `/agents/jobs/{id}/scores` | Yes | Get persisted scores |
| GET | `/agents/jobs/ranked` | Yes | Ranked jobs by score |
| GET | `/agents/jobs/{id}/runs` | Yes | Agent run history |

---

## Documents (Layer 6)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/documents/jobs/{id}/generate` | Yes | Generate application package |
| GET | `/documents/jobs/{id}` | Yes | Get application + documents |
| GET | `/documents/jobs/{id}/{type}` | Yes | Get specific document artifact |

---

## Tracking (Layer 7)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/tracking/applications` | Yes | List applications by status |
| GET | `/tracking/jobs/{id}` | Yes | Application detail |
| POST | `/tracking/jobs/{id}/approve` | Yes | Approve for submission |
| POST | `/tracking/jobs/{id}/submit` | Yes | Record manual submission |
| POST | `/tracking/jobs/{id}/withdraw` | Yes | Withdraw application |
| POST | `/tracking/jobs/{id}/screenshots` | Yes | Upload submission screenshot |

---

## Review (Layer 8)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/review/queue` | Yes | Pending review items |
| GET | `/review/stats` | Yes | Queue counts |
| GET | `/review/jobs/{id}` | Yes | Review detail + previews |
| POST | `/review/jobs/{id}/decide` | Yes | Approve / reject / request_revision |
| POST | `/review/batch` | Yes | Batch decisions |

---

## Automation (Layer 9)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/automation/jobs/{id}/submit` | Yes | Start Playwright submission |
| POST | `/automation/sessions/{id}/resume` | Yes | Resume after CAPTCHA |
| GET | `/automation/runs/{id}` | Yes | Run status |
| GET | `/automation/jobs/{id}/runs` | Yes | Runs for job |
| GET | `/automation/runs/{id}/actions` | Yes | Action log |
| GET | `/automation/sessions` | Yes | Browser sessions |

---

## Scheduler (Layer 10)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/scheduler/run` | Yes | Manual full pipeline |
| POST | `/scheduler/run/source/{id}` | Yes | Single source run |
| POST | `/scheduler/run/company` | Yes | Single company run |
| POST | `/scheduler/run/job/{id}` | Yes | Single job run |
| GET | `/scheduler/status` | No | Scheduler enabled, next run |
| GET | `/scheduler/runs` | Yes | Recent pipeline runs |
| GET | `/scheduler/runs/{id}` | Yes | Run detail |
| GET | `/scheduler/notifications` | Yes | Pipeline notifications |
| POST | `/scheduler/notifications/{id}/read` | Yes | Mark notification read |

---

## Error Handling

| Condition | HTTP Status |
|-----------|-------------|
| Validation / business rule | 400 |
| Not found | 404 |
| Missing / invalid token | 401 / 403 |
| AI or automation disabled | 503 |

Errors return `{"detail": "<message>"}`.
