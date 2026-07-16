# CareerOS

AI job-search copilot built for the **Canadian job market** — NOC 2021 + TEER as first-class data, immigration-pathway intelligence, and human-in-the-loop review.

## Monorepo structure

```
career-os/
├── apps/
│   └── web/                    # Next.js 14 (App Router), Supabase Auth, next-intl
├── services/
│   └── agent/                  # Python FastAPI + LangGraph worker
│       ├── graphs/             # discovery, noc_classify, matching, pathways, tailoring, dispatch
│       ├── parsers/            # jd_parser, resume_parser, eligibility
│       ├── scrapers/           # jobbank.py
│       ├── templates/          # Jinja2 Canadian resume HTML
│       └── data/               # noc_2021, teer_rules, ee_categories, pnp_streams, wage_data
├── packages/
│   └── shared/                 # Shared TypeScript types
└── supabase/
    ├── config.toml
    └── migrations/             # Schema + RLS + PIPEDA RPCs
```

## Phase 1 setup

### 1. Supabase (ca-central-1)

1. Create a Supabase project in **Canada (Central)** region.
2. Enable Email and Google auth providers.
3. Add Google OAuth credentials in Supabase dashboard.
4. Install [Supabase CLI](https://supabase.com/docs/guides/cli) and run:

```bash
supabase link --project-ref YOUR_PROJECT_REF
supabase db push
```

Or apply `supabase/migrations/20250705000001_initial_schema.sql` manually in the SQL editor.

### 2. Environment

```bash
cp .env.example .env.local   # apps/web — copy vars into apps/web/.env.local
cp .env.example .env         # services/agent
```

Fill in placeholders (see `.env.example`). **Do not commit secrets.**

### 3. Web app

```bash
npm install
npm run dev
```

Open http://localhost:3000

### 4. Agent worker (optional in Phase 1)

```bash
cd services/agent
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -e .
uvicorn main:app --reload --port 8000
```

## Onboarding flow

1. Sign up (email or Google)
2. Upload resume → work history → NOC mapping → permit status → languages
3. Redirect to dashboard

Resume parsing and NOC suggestions connect in **Phase 2** via the agent worker.

## Data files

| File | Purpose |
|------|---------|
| `noc_2021.json` | StatCan NOC hierarchy (20 sample unit groups; replace with full dataset) |
| `teer_rules.json` | TEER 0–5 definitions + EE eligibility |
| `ee_categories.json` | Express Entry category-based draw NOC lists |
| `pnp_streams.json` | PNP in-demand lists by province |
| `wage_data.json` | Job Bank median wages by NOC + region |

Each file includes `source_url` and `last_verified` for easy updates without deploys.

## PIPEDA

- `data_export()` RPC — export all user data as JSON
- `delete_user_account()` RPC — cascade delete + storage cleanup
- Privacy page at `/privacy`

## Current phase

**Phase 4 — Monetization + Polish** ✓

- Stripe checkout + webhook → `profiles.plan_tier`
- Free vs Pro ($24 CAD/mo) limits enforced in agent
- Polished landing, pricing, PIPEDA privacy + terms, waitlist
- Activity log transparency page, billing settings

**Post-launch (Phase 5):** French UI, career-page scrapers, browser extension, CLB integration, B2B2C partnerships.
