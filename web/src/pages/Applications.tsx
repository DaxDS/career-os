import { useCallback, useEffect, useState } from "react";
import { ApiError, api, type JobPosting } from "../api/client";
import "../styles/review.css";

export function ApplicationsPage() {
  const [apps, setApps] = useState<
    Awaited<ReturnType<typeof api.listApplications>>
  >([]);
  const [jobsById, setJobsById] = useState<Record<string, JobPosting>>({});
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loadingJobId, setLoadingJobId] = useState<string | null>(null);

  const refresh = useCallback(() => {
    void Promise.all([api.listApplications(), api.listJobs()]).then(([applications, jobs]) => {
      setApps(applications);
      setJobsById(Object.fromEntries(jobs.map((j) => [j.id, j])));
    });
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function apply(jobId: string, title: string) {
    const confirmed = window.confirm(
      `Submit your application for "${title}"?\n\nCareer OS will open the job site in a browser, upload your resume, fill fields, and click submit.`,
    );
    if (!confirmed) return;

    setError("");
    setSuccess("");
    setLoadingJobId(jobId);
    try {
      const result = await api.applyToJob(jobId, false);
      const detail =
        result.failure_reason ||
        (typeof result.result?.message === "string" ? result.result.message : "");

      if (result.submitted) {
        setSuccess(`Application submitted for ${title}.`);
      } else if (result.paused_for_captcha) {
        setError(`CAPTCHA on ${title}. Set BROWSER_HEADLESS=false in backend/.env, restart the API, and try again.`);
      } else if (result.status === "stopped_before_submit") {
        setSuccess(`Form filled for ${title} but final submit was skipped by server settings.`);
      } else if (result.status === "failed") {
        setError(
          detail ||
            `Could not apply to ${title}. Job Bank may be in maintenance until 7:00 a.m. Eastern, or this employer uses an external careers site.`,
        );
      } else {
        setSuccess(`Automation finished (${result.status}). ${detail}`);
      }
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not apply to this job");
    } finally {
      setLoadingJobId(null);
    }
  }

  const approved = apps.filter((a) => a.application.status === "approved");
  const submitted = apps.filter((a) => a.application.status === "submitted");

  return (
    <>
      <header className="page-header">
        <h1>Applications</h1>
        <p>Approved jobs ready to submit, and jobs you&apos;ve already applied to.</p>
      </header>

      {error && <div className="error-banner">{error}</div>}
      {success && <div className="success-banner">{success}</div>}

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ marginTop: 0 }}>Ready to apply ({approved.length})</h2>
        <p className="muted pipeline-tip">
          <strong>To make auto-apply work on Job Bank:</strong>
          <br />
          1. Create a free <strong>Job Bank Plus</strong> account at jobbank.gc.ca and upload your resume there.
          <br />
          2. Add <code>JOB_BANK_EMAIL</code> and <code>JOB_BANK_PASSWORD</code> to <code>backend/.env</code>, then restart the API.
          <br />
          3. Set <code>BROWSER_HEADLESS=false</code> so you can see the browser and complete CAPTCHA if needed.
          <br />
          4. Apply only <strong>after 7:00 a.m. Eastern</strong> — Job Bank is down for maintenance midnight–7am.
          <br />
          Bell Canada jobs may redirect to Bell&apos;s careers site — use <strong>Open posting</strong> if automation fails.
        </p>
        {approved.length === 0 ? (
          <p className="muted">No approved applications. Approve a job in Review first.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Role</th>
                <th>Company</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {approved.map((row) => (
                <tr key={row.application.id}>
                  <td>
                    <strong>{row.job_title}</strong>
                    <br />
                    <span className="muted">{row.location_province}</span>
                  </td>
                  <td>{row.company}</td>
                  <td>
                    {jobsById[row.application.job_id]?.source_url && (
                      <a
                        className="btn btn-secondary"
                        href={jobsById[row.application.job_id].source_url}
                        target="_blank"
                        rel="noreferrer"
                        style={{ marginRight: "0.5rem" }}
                      >
                        Open posting
                      </a>
                    )}
                    <button
                      type="button"
                      className="btn btn-primary"
                      disabled={loadingJobId === row.application.job_id}
                      onClick={() => void apply(row.application.job_id, row.job_title)}
                    >
                      {loadingJobId === row.application.job_id ? "Applying…" : "Apply now"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {submitted.length > 0 && (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>Submitted ({submitted.length})</h2>
          <ul className="queue-list">
            {submitted.map((row) => (
              <li key={row.application.id} className="queue-item">
                <strong>{row.job_title}</strong>
                <span>{row.company}</span>
                <span className="badge badge-approved">Submitted</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}
