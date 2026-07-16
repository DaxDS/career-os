import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, api, type BillingOverview } from "../api/client";
import "../styles/pricing.css";

const PLANS = [
  {
    id: "free",
    name: "Starter",
    price: 0,
    description: "Try Career OS and run your first applications.",
    features: ["5 AI pipeline runs / month", "10 jobs / month", "2 resume tracks", "Review queue"],
  },
  {
    id: "pro",
    name: "Pro",
    price: 29,
    description: "For active job seekers running daily pipelines.",
    features: [
      "50 AI pipeline runs / month",
      "100 jobs / month",
      "5 resume tracks",
      "Priority AI models",
      "Email support",
    ],
    highlighted: true,
  },
  {
    id: "team",
    name: "Career Coach",
    price: 99,
    description: "For coaches managing multiple clients.",
    features: [
      "Unlimited pipeline runs",
      "Multi-client workspace",
      "White-label reports",
      "API access",
      "Dedicated support",
    ],
  },
];

export function PricingPage({ showUsage = true }: { showUsage?: boolean }) {
  const [current, setCurrent] = useState<BillingOverview | null>(null);
  const [checkoutError, setCheckoutError] = useState("");
  const [checkoutLoading, setCheckoutLoading] = useState(false);

  useEffect(() => {
    if (!showUsage) return;
    void api.billingOverview().then(setCurrent).catch(() => undefined);
  }, [showUsage]);

  async function handleUpgrade(planId: string) {
    setCheckoutError("");
    setCheckoutLoading(true);
    try {
      const { url } = await api.createCheckoutSession(planId);
      window.location.href = url;
    } catch (err) {
      setCheckoutError(err instanceof ApiError ? err.message : "Checkout unavailable");
    } finally {
      setCheckoutLoading(false);
    }
  }

  function usagePct(used: number, limit: number) {
    if (limit <= 0) return 0;
    return Math.min(100, Math.round((used / limit) * 100));
  }

  return (
    <>
      <header className="page-header">
        <h1>Plans</h1>
        <p>Start free. Upgrade when you&apos;re ready to scale your search.</p>
      </header>

      {checkoutError && <div className="error-banner">{checkoutError}</div>}

      {current && showUsage && (
        <div className="card usage-meters" style={{ marginBottom: "1.5rem" }}>
          <h2 style={{ marginTop: 0 }}>Current plan: {current.plan_label}</h2>
          <div className="usage-meter">
            <div className="usage-meter-header">
              <span>AI pipeline runs</span>
              <span>
                {current.usage.ai_pipeline_runs} / {current.limits.ai_pipeline_runs}
              </span>
            </div>
            <div className="usage-bar">
              <div
                className="usage-bar-fill"
                style={{ width: `${usagePct(current.usage.ai_pipeline_runs, current.limits.ai_pipeline_runs)}%` }}
              />
            </div>
          </div>
          <div className="usage-meter">
            <div className="usage-meter-header">
              <span>Jobs imported</span>
              <span>
                {current.usage.jobs_this_month} / {current.limits.jobs_per_month}
              </span>
            </div>
            <div className="usage-bar">
              <div
                className="usage-bar-fill"
                style={{ width: `${usagePct(current.usage.jobs_this_month, current.limits.jobs_per_month)}%` }}
              />
            </div>
          </div>
          <div className="usage-meter">
            <div className="usage-meter-header">
              <span>Resume tracks</span>
              <span>
                {current.usage.resumes} / {current.limits.resume_slots}
              </span>
            </div>
            <div className="usage-bar">
              <div
                className="usage-bar-fill"
                style={{ width: `${usagePct(current.usage.resumes, current.limits.resume_slots)}%` }}
              />
            </div>
          </div>
        </div>
      )}

      <div className="pricing-grid">
        {PLANS.map((plan) => (
          <div
            key={plan.id}
            className={plan.highlighted ? "pricing-card card highlighted" : "pricing-card card"}
          >
            {plan.highlighted && <span className="pricing-badge">Most popular</span>}
            <h2>{plan.name}</h2>
            <p className="pricing-price">
              {plan.price === 0 ? (
                "Free"
              ) : (
                <>
                  ${plan.price}
                  <span>/mo CAD</span>
                </>
              )}
            </p>
            <p className="muted">{plan.description}</p>
            <ul>
              {plan.features.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
            {current?.plan === plan.id ? (
              <span className="btn btn-secondary btn-block current-plan">Current plan</span>
            ) : plan.id === "free" ? (
              <Link to="/app" className="btn btn-secondary btn-block">
                Included
              </Link>
            ) : (
              <button
                type="button"
                className="btn btn-primary btn-block"
                disabled={checkoutLoading}
                onClick={() => void handleUpgrade(plan.id)}
              >
                {checkoutLoading ? "Redirecting…" : `Upgrade to ${plan.name}`}
              </button>
            )}
          </div>
        ))}
      </div>

      <p className="muted pricing-note">
        Pro upgrades use Stripe checkout. Set STRIPE_SECRET_KEY and STRIPE_PRICE_PRO in backend .env.
      </p>
    </>
  );
}

export function PublicPricingPage() {
  return (
    <div className="landing">
      <header className="landing-header">
        <Link to="/" className="brand">
          <span className="brand-mark">◆</span> Career OS
        </Link>
        <nav>
          <Link to="/login" className="btn btn-primary">
            Get started
          </Link>
        </nav>
      </header>
      <div style={{ maxWidth: 1000, margin: "0 auto", padding: "2rem" }}>
        <PricingPage showUsage={false} />
      </div>
    </div>
  );
}
