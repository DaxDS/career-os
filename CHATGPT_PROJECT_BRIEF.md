# Career OS / Professional Twin — Project Brief for ChatGPT

**Purpose:** Paste this entire document into ChatGPT as project context.  
**Last updated:** July 2026  
**Owner:** Daksh Patel  
**Workspace:** `s:\cursor\AI - Job application\career-os`

---

## How ChatGPT should behave

1. **Strategy is decided.** Do not reopen “should this be an apply bot?” debates unless the user explicitly asks to revisit strategy.
2. **Company thesis:** Professional Twin. Career OS is the **first product** built on that platform.
3. **Product law:** Optimize for decision quality, career growth, memory, evidence, opportunity routing, trust — **not** resume spam, cover-letter factories, or mass auto-apply.
4. **Engineering source of truth:** Live code is `apps/web` (Next.js) + Supabase + Stripe + Claude on Vercel. Treat `web/` + `backend/` as legacy.
5. **When coding:** Small focused diffs; never commit secrets; immigration/pathway scores are informational, not legal advice; preserve human approval for any send/apply actions.
6. **When designing product:** Prefer Sunday Twin ritual, Twin memory, Evidence Gaps, Outcome logging over new apply features.

---

## PART 1 — Company thesis (locked)

### Mission
Help ambitious professionals make better career decisions throughout their entire career — not just find jobs, generate resumes, or apply faster.

### Category
**Professional Twin Platform** — a living digital model of the professional (skills, evidence, goals, constraints, history, outcomes) plus an Opportunity Graph that routes high-leverage next moves.

### Branding relationship
- **Platform / substrate:** Professional Twin  
- **First product surface:** Career OS (weekly decision cockpit powered by the Twin)  
- Applications are a **small optional feature**, not the product.

### Atomic unit
The **Twin** and the **weekly decision** — not the job application.

### Magical moment (“can’t live without this”)
**The Counterfactual** — Twin compares Offer A vs B vs stay using the user’s goals, constraints, evidence, and history. Feeling: “I would have flown blind.”

### What we refuse to become
Job board · auto-apply spam · resume factory · social feed · interview cheating copilot · generic ChatGPT wrapper with a careers prompt.

---

## PART 2 — First product design (locked direction)

### Product in one sentence
Every Sunday, your Twin tells you the **three highest-leverage career moves** this week — with evidence, risks, and the smallest next action — and remembers every outcome so next week is smarter.

### Primary habit
**Sunday Twin** (8–12 minutes). Finite. No feed. No endless scroll.

**Fixed brief structure:**
1. Top 3 Opportunities  
2. Biggest Risk  
3. Biggest Evidence Gap  
4. One Skill To Learn  
5. One Person To Contact  
6. One Project To Build  
7. One Career Decision  
8. Reflection: what happened to last week’s #1?

Each item: Accept / Later / Not me → trains the Twin.

**Opportunity types allowed:** role, internal move, skill bet, relationship, project/proof, mobility/constraint.  
**Forbidden:** spray-apply N jobs.

### Why install / return / stay 5 years
- **Today:** Stuck between options, drowning in search, plateauing, or constraint-heavy (e.g. visa/geo).  
- **Next week:** Personal finite brief; logging outcomes changes next week; evidence gaps close.  
- **Five years:** Career memory ChatGPT doesn’t keep; switching cost; expands with life stage without reset.

### Onboarding (≤15 min; value before leave)
1. Intent mode (Growing / Exploring / Transition / Constrained) — 60s  
2. Identity seed (title/company/location/seniority) — 90s  
3. Import spine (resume, LinkedIn export/URL, GitHub, portfolio) — 3–6 min  
4. Twin mirror + max 3 corrections — 2 min  
5. Goals (≤3) + constraint chips — 2 min  
6. **First Decision Brief** + Accept/Later/Not me — 2 min  
7. Ritual time/channel — 30s  

