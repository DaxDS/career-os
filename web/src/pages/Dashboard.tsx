import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type BillingOverview, type ReviewStats } from "../api/client";
import "../styles/checklist.css";

export function DashboardPage() {
  const [stats, setStats] = useState<ReviewStats | null>(null);
  const [billing, setBilling] = useState<BillingOverview | null>(null);
  const [aiOk, setAiOk] = useState(true);
  const [jobsCount, setJobsCount] = useState<number | null>(null);
  const [submittedCount, setSubmittedCount] = useState<number | null>(null);

  useEffect(() => {
    void Promise.all([api.reviewStats(), api.billingOverview(), api.aiStatus()]).then(
      ([s, b, ai]) => {
        setStats(s);
        setBilling(b);
        setAiOk(ai.ai_enabled && Object.values(ai.providers).every(Boolean));
      },
    );
    void api.listJobs().then((jobs) => setJobsCount(jobs.length));
    void api.listApplications("submitted").then((apps) => setSubmittedCount(apps.length));
  }, []);

  return (
    <>
      <header className="page-header">
        <h1>Dashboard</h1>
        <p>Your job search command center.</p>
      </header>

      {!aiOk && (
        <div className="error-banner">
          AI providers are not fully configured. Add API keys in server settings to enable
          scoring and document generation.
        </div>
      )}

      <div className="stat-grid" style={{ marginBottom: "2rem" }}>
        <div className="stat card">
          <strong>{jobsCount ?? "—"}</strong>
          <span className="muted">Jobs tracked</span>
        </div>
        <div className="stat card">
          <strong>{stats?.pending_review ?? "—"}</strong>
          <span className="muted">Pending review</span>
        </div>
        <div className="stat card">
          <strong>{stats?.approved ?? "—"}</strong>
          <span className="muted">Approved</span>
        </div>
        <div className="stat card">
          <strong>{submittedCount ?? "—"}</strong>
          <span className="muted">Submitted</span>
        </div>
        <div className="stat card">
          <strong>{stats?.rejected ?? "—"}</strong>
          <span className="muted">Rejected</span>
        </div>
        <div className="stat card">
          <strong>{billing?.usage.resumes ?? "—"}</strong>
          <span className="muted">Resumes</span>
        </div>
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ marginTop: 0 }}>Quick start</h2>
        <ol className="checklist">
          <li>
            <Link to="/app/resumes">Upload your master resumes</Link> — one per career track
          </li>
          <li>
            <Link to="/app/jobs">Add job postings</Link> — paste title, company, and description
          </li>
          <li>
            <Link to="/app/pipeline">Run the pipeline</Link> — AI scores and generates documents
          </li>
          <li>
            <Link to="/app/review">Review & approve</Link> — you stay in control
          </li>
          <li>
            <Link to="/app/apply">Apply</Link> — submit approved applications, tracked automatically
          </li>
        </ol>
      </div>

      {billing && (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>
            {billing.plan_label} plan
            {billing.upgrade_available && (
              <Link to="/app/pricing" className="badge" style={{ marginLeft: "0.75rem" }}>
                Upgrade
              </Link>
            )}
          </h2>
          <p className="muted">
            {billing.usage.ai_pipeline_runs} / {billing.limits.ai_pipeline_runs} AI pipeline runs
            this month · {billing.usage.jobs_this_month} / {billing.limits.jobs_per_month} jobs
          </p>
        </div>
      )}
    </>
  );
}
