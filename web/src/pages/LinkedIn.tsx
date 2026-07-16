import { FormEvent, useState } from "react";
import { ApiError, api, RESUME_TYPES, type LinkedInOptimization } from "../api/client";
import "../styles/review.css";

export function LinkedInPage() {
  const [headline, setHeadline] = useState("");
  const [about, setAbout] = useState("");
  const [targetRole, setTargetRole] = useState<string>(RESUME_TYPES[0].id);
  const [result, setResult] = useState<LinkedInOptimization | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleOptimize(e: FormEvent) {
    e.preventDefault();
    setError("");
    setResult(null);
    setLoading(true);
    try {
      setResult(await api.optimizeLinkedIn(headline, about, targetRole));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Optimization failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <header className="page-header">
        <h1>LinkedIn optimizer</h1>
        <p>
          Paste your LinkedIn headline and About section — Career OS scores keyword fit for your
          target role and suggests rewrites. Nothing is scraped; copy it in yourself.
        </p>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <form onSubmit={(e) => void handleOptimize(e)}>
          <div className="field">
            <label className="label" htmlFor="li-headline">
              Headline
            </label>
            <input
              id="li-headline"
              className="input"
              value={headline}
              onChange={(e) => setHeadline(e.target.value)}
              placeholder="e.g. Software Developer | Python | Toronto"
              maxLength={500}
            />
          </div>
          <div className="field">
            <label className="label" htmlFor="li-about">
              About section
            </label>
            <textarea
              id="li-about"
              className="textarea"
              rows={8}
              value={about}
              onChange={(e) => setAbout(e.target.value)}
              placeholder="Paste your LinkedIn About section here…"
              maxLength={10000}
            />
          </div>
          <div className="field">
            <label className="label" htmlFor="li-role">
              Target role family
            </label>
            <select
              id="li-role"
              className="select"
              value={targetRole}
              onChange={(e) => setTargetRole(e.target.value)}
            >
              {RESUME_TYPES.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? "Analyzing…" : "Optimize my profile"}
          </button>
        </form>
      </div>

      {result && (
        <div className="card">
          <div className="score-panel">
            <div className="score-pill score-pill-primary">
              <strong>{result.keyword_score}%</strong>
              <span>Keyword fit</span>
            </div>
            <div className="score-pill">
              <strong>{result.missing_keywords.length}</strong>
              <span>Missing keywords</span>
            </div>
            <div className="score-pill">
              <strong>{result.suggestions.length}</strong>
              <span>Suggested fixes</span>
            </div>
          </div>

          {result.missing_keywords.length > 0 && (
            <p className="muted" style={{ marginTop: 0 }}>
              Recruiters search for: {result.missing_keywords.join(", ")}
            </p>
          )}

          <h3>Headline</h3>
          <div className="preview-block">
            <pre>Before: {headline || "(empty)"}</pre>
          </div>
          <div className="preview-block">
            <pre>After: {result.headline_rewrite}</pre>
          </div>

          <h3>About</h3>
          <div className="preview-block">
            <pre>Before: {about || "(empty)"}</pre>
          </div>
          <div className="preview-block">
            <pre>After: {result.about_rewrite}</pre>
          </div>

          {result.suggestions.length > 0 && (
            <>
              <h3>Why these changes</h3>
              <ul>
                {result.suggestions.map((s, i) => (
                  <li key={i} style={{ marginBottom: "0.5rem" }}>
                    <strong style={{ textTransform: "capitalize" }}>{s.section}</strong>: {s.issue}{" "}
                    <span className="muted">— {s.fix}</span>
                  </li>
                ))}
              </ul>
            </>
          )}

          <p className="muted">
            Copy the rewrites into LinkedIn yourself — Career OS never edits your profile for you.
          </p>
        </div>
      )}
    </>
  );
}