**Never ask day 1:** full CV essay, required salary, email passwords, blanket Drive access, personality quizzes, friend-list scrape.

**Import priority v1:** Resume, LinkedIn export/URL, GitHub (eng), portfolio URL, certificates. Calendar/email later (opt-in vault). No continuous LinkedIn scrape; no Drive vacuum.

### Home information architecture (not visual UI)
- **A. Ritual Hero** — Weekly Decision Brief (the product)  
- **B. Twin Pulse** — Career Health, Professional Confidence, Biggest Risk  
- **C. Capital & Gaps** — Evidence Gaps, Learning Priorities, Interview Readiness (contextual)  
- **D. Trajectory** — Salary Trajectory (opt-in), Opportunity Score, Career Risks  
- **E. Graph Peek** — Professional Graph snapshot, 1–2 Relationship Opportunities  
- **F. Memory Rail** — Last 5 decisions/outcomes  

**Nav:** Home · Twin · Brief Archive · Evidence · Opportunities · Relationships · Settings/Vault  
**No top-level “Jobs” in v1** — jobs are one Opportunity node type.

### Twin memory
**Permanent:** verified roles/history, evidence artifacts, decisions log, outcomes, goals history, user corrections.  
**Decays/expires:** soft inferences, hot opportunities, drafts, session chat, provisional parses, stale market snippets.  
**Why > ChatGPT:** schema + provenance + corrections + outcome labels + constraint engine + weekly ritual.

### Graphs (platform; v1 stores all, UI exposes few)
Professional · Opportunity · Evidence · Relationship · Trust · Learning · Career · Outcome  
Each has nodes, relationships, signals, learning, updates, scoring, business value (see product design canvas for detail).

### AI architecture (product-level)
Layers: Ingestion → Memory → Retrieval → Reasoning → Planning → Reflection → Generation (optional) → Safety.  
**Agents:** Librarian, Auditor, Strategist, Coach, Reflector, Guardian.  
**Law:** Constraints in **code** (hard fail). LLM explains/ranks. Chat is never system of record. Explainability required on rankings.  
**Kill metric:** resumes generated per user. **Win metrics:** Sunday opens, Accept→action, retention **without** active job search.

### v1 ship / no-ship
**Ship:** Onboarding → Twin mirror → First Brief → Sunday Twin → Outcome logging → Evidence Gaps; constraints as Twin attributes; Career OS on Twin.  
**Do not ship v1:** Auto-apply, job feed, social feed, recruiter marketplace, live interview copilot, Drive-wide ingest, required salary, immigration-as-entire-homepage.

### Proof Twin should exist (90-day targets)
- D1 Brief completion ≥70%  
- W4 Sunday open ≥40%  
- W8 active **without** active job search ≥35%  
- ≥40% weeks with ≥1 Accept; ≥25% action completion on Accepted  

---

## PART 3 — What exists in code today (engineering reality)

### Live URLs
- **Canonical:** https://career-os-daxds.vercel.app  
- **Alias:** https://web-alpha-henna-62.vercel.app (same Next.js deployment)

### Current positioning on landing (may lag Twin messaging)
- Headline about Express Entry / scoring postings  
- Teal/charcoal dark theme; score-card mockup (Senior AI Engineer @ Bell Canada)  
- Eyebrow “AI Career Operating System” removed  
- Product principle: human approve-before-send (marketing may still say “auto-submits” — prefer product principle)

### Stack (live)
| Piece | Tech |
|-------|------|
| App | Next.js 14 App Router — `apps/web` |
| Auth/DB | Supabase (Auth, Postgres, RLS) — prefer ca-central-1 |
| i18n | next-intl (en/fr) |
| Billing | Stripe Checkout + webhook → `profiles.plan_tier` |
| AI | Anthropic Claude (`ANTHROPIC_API_KEY`); optional LangGraph agent `services/agent` |
| Shared | `packages/shared` (incl. PLANS) |
| Deploy | Vercel `daxds-projects/career-os` |

