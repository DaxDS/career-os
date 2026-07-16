# Career OS V1 — User Manual

Career OS is your personal AI-powered job application system for the Canadian market. It helps you discover jobs, score them for fit and immigration potential, generate tailored application materials, review them before sending, and optionally assist with browser-based submission.

---

## Getting Started

### 1. Start the Backend

Use Docker (`docker compose up`) or run the API locally. See [DEPLOYMENT.md](DEPLOYMENT.md).

### 2. Sign In

Default credentials (change in production):
- **Email:** `user@careeros.local`
- **Password:** `careeros-dev-password`

Sign in via the desktop app or API (`POST /api/v1/auth/login`).

### 3. Set Up Your Profile

Update your profile with:
- Legal name, location, work authorization
- Preferred provinces and job categories
- Skills, salary range, remote preference
- Immigration goals (for PR scoring)

`PATCH /api/v1/profile`

### 4. Upload Resumes

Upload up to five master resumes (one per label):
- Production, Maintenance, Quality, Engineering, General

`POST /api/v1/resumes/master` (multipart file upload)

Supported formats: `.txt`, `.pdf`, `.docx`

---

## Daily Workflow

### Morning (Automated)

If the scheduler is enabled, Career OS runs each morning:

1. Searches configured job sources
2. Imports new jobs (skips duplicates)
3. Classifies and scores each job
4. Generates tailored resume, cover letter, and recruiter email
5. Places applications in your **review queue**
6. Notifies you: *"Today's applications are ready for review."*

### Review Applications

Check your review queue:

```
GET /api/v1/review/queue
```

For each application you can:
- **Approve** — ready for submission
- **Reject** — discard
- **Request revision** — regenerate documents with notes

Or use the desktop app to see pending counts and notifications.

### Submit Applications

Career OS does **not** auto-submit by default. After approving:

**Manual submission:**
1. Submit on the employer's website yourself
2. Record it: `POST /api/v1/tracking/jobs/{id}/submit`
3. Optionally upload a screenshot

**Browser-assisted submission (Layer 9):**
1. Approve the application in review
2. `POST /api/v1/automation/jobs/{id}/submit`
3. Playwright opens the job page, fills the form, uploads documents
4. If CAPTCHA appears, resolve it and resume the session
5. Use `stop_before_submit: true` to review the form before final click

---

## Job Sources

Five built-in presets are seeded automatically:

| Source | Type |
|--------|------|
| Job Bank Canada | API (config placeholder) |
| WorkPEI | API (config placeholder) |
| Indeed | Scraper (config placeholder) |
| Company Career Pages | Manual |
| Manual URL Import | Manual |

To test the pipeline before live scrapers exist, add jobs to a source config:

```json
{
  "scheduled_search_jobs": [
    {
      "title": "Production Operator",
      "company": "Atlantic Foods",
      "description": "...",
      "location_province": "PE"
    }
  ]
}
```

Or import manually: `POST /api/v1/jobs/import`

---

## Intelligence Scoring

Each job receives:
- **Immigration score** — PR pathway fit, NOC alignment
- **Match score** — skills and experience fit
- **ATS score** — keyword and formatting analysis
- **Resume selection** — picks best master resume for the role

Trigger manually: `POST /api/v1/agents/jobs/{id}/analyze`

Requires `AI_ENABLED=true` and API keys.

---

## Document Package

For each scored job, Career OS generates:
- Tailored resume (JSON + stored artifact)
- Cover letter
- Recruiter outreach email
- ATS report

Trigger: `POST /api/v1/documents/jobs/{id}/generate`

Applications start in `generated` status (review queue).

---

## Desktop App

The Windows desktop companion provides:

| Feature | What it does |
|---------|-------------|
| Connection panel | Sign in to your local backend |
| Review stats | Pending / approved / rejected counts |
| Notifications | Windows toasts when pipeline completes |
| Settings | Backend URL, auto-start, poll interval |
| Tray icon | Run in background; close hides to tray |
| Manual pipeline | Trigger morning run on demand |

The desktop stores only your auth token and preferences. All career data lives on the backend.

---

## Scheduler Controls

| Action | How |
|--------|-----|
| Run full pipeline | Desktop button or `POST /scheduler/run` |
| Run one source | `POST /scheduler/run/source/{id}` |
| Run one company | `POST /scheduler/run/company` |
| Run one job | `POST /scheduler/run/job/{id}` |
| Check schedule | `GET /scheduler/status` |

---

## Status Reference

| Application Status | Meaning |
|-------------------|---------|
| `generated` | Documents ready for your review |
| `approved` | You approved; ready to submit |
| `rejected` | You rejected during review |
| `revision_requested` | Needs document regeneration |
| `submitted` | Application recorded as sent |

| Job Status | Meaning |
|------------|---------|
| `new` | Imported, not yet processed |
| `archived` | Removed from active list |

---

## Tips

1. **Upload all five resume types** before running the pipeline — selection works best with options.
2. **Complete your profile** — immigration and match scores use your preferences.
3. **Review before submitting** — the system is designed for human oversight.
4. **Use stop-before-submit** when testing browser automation on real applications.
5. **Check audit log** (`GET /foundation/audit`) to trace system actions.

---

## Getting Help

- API reference: [API_REFERENCE.md](API_REFERENCE.md)
- Architecture details: [ARCHITECTURE.md](ARCHITECTURE.md)
- Deployment issues: [DEPLOYMENT.md](DEPLOYMENT.md)
- Interactive API docs: `http://127.0.0.1:8000/docs`
