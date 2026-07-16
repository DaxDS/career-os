# Career OS — Cursor prompts

Ready-to-paste prompts for Cursor's agent, built from the competitive research and engineering audit done this session. Paste one at a time — each is self-contained with context, files, and acceptance criteria so Cursor doesn't have to guess scope.

Session note: `web/src` and the score API (`backend/app/api/routes/review.py`, `review_queue_service.py`) were already touched this session (Apply route fix, immigration score surfaced, pricing bug fix). Run the verification prompt first so Cursor has current-state context before building on top.

---

## 0. Verify this session's changes

```
Before I add anything new, verify the current state of this repo builds and tests cleanly.

1. Backend: cd backend, install deps if needed (pip install -e ".[dev]"), then run
   pytest tests/ -v --ignore=tests/integration/test_database.py
   Pay particular attention to tests/integration/test_review_api.py — the
   ReviewQueueItem dataclass and ReviewQueueItemResponse/ReviewDetailResponse
   schemas in app/api/schemas/review.py recently gained three new optional
   fields (match_score, ats_score, immigration_score, all defaulted to None
   at the end of the dataclass/schema to preserve field ordering). Confirm
   nothing broke.

2. Frontend: cd web, run npm install, npx tsc --noEmit, and npm run build.
   Confirm no type errors and the build succeeds.

3. Report back: pass/fail for each, and paste any failing test output or
   compiler errors so I can decide what to fix first.

Do not change any application code in this pass — this is a verification-only step.
```

---

## Now — close the gaps

### 1. Free Chrome-extension autofill (acquisition wedge)

```
Context: Career OS is a job-search AI pipeline (FastAPI backend in backend/,
React+Vite frontend in web/). Competitive research found that every major
competitor in this category (Teal, Simplify Copilot, Huntr, Careerflow) uses
a free browser-extension autofill as their primary user-acquisition wedge —
free before the paid AI tiers. Career OS currently has no browser extension
at all; the only "apply" path is the internal Playwright automation gated
behind a logged-in account and a review queue.

Task: scaffold a minimal Chrome extension (Manifest V3) in a new top-level
`extension/` directory that:
- On any job application form (start with Workday, Greenhouse, and Lever
  detection via DOM heuristics — look for their known form field patterns),
  shows a small floating button "Autofill from Career OS".
- On click, calls the existing backend API (see backend/app/api/routes/resumes.py
  and profile.py) to pull the user's active master resume + profile fields,
  and fills name/email/phone/resume-upload/work-authorization fields it can
  confidently match.
- Requires the user to already have a Career OS account and paste in an API
  token (reuse the existing JWT auth in app/api/routes/auth.py) — no new
  auth system.
- Does NOT click any Submit/Apply button — stops at filled-but-unsubmitted,
  consistent with the product's human-in-the-loop positioning.

Keep the first version narrow (3 ATS platforms, best-effort field matching)
rather than broad and unreliable. Add a extension/README.md with load-unpacked
instructions for local testing.
```

### 2. Surface the PR/NOC score everywhere it matters

```
Context: immigration_score (Express Entry / NOC / PR pathway fit) is Career
OS's single biggest competitive differentiator — zero competitors researched
(Teal, Simplify, Huntr, Jobright, JobCopilot, LoopCV, LazyApply) score this.
It was already wired through the review queue this session
(web/src/pages/Review.tsx now shows a "🇨🇦 XX% PR fit" badge), but it's not
surfaced anywhere else a user would see it.

Task:
1. In web/src/pages/Jobs.tsx, add the immigration/PR score as a column or
   badge next to each job in the "Your jobs" table — currently that table
   only shows role, company, and "Score track". Check whether
   GET /api/v1/jobs already returns a score; if not, extend the backend
   route (backend/app/api/routes/jobs.py) to join in the JobScore data the
   same way review_queue_service.py does.
2. On web/src/pages/Landing.tsx, the current copy says "The only job
   platform that scores every posting for your Express Entry pathway" —
   good headline, but nothing on the page after the hero actually shows
   what that score looks like. Add a small visual mockup or real
   screenshot-style component under the hero showing an example PR-fit
   score badge, so the claim is demonstrated, not just stated.
3. Confirm backend/app/api/routes/jobs.py list endpoint doesn't leak scores
   for jobs belonging to other users — reuse the existing user_id scoping
   pattern from review_queue_service.py.
```

