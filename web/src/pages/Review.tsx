import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, api, type ReviewDetail, type ReviewQueueItem } from "../api/client";
import "../styles/review.css";

function ReviewDemoCard() {
  return (
    <div className="review-demo-card" aria-hidden="true">
      <div className="review-demo-lock">Sample preview</div>
      <div className="review-demo-content">
        <strong>Senior AI Engineer</strong>
        <span className="muted">Bell Canada · ON</span>
        <span className="badge">87% match · ATS ✓</span>
        <div className="review-demo-snippet">
          <h4>Tailored resume</h4>
          <p>
            Led ML pipeline optimization reducing inference latency by 40%. Experienced with PyTorch,
            LLM fine-tuning, and production deployment…
          </p>
          <h4>Cover letter</h4>
          <p>
            Dear Hiring Manager, I am excited to apply for the Senior AI Engineer role at Bell Canada.
            My background in scalable ML systems aligns closely with your team&apos;s focus…
          </p>
        </div>
      </div>
      <p className="review-demo-cta">
        <Link to="/app/jobs">Run the pipeline on a job to see your first result.</Link>
      </p>
    </div>
  );
}

export function ReviewPage() {
  const [queue, setQueue] = useState<ReviewQueueItem[]>([]);
  const [selected, setSelected] = useState<ReviewDetail | null>(null);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  function refresh() {
    void api.reviewQueue().then(setQueue);
  }

  useEffect(() => {
    refresh();
  }, []);

  async function openDetail(jobId: string) {
    setError("");
    try {
      const detail = await api.reviewDetail(jobId);
      setSelected(detail);
      setNotes("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load details");
    }
  }

  async function decide(decision: string) {
    if (!selected) return;
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      await api.reviewDecide(selected.job_id, decision, notes);
      setSelected(null);
      refresh();
      if (decision === "approve") {
        setSuccess("Approved — go to Apply to submit this job.");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <header className="page-header">
        <h1>Review queue</h1>
        <p>Approve, reject, or request revisions before anything goes out.</p>
      </header>

      {error && <div className="error-banner">{error}</div>}
      {success && <div className="success-banner">{success}</div>}

      <div className="review-layout">
        <div className="card review-list">
          <h2 style={{ marginTop: 0 }}>Pending ({queue.length})</h2>
          {queue.length === 0 ? (
            <ReviewDemoCard />
          ) : (
            <ul className="queue-list">
              {queue.map((item) => (
                <li key={item.job_id}>
                  <button
                    type="button"
                    className={selected?.job_id === item.job_id ? "queue-item active" : "queue-item"}
                    onClick={() => void openDetail(item.job_id)}
                  >
                    <strong>{item.title}</strong>
                    <span>{item.company}</span>
                    <div className="score-row">
                      {item.overall_score != null && item.overall_score > 0 ? (
                        <span className="badge">{item.overall_score}% overall</span>
                      ) : (
                        <span className="badge badge-muted">Score unavailable</span>
                      )}
                      {item.immigration_score != null && (
                        <span className="badge badge-immigration" title="Express Entry / PR pathway fit">
                          🇨🇦 {item.immigration_score}% PR fit
                        </span>
                      )}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {selected && (
          <div className="card review-detail">
            <h2 style={{ marginTop: 0 }}>
              {selected.title} · {selected.company}
            </h2>
            {selected.overall_score == null || selected.overall_score === 0 ? (
              <p className="muted">Score unavailable — job description was missing when scored.</p>
            ) : (
              <div className="score-panel">
                <div className="score-pill score-pill-primary">
                  <strong>{selected.overall_score}%</strong>
                  <span>Overall fit</span>
                </div>
                <div className="score-pill">
                  <strong>{selected.match_score ?? "—"}%</strong>
                  <span>Role match</span>
                </div>
                <div className="score-pill">
                  <strong>{selected.ats_score ?? "—"}%</strong>
                  <span>ATS score</span>
                </div>
                {selected.immigration_score != null && (
                  <div className="score-pill score-pill-immigration">
                    <strong>{selected.immigration_score}%</strong>
                    <span>🇨🇦 PR / Express Entry fit</span>
                  </div>
                )}
              </div>
            )}

            <div className="preview-block">
              <h3>Tailored resume summary</h3>
              <p>{selected.document_previews.resume_summary || "Not generated yet."}</p>
            </div>
            <div className="preview-block">
              <h3>Cover letter</h3>
              <p>{selected.document_previews.cover_letter_excerpt || "Not generated yet."}</p>
            </div>
            {selected.document_previews.email_subject && (
              <div className="preview-block">
                <h3>Recruiter email</h3>
                <p>
                  <strong>Subject:</strong> {selected.document_previews.email_subject}
                </p>
              </div>
            )}
            <div className="preview-block">
              <h3>ATS fact-check</h3>
              <p>
                {selected.document_previews.fact_check_passed === true
                  ? "✅ Tailored resume verified against your master resume — no fabricated claims detected."
                  : selected.document_previews.fact_check_passed === false
                    ? "⚠️ Fact-check flagged possible discrepancies — review the tailored resume carefully."
                    : "Fact-check pending."}
              </p>
            </div>
            <div className="field">
              <label className="label">Notes (optional)</label>
              <textarea className="textarea" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
            </div>
            <div className="row-actions">
              <button type="button" className="btn btn-primary" disabled={loading} onClick={() => void decide("approve")}>
                Approve
              </button>
              <button type="button" className="btn btn-secondary" disabled={loading} onClick={() => void decide("request_revision")}>
                Request revision
              </button>
              <button type="button" className="btn btn-ghost" disabled={loading} onClick={() => void decide("reject")}>
                Reject
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
