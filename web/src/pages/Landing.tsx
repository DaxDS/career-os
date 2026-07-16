import { Link } from "react-router-dom";
import { FeatureComparison } from "../components/FeatureComparison";
import "../styles/landing.css";
import "../styles/comparison.css";

export function LandingPage() {
  return (
    <div className="landing">
      <header className="landing-header">
        <Link to="/" className="brand">
          <span className="brand-mark">◆</span> Career OS
        </Link>
        <nav>
          <Link to="/pricing">Pricing</Link>
          <Link to="/login" className="btn btn-secondary">
            Sign in
          </Link>
          <Link to="/register" className="btn btn-primary">
            Get started
          </Link>
        </nav>
      </header>

      <section className="hero">
        <p className="eyebrow">AI Career Operating System</p>
        <h1>The only job platform that scores every posting for your Express Entry pathway.</h1>
        <p className="hero-sub">
          AI pipeline that tailors your resume, writes your cover letter, and auto-submits — with
          Canadian PR/NOC scoring on every job.
        </p>
        <p className="social-proof">
          The only tool that does quality-tailored autonomous apply, not volume spam.
        </p>
        <div className="hero-cta">
          <Link to="/register" className="btn btn-primary btn-lg">
            Start free
          </Link>
          <Link to="/pricing" className="btn btn-secondary btn-lg">
            View plans
          </Link>
        </div>
      </section>

      <section className="score-demo" aria-label="Example of Career OS job scoring">
        <div className="score-demo-card">
          <div className="score-demo-header">
            <div>
              <strong>Senior AI Engineer</strong>
              <span className="score-demo-meta">Bell Canada · Toronto, ON</span>
            </div>
            <span className="badge badge-immigration score-demo-pr" title="Express Entry / PR pathway fit">
              🇨🇦 92% PR fit
            </span>
          </div>
          <div className="score-demo-scores">
            <div className="score-demo-pill">
              <strong>87%</strong>
              <span>Overall match</span>
            </div>
            <div className="score-demo-pill">
              <strong>84%</strong>
              <span>ATS score</span>
            </div>
            <div className="score-demo-pill score-demo-pill-accent">
              <strong>NOC 21231</strong>
              <span>Express Entry eligible</span>
            </div>
          </div>
          <p className="score-demo-caption">
            Every imported job is scored like this — PR pathway fit, NOC code, and ATS match —
            before a single document is generated.
          </p>
        </div>
      </section>

      <FeatureComparison />

      <section className="features">
        <div className="feature card">
          <h3>Smart job pipeline</h3>
          <p>Import postings, score immigration fit, ATS match, and role alignment automatically.</p>
        </div>
        <div className="feature card">
          <h3>AI document studio</h3>
          <p>Tailored resumes, cover letters, and recruiter emails from your master profiles.</p>
        </div>
        <div className="feature card">
          <h3>Human-in-the-loop</h3>
          <p>Nothing submits without your approval. Review, revise, then apply with confidence.</p>
        </div>
      </section>

      <footer className="landing-footer">
        <p>© {new Date().getFullYear()} Career OS · Built for ambitious job seekers</p>
      </footer>
    </div>
  );
}
