# Career OS — Product & Monetization

Career OS is a **B2C SaaS** for job seekers who want AI-assisted applications without losing control. The product surface is the **web app** at `/` — not Swagger.

---

## Value proposition

**Problem:** Applying to jobs is repetitive — tailoring resumes, writing cover letters, tracking applications — while quality suffers at volume.

**Solution:** Career OS runs an AI pipeline (score → tailor → generate → review queue). Users approve before anything is submitted.

**Differentiator:** Human-in-the-loop by design. Not auto-spam apply bots.

---

## Target customers

| Segment | Plan | Willingness to pay |
|---------|------|-------------------|
| Active job seeker (tech, AI, IT) | Pro $29/mo CAD | High — saves 10+ hrs/week |
| Casual explorer | Starter (free) | Lead gen → convert to Pro |
| Career coaches / agencies | Career Coach $99/mo | Multi-client, white-label |

---

## Revenue model

1. **Subscription (primary)** — Stripe monthly plans (Starter free, Pro, Career Coach)
2. **Usage limits (enforcement)** — AI pipeline runs, job imports, resume slots per plan
3. **Future:** Pay-per-application overage, affiliate job board integrations, coach marketplace

---

## Go-to-market (phased)

### Phase 1 — Now (V1 product)
- Web app: landing, login, dashboard, resumes, jobs, review, pricing
- Single-user deploy; you as first customer
- Manual onboarding for beta users

### Phase 2 — Monetization (V1.1)
- Stripe Checkout + webhooks
- `plan_tier` on User model
- Enforce limits in pipeline service (402 when over quota)
- Email waitlist on landing page

### Phase 3 — Scale (V2)
- Multi-tenant signup (self-serve register)
- Job board scrapers (Indeed, Job Bank Canada)
- Mobile-friendly PWA
- Referral program

---

## Pricing (CAD)

| Plan | Price | Pipeline runs/mo | Jobs/mo | Resumes |
|------|-------|------------------|---------|---------|
| Starter | Free | 5 | 10 | 2 |
| Pro | $29 | 50 | 100 | 5 |
| Career Coach | $99 | Unlimited | Unlimited | 20 |

---

## Technical product stack

| Layer | Role |
|-------|------|
| `web/` | Product UI — **primary user interface** |
| `backend/` | API + AI pipeline |
| `desktop/` | Optional Windows companion (notifications, tray) |
| `/docs` | Developer API reference only |

---

## Launch checklist

- [ ] Build web: `cd web && npm install && npm run build`
- [ ] Deploy backend + PostgreSQL (see DEPLOYMENT.md)
- [ ] Custom domain + HTTPS
- [ ] Stripe account + products
- [ ] Privacy policy + Terms of Service
- [ ] Beta users (5–10) from LinkedIn / Reddit r/OntarioJobs
