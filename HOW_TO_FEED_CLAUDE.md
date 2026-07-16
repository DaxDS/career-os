# How to Feed Career OS Into Claude Chat

Use this guide to give Claude **full project context** without missing details.

---

## Option 1 — Best: Claude Project (recommended)

1. Go to [claude.ai](https://claude.ai) → **Projects** → **Create project**
2. Name it **Career OS**
3. Add **Project knowledge** files:

### Must upload (priority order)

| File | Why |
|------|-----|
| `CLAUDE_PROJECT_BRIEF.md` | **Complete overview** — start here |
| `PRODUCT.md` | Monetization & business model |
| `ARCHITECTURE.md` | System design |
| `API_REFERENCE.md` | All endpoints |
| `DEPLOYMENT.md` | How to run in production |

### Also useful

- `README.md`
- `backend/app/infrastructure/ai/capabilities.yaml`
- `backend/app/domain/job_source_presets.py`
- `backend/app/application/services/scheduler_pipeline_service.py`
- `web/src/api/client.ts`

4. In project instructions, paste:

```
You are helping build and operate Career OS — an AI job search SaaS for Canadian job seekers.
Read CLAUDE_PROJECT_BRIEF.md first. The product UI is web/ at localhost:3000 or 8000.
Never suggest Swagger as the user interface. Default login: user@example.com / careeros-dev-password.
Live job search: Job Bank Canada + Indeed. Human-in-the-loop review before submit.
```

---

## Option 2 — Paste in one chat (quick)

1. Open `CLAUDE_PROJECT_BRIEF.md` in Cursor
2. Copy **entire file** (Ctrl+A, Ctrl+C)
3. Paste as first message in Claude:

```
Here is the complete Career OS project context. Read all of it before answering.

[paste CLAUDE_PROJECT_BRIEF.md here]
```

4. For code questions, paste specific files in follow-up messages.

**Limit:** Claude has context limits (~200k tokens). The brief fits; entire codebase does not.

---

## Option 3 — Zip the project (for Claude Projects or upload)

Run in PowerShell from `career-os` folder:

```powershell
# Creates career-os-export.zip excluding secrets and heavy folders
$exclude = @('node_modules', '.git', 'storage', 'dist', '__pycache__', '.pytest_cache', '*.egg-info', 'inbox\*.pdf')
Compress-Archive -Path * -DestinationPath ..\career-os-export.zip -Force
```

**Before zipping:** ensure `.env` is NOT included (check `.gitignore`).

Upload zip to Claude Project knowledge (Claude will index text files).

---

## Option 4 — GitHub (if you push the repo)

1. Push `career-os` to a **private** GitHub repo
2. In Claude, use GitHub integration or paste repo URL
3. Reference files by path: `backend/app/main.py`

---

## What NOT to feed Claude

- `backend/.env` — API keys
- `storage/` — personal resumes and documents
- `inbox/*.pdf` — your resume file
- `node_modules/` — too large, useless

---

## Verify Claude understood

Ask Claude:

```
Summarize Career OS in 5 bullets: what it does, tech stack, UI location, 
job search sources, and what's not implemented yet.
```

Expected: mentions web app, Job Bank + Indeed live search, review queue, no Stripe yet.

---

## Keep context updated

After major changes, re-upload or re-paste:

1. `CLAUDE_PROJECT_BRIEF.md` (update the "Last updated" section)
2. Any new migration or feature docs