### 3. Finish Stripe Checkout for both paid tiers

```
Context: backend/app/api/routes/billing.py was updated this session to
support both "pro" and "team" (Career Coach) plans via a price_by_plan map
that reads settings.stripe_price_pro and settings.stripe_price_team
(backend/app/config.py). Pro was already wired; Career Coach was previously
broken (always charged the Pro price). Stripe itself has not been configured
in any environment yet.

Task:
1. Walk me through creating two Stripe Price objects (Pro monthly CAD $29,
   Career Coach monthly CAD $99) in test mode, either via Stripe CLI
   commands you generate or a script in backend/scripts/.
2. Add STRIPE_SECRET_KEY, STRIPE_PRICE_PRO, and STRIPE_PRICE_TEAM to
   backend/.env.example with comments explaining where to get each value.
3. Implement the Stripe webhook handler that's referenced but not yet built
   — after a successful checkout, the user's plan_tier needs to actually
   update (PRODUCT.md phase 2 mentions this: "plan_tier on User model").
   Check backend/app/infrastructure/db/models.py for the User model and add
   the field + migration if it doesn't exist, then wire
   POST /api/v1/billing/webhook to verify the Stripe signature and update
   plan_tier on checkout.session.completed.
4. Enforce the plan limits during pipeline runs (ai_pipeline_runs,
   jobs_per_month, resume_slots) — right now backend/app/api/routes/billing.py
   billing_overview() hardcodes plan_key = "free" with a comment saying
   "Stripe subscription will set plan tier on User in V1.1". Make that real:
   read the actual plan_tier off the User row.
5. Return a 402 Payment Required with a clear message when a user exceeds
   their plan's limits, and surface that error cleanly in the frontend
   (web/src/pages/Pipeline.tsx and Jobs.tsx already have error-banner
   patterns to reuse).
```

---

## Next — match the category

### 4. LinkedIn profile optimizer

```
Context: Careerflow.ai's strongest and most-used feature (per competitive
research) is a free LinkedIn profile optimizer — it's their user-acquisition
hook the same way autofill is for Simplify/Huntr. Career OS has nothing like
this today.

Task: add a new "LinkedIn" page to the app (web/src/pages/, add to the NAV
array in web/src/components/AppShell.tsx and the route in App.tsx). It
should:
1. Let the user paste their LinkedIn "About" section and headline as plain
   text (no LinkedIn API/scraping — keep this manual-paste to avoid ToS
   issues, consistent with the product's existing "no bypassing platform
   protections" stance from the browser-automation layer).
2. Send it through the existing AI capability-routing system
   (backend/app/application/services — follow the pattern used by
   resume_tailoring or cover_letter_generation capabilities in
   capabilities.yaml) with a new `linkedin_optimization` capability that
   scores keyword density against the user's target role family and
   suggests specific rewrites.
3. Show a before/after diff view, reusing styling patterns from
   web/src/styles/review.css (score-panel, preview-block classes already
   exist and fit this use case).
Keep this additive — don't touch the existing resume/job/pipeline flows.
```

### 5. Mock interview prep

```
Context: Careerflow and JobCopilot both ship mock interview practice as a
retention feature (keeps users in the product between application cycles).
Career OS's pipeline currently ends at application submission with no
post-application engagement loop.

Task: add an "Interview Prep" page that, for any job with status "approved"
or "submitted" (see backend/app/api/routes/tracking.py for the existing
application status model), generates 5-8 likely interview questions based
on the job description and the user's tailored resume for that job (reuse
the same job_id + document lookup pattern as
backend/app/application/services/review_queue_service.py's
_document_previews). Let the user type a practice answer and get AI
feedback via a new `interview_coaching` capability. This is a good candidate
for a Pro-tier-gated feature — check how billing.py's plan features list is
structured and add "Interview prep" to the Pro plan's feature list only.
```

### 6. Broaden ATS autofill coverage

