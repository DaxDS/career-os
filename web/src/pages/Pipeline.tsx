import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, api, type PipelineRun } from "../api/client";
import "../styles/pipeline.css";

function formatRunResult(run: PipelineRun): string {
  const s = run.summary;
  const ready = s.applications_ready_for_review ?? 0;
  const imported = s.jobs_imported_created ?? 0;
  const analyzed = s.jobs_analyzed ?? 0;
  if (run.status === "failed") return run.error_message || "Pipeline failed.";
  if (ready > 0) return `${ready} application(s) ready — check Review.`;
  if (imported > 0 && analyzed === 0) return `${imported} job(s) imported — scoring in progress or skipped.`;
  if (imported === 0 && (s.jobs_searched ?? 0) === 0) {
    return "Completed, but no jobs were found. Add a job under Jobs, then run pipeline on that job.";
  }
  return "Completed — no new applications in the review queue yet.";
}

export function PipelinePage() {
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [error, setError] = useState("");
  const [limitReached, setLimitReached] = useState(false);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(() => {
    void api.listPipelineRuns(10).then(setRuns).catch(() => undefined);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function runMorningPipeline() {
    setError("");
    setLimitReached(false);
    setLoading(true);
    try {
      const run = await api.runPipeline();
      setRuns((prev) => [run, ...prev.filter((r) => r.id !== run.id)]);
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Pipeline failed to start");
      setLimitReached(err instanceof ApiError && err.status === 402);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <header className="page-header">
        <h1>Pipeline</h1>
        <p>Run the full AI job search and application preparation workflow.</p>
      </header>

      {error && (
        <div className="error-banner">
          {error}
          {limitReached && (
            <>
              {" "}
              <Link to="/app/plan">Upgrade your plan →</Link>
            </>
          )}
        </div>
      )}

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Morning pipeline</h2>
        <p className="muted">
          Search → import → score → tailor resume → cover letter → recruiter email → review queue.
          Nothing is submitted automatically.
        </p>
        <p className="pipeline-tip">
          <strong>Live search:</strong> Job Bank Canada and Indeed are searched automatically using keywords
          like &quot;AI engineer&quot; and &quot;machine learning&quot;. WorkPEI and company career pages coming
          soon. Results appear under <Link to="/app/jobs">Jobs</Link>, then AI runs on each new posting.
        </p>
        <button type="button" className="btn btn-primary" disabled={loading} onClick={() => void runMorningPipeline()}>
          {loading ? "Running…" : "Run full pipeline now"}
        </button>
      </div>

      <div className="card" style={{ marginTop: "1.5rem" }}>
        <h2 style={{ marginTop: 0 }}>Recent runs</h2>
        {runs.length === 0 ? (
          <p className="muted">No pipeline runs yet. Click the button above to start one.</p>
        ) : (
          <ul className="run-list">
            {runs.map((run) => (
              <li key={run.id} className="run-item">
                <div className="run-header">
                  <span className={`run-status status-${run.status}`}>{run.status}</span>
                  <span className="muted">
                    {new Date(run.completed_at || run.created_at).toLocaleString()}
                  </span>
                </div>
                <p className="run-message">{formatRunResult(run)}</p>
                <details className="run-details">
                  <summary>Step log</summary>
                  <ul>
                    {run.step_log.map((step) => (
                      <li key={step.step}>
                        <code>{step.step}</code> — {step.status}
                        {"jobs_found" in step && step.jobs_found != null ? ` (${step.jobs_found} jobs)` : ""}
                        {"jobs_processed" in step && step.jobs_processed != null
                          ? ` (${step.jobs_processed} processed)`
                          : ""}
                        {"applications_ready" in step && step.applications_ready != null
                          ? ` (${step.applications_ready} ready)`
                          : ""}
                      </li>
                    ))}
                  </ul>
                </details>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}
