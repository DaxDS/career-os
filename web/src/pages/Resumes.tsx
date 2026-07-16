import { FormEvent, useEffect, useState } from "react";
import { ApiError, RESUME_TYPES, api, type MasterResume } from "../api/client";

export function ResumesPage() {
  const [resumes, setResumes] = useState<MasterResume[]>([]);
  const [typeId, setTypeId] = useState("ai");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  function refresh() {
    void api.listResumes().then(setResumes);
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleUpload(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setError("");
    setSuccess("");
    setLoading(true);
    const type = RESUME_TYPES.find((t) => t.id === typeId)!;
    try {
      await api.uploadResume(file, type.apiLabel);
      setSuccess(`${file.name} uploaded as ${type.label}.`);
      setFile(null);
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <header className="page-header">
        <h1>Resumes</h1>
        <p>Upload one master resume per career track. AI uses these to tailor applications.</p>
      </header>

      <div className="card" style={{ marginBottom: "2rem" }}>
        <h2 style={{ marginTop: 0 }}>Upload resume</h2>
        {error && <div className="error-banner">{error}</div>}
        {success && <div className="success-banner">{success}</div>}
        <form onSubmit={(e) => void handleUpload(e)}>
          <div className="field">
            <label className="label" htmlFor="type">
              Career track
            </label>
            <select
              id="type"
              className="select"
              value={typeId}
              onChange={(e) => setTypeId(e.target.value)}
            >
              {RESUME_TYPES.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label className="label" htmlFor="file">
              PDF or Word document
            </label>
            <input
              id="file"
              type="file"
              accept=".pdf,.doc,.docx"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              required
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading || !file}>
            {loading ? "Uploading…" : "Upload resume"}
          </button>
        </form>
      </div>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Your resumes</h2>
        {resumes.length === 0 ? (
          <p className="muted">No resumes yet. Upload your first one above.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>File</th>
                <th>Track</th>
                <th>Skills preview</th>
                <th>Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {resumes.map((r) => (
                <tr key={r.id}>
                  <td>{r.original_filename}</td>
                  <td>{r.label}</td>
                  <td className="muted">
                    {(r.parsed_preview?.skills ?? []).slice(0, 5).join(", ") || "—"}
                  </td>
                  <td>{new Date(r.uploaded_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