### Legacy (do not treat as live product)
- `web/` — Vite React (original teal landing reference)  
- `backend/` — FastAPI  
- `desktop/` — Tauri  
- Older docs (`CLAUDE_PROJECT_BRIEF.md`, parts of `PRODUCT.md`) may describe legacy/$29 pricing

### Current pricing in code
- Free: $0 · ~5 sends/day · limited tailored apps/month  
- Pro: **$24 CAD/mo** · higher caps · unlimited tailoring (intent)  
- Stripe **test mode**; card `4242 4242 4242 4242`  
- Strategy/product may later add Sprint / Continuity / Twin Pro — not all reflected in code yet

### Demo
- Email: `demo@careeros.app`  
- Password: `careeros-dev-password`

### Monorepo focus
```
career-os/
├── apps/web/              # ★ LIVE Next.js
├── packages/shared/
├── services/agent/        # LangGraph worker
├── supabase/migrations/
├── scripts/               # seed, stripe, supabase, vercel env sync
├── web/, backend/         # legacy
└── CHATGPT_PROJECT_BRIEF.md / this brief
```

### Key routes (today)
Marketing: `/`, `/pricing`, `/privacy`, `/terms`, `/login`, `/signup`  
App: onboarding, `/dashboard`, `/jobs`, `/queue`, `/tracker`, `/activity`, `/pathways`, `/profile`, `/settings`  
APIs: billing, stripe webhook, `tailoring/prepare`, discovery, pathways, applications, waitlist, auth

### Domain concepts already in product
NOC 2021, TEER, Express Entry/PNP/AIP pathway fit, permit filters, ATS/match scores, review queue, PIPEDA export/delete RPCs.  
**Twin direction:** treat these as **constraint/opportunity modules** inside Twin — not the whole company identity.

### Infra notes
- Supabase ref (known): `nvsxswvdktnphktrrxlg`  
- `NEXT_PUBLIC_APP_URL=https://career-os-daxds.vercel.app`  
- Re-alias if needed: `npx vercel alias set <url> career-os-daxds.vercel.app`  
- Scripts: `npm run dev|build|seed:demo-data|setup:supabase|setup:stripe|sync:vercel-secrets`  
- Gotcha: Windows `echo | vercel env add` corrupts secrets → use `scripts/vercel-env-sync.mjs`  
- Deployment Protection can block public URL  

### Design tokens (current landing)
Dark charcoal ~`#0b0f14`, teal ~`#2dd4bf`, Fraunces + DM Sans, brand `◆ Career OS`.

### Gap: code vs Twin product
Much of the Twin ritual (Sunday Brief, Twin mirror, Evidence Gaps as home IA, Outcome Graph) is **designed** but **not fully built**. Existing app is closer to Canada job-match + tailor + queue + Stripe. ChatGPT should help **migrate the product toward Twin** without rewriting the whole stack unless asked.

---

## PART 4 — Prior strategy conclusion (for context only; do not re-litigate)

IC passed on “AI apply / resume SaaS as the company.” Niche Canada apply tools can make money but are not decade-defining. Investable path = Professional Twin + Career OS ritual. Immigration intelligence = high-value **module** for mobile professionals, not the prison of the brand.

Cursor canvases (if useful to the human; ChatGPT may not see them):
- `canvases/ic-memo-professional-os.canvas.tsx` — IC memo  
- `canvases/twin-first-product-design.canvas.tsx` — first product design  
- `canvases/career-os-strategy-brief.canvas.tsx` — earlier strategy brief  

---

## PART 5 — One-line summary

**Career OS is the first product on a Professional Twin platform:** a Sunday decision ritual and long-term career memory for ambitious professionals, implemented today as a Next.js + Supabase + Claude + Stripe app at https://career-os-daxds.vercel.app — evolving from Canada job scoring/tailoring toward Twin-native home, brief, evidence, and outcomes.

**End of briefing.**