```
Context: Career OS's Playwright automation (backend/app/infrastructure,
see the Layer 9 browser automation docs in README.md) currently only has
connector presets for job_bank_canada, workpei, indeed, and
company_career_pages (backend/app/api/routes/jobs.py — search for
source_preset_key). Competitors claim autofill across "100+ ATS platforms";
Career OS's automation is Canada-specific and narrow.

Task: add connector presets for Workday and Greenhouse-hosted job postings
(these two cover a large share of North American tech-company postings).
Follow the existing connector pattern — check
backend/app/infrastructure/browser_automation or wherever the
job_bank_canada connector logic lives, and mirror its structure:
- Detect the ATS platform from the posting URL pattern
  (myworkdayjobs.com, boards.greenhouse.io)
- Map their form field selectors (these are fairly stable/documented in
  Playwright automation communities — look them up)
- Reuse the existing CAPTCHA-pause and stop-before-submit safety behavior
  exactly as-is; do not weaken those guarantees for the new connectors.
Add tests mirroring whatever test coverage exists for the job_bank_canada
connector.
```

---

## Later — scale

### 7. Multi-tenant self-serve signup

```
Context: README.md and PRODUCT.md both describe the current deployment as
"single-user deploy; you as first customer" (Phase 1). Auth already exists
(backend/app/api/routes/auth.py has register/login), so this may already be
closer to multi-tenant than the docs suggest — audit before assuming work
is needed.

Task: confirm whether backend/app/api/routes/auth.py's register endpoint
already supports arbitrary new users signing up (not just a single seeded
account), and whether all data access throughout the API is properly scoped
by user_id (spot-check jobs.py, resumes.py, review.py, tracking.py for
Depends(get_current_user_id) usage — review_queue_service.py has the
right pattern to compare against). If self-serve signup already works
end-to-end, the remaining work is just removing "single-user" language from
docs and adding basic abuse protection (rate limiting on /auth/register,
email verification). If it doesn't work, report back what's missing before
building anything.
```

### 8. Mobile-friendly PWA

```
Context: web/ is a Vite + React 19 SPA with no PWA manifest or
service worker currently. The review/approve workflow (web/src/pages/Review.tsx)
is the highest-value screen to make usable on a phone — users will want to
approve applications from their phone between pipeline runs.

Task:
1. Add a web app manifest (vite-plugin-pwa is the standard choice for
   Vite) with Career OS's existing branding (teal #2dd4bf accent, dark
   #0b0f14 background — pull exact values from web/src/styles/global.css).
2. Audit web/src/styles/*.css for fixed-width layouts that will break
   below ~500px — review.css's .review-layout grid
   (grid-template-columns: 320px 1fr) already has a mobile breakpoint at
   900px; verify it actually looks usable at phone width, not just
   "doesn't overflow".
3. Don't attempt offline support in this pass — a responsive, installable
   shell is the goal, not full offline-first behavior.
```

### 9. Recruiter / networking contact discovery

```
Context: Jobright.ai's "Insider Connections" feature (surfacing recruiter/
employee contacts at target companies) was flagged in competitive research
as a differentiator Career OS doesn't have. This is the lowest-priority
roadmap item — treat it as exploratory, not committed scope.

Task: don't build anything yet. Research and report back on:
1. What data source this would realistically use without scraping LinkedIn
   directly (which risks the same ToS/anti-bot problems flagged for the
   browser-automation layer — see the "Risks to watch" section of the
   engineering review). Consider whether a legitimate people-data API
   (e.g. a paid B2B contact-enrichment provider) is more viable than any
   scraping approach.
2. Rough cost per lookup at that provider, and whether it fits the
   existing Pro ($29/mo) or Career Coach ($99/mo) pricing without wrecking
   margins.
Report findings before I decide whether this makes the roadmap for real.
```

---

## Positioning / marketing polish (small, do anytime)

```
Context: web/src/pages/Landing.tsx currently has unverifiable superlative
claims ("The only tool that does quality-tailored autonomous apply, not
volume spam.") sitting right next to a self-authored comparison table
(web/src/components/FeatureComparison.tsx) that isn't cited or sourced.
For a technical audience this reads as unsubstantiated marketing copy
rather than an engineering-credible claim — even though the underlying
claim (human-in-the-loop + PR/NOC scoring) is genuinely true and
differentiated per this session's competitive research.

Task: rewrite the hero subhead and the italic tagline on Landing.tsx to be
specific and falsifiable rather than superlative — e.g. state the actual
mechanism ("every application stops at a review queue before it's
submitted") instead of the adjective ("the only tool that does
quality-tailored..."). Keep FeatureComparison.tsx's table but add a small
"as of [date], based on public pricing pages" caption so it reads as
researched rather than asserted.
```
