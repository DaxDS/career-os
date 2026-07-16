import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, api, type JobPosting } from "../api/client";

export function JobsPage() {
  const [jobs, setJobs] = useState<JobPosting[]>([]);
  const [importUrl, setImportUrl] = useState("");
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [url, setUrl] = useState("");
  const [description, setDescription] = useState("");
  const [province, setProvince] = useState("ON");
  const [error, setError] = useState("");
  const [limitReached, setLimitReached] = useState(false);
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const [parsing, setParsing] = useState(false);

  function refresh() {
    void api.listJobs().then(setJobs);
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleImportUrl(e: FormEvent) {
    e.preventDefault();
    if (!importUrl.trim()) return;
    setError("");
    setSuccess("");
    setParsing(true);
    try {
      const parsed = await api.parseJobUrl(importUrl.trim());
      setTitle(parsed.title);
      setCompany(parsed.company);
      setUrl(parsed.source_url);
      setDescription(parsed.description);
      if (parsed.location_province) setProvince(parsed.location_province);
      setSuccess("Job details loaded — review and add below.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not parse URL");
    } finally {
      setParsing(false);
    }
  }

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLimitReached(false);
    setSuccess("");
    setLoading(true);
    try {
      const result = await api.importJob({
        title,
        company,
        source_url: url,
        description,
        location_province: province,
      });
      setSuccess(result.created ? "Job added to your pipeline." : "Job already exists (duplicate).");
      setTitle("");
      setCompany("");
      setUrl("");
      setDescription("");
      setImportUrl("");
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not add job");
      setLimitReached(err instanceof ApiError && err.status === 402);
    } finally {
      setLoading(false);
    }
  }

  async function runPipeline(jobId: string) {
    setError("");
    setLimitReached(false);
    try {
      await api.runJobPipeline(jobId);
      setSuccess("Pipeline started for this job. Check Review in a few minutes.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Pipeline failed");
      setLimitReached(err instanceof ApiError && err.status === 402);
    }
  }

  return (
    <>
      <header className="page-header">
        <h1>Jobs</h1>
        <p>Add postings you want to pursue. Career OS scores fit and prepares application packages.</p>
      </header>

      <div className="card" style={{ marginBottom: "2rem" }}>
        <h2 style={{ marginTop: 0 }}>Add a job</h2>
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
        {success && <div className="success-banner">{success}</div>}

        <form onSubmit={(e) => void handleImportUrl(e)} style={{ marginBottom: "1.5rem" }}>
          <div className="field">
            <label className="label">Import from URL</label>
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
              <input
                className="input"
                type="url"
                value={importUrl}
                onChange={(e) => setImportUrl(e.target.value)}
                placeholder="LinkedIn, Indeed, or Job Bank Canada URL…"
                style={{ flex: "1 1 240px" }}
              />
              <button type="submit" className="btn btn-secondary" disabled={parsing || !importUrl.trim()}>
                {parsing ? "Parsing…" : "Import"}
              </button>
            </div>
          </div>
        </form>

        <form onSubmit={(e) => void handleAdd(e)}>
          <div className="field">
            <label className="label">Job title</label>
            <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} required />
          </div>
          <div className="field">
            <label className="label">Company</label>
            <input className="input" value={company} onChange={(e) => setCompany(e.target.value)} required />
          </div>
          <div className="field">
            <label className="label">Posting URL (optional)</label>
            <input className="input" type="url" value={url} onChange={(e) => setUrl(e.target.value)} />
          </div>
          <div className="field">
            <label className="label">Province</label>
            <select className="select" value={province} onChange={(e) => setProvince(e.target.value)}>
              {["ON", "BC", "AB", "QC", "MB", "SK", "NS", "NB", "NL", "PE", "NT", "YT", "NU"].map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label className="label">Description</label>
            <textarea
              className="textarea"
              rows={6}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Paste the full job description here…"
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? "Adding…" : "Add job"}
          </button>
        </form>
      </div>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Your jobs</h2>
        {jobs.length === 0 ? (
          <p className="muted">No jobs yet. Add your first posting above.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Role</th>
                <th>Company</th>
                <th>Score track</th>
                <th>PR fit</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.id}>
                  <td>
                    <strong>{j.title}</strong>
                    <br />
                    <span className="muted">{j.location_province}</span>
                  </td>
                  <td>{j.company}</td>
                  <td>{j.role_family ?? "—"}</td>
                  <td>
                    {j.immigration_score != null ? (
                      <span className="badge badge-immigration" title="Express Entry / PR pathway fit">
                        🇨🇦 {j.immigration_score}%
                      </span>
                    ) : (
                      <span className="muted" title="Run the AI pipeline to score this job">
                        —
                      </span>
                    )}
                  </td>
                  <td>
                    <button type="button" className="btn btn-secondary" onClick={() => void runPipeline(j.id)}>
                      Run AI pipeline
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
