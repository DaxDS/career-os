import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ApiError,
  api,
  type InterviewFeedback,
  type InterviewQuestionSet,
} from "../api/client";
import "../styles/review.css";

interface EligibleApplication {
  jobId: string;
  jobTitle: string;
  company: string;
  status: string;
}

const FOCUS_LABELS: Record<string, string> = {
  behavioral: "Behavioral",
  technical: "Technical",
  role_fit: "Role fit",
};

export function InterviewPrepPage() {
  const [applications, setApplications] = useState<EligibleApplication[]>([]);
  const [selectedJobId, setSelectedJobId] = useState("");
  const [questionSet, setQuestionSet] = useState<InterviewQuestionSet | null>(null);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [feedback, setFeedback] = useState<Record<number, InterviewFeedback>>({});
  const [coachingIndex, setCoachingIndex] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [proRequired, setProRequired] = useState(false);

  const loadApplications = useCallback(async () => {
    setLoading(true);
    try {
      const [approved, submitted] = await Promise.all([
        api.listApplications("approved"),
        api.listApplications("submitted"),
      ]);
      const rows = [...approved, ...submitted].map((row) => ({
        jobId: row.application.job_id,
        jobTitle: row.job_title,
        company: row.company,
        status: row.application.status,
      }));
      setApplications(rows);
      if (rows.length > 0) {
        setSelectedJobId((current) => current || rows[0].jobId);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load applications");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadApplications();
  }, [loadApplications]);

  function handleFailure(err: unknown, fallback: string) {
    if (err instanceof ApiError && err.status === 402) {
      setProRequired(true);
      setError("");
      return;
    }
    setError(err instanceof ApiError ? err.message : fallback);
  }

  async function handleGenerate() {
    if (!selectedJobId) return;
    setError("");
    setProRequired(false);
    setQuestionSet(null);
    setAnswers({});
    setFeedback({});
    setGenerating(true);
    try {
      setQuestionSet(await api.interviewQuestions(selectedJobId));
    } catch (err) {
      handleFailure(err, "Failed to generate questions");
    } finally {
      setGenerating(false);
    }
  }

  async function handleCoach(index: number, question: string) {
    const answer = (answers[index] || "").trim();
    if (!answer) return;
    setError("");
    setCoachingIndex(index);
    try {
      const result = await api.coachInterviewAnswer(selectedJobId, question, answer);
      setFeedback((prev) => ({ ...prev, [index]: result }));
    } catch (err) {
      handleFailure(err, "Failed to get feedback");
    } finally {
      setCoachingIndex(null);
    }
  }

  return (
    <>
      <header className="page-header">
        <h1>Interview prep</h1>
        <p>
          Practice for jobs you have applied to. Career OS generates likely questions from the job
          description and your tailored resume, then coaches your answers.
        </p>
      </header>

      {error && <div className="error-banner">{error}</div>}
      {proRequired && (
        <div className="error-banner">
          Interview prep is a Pro feature. <Link to="/app/plan">Upgrade your plan</Link> to unlock
          it.
        </div>
      )}

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        {loading ? (
          <p className="muted">Loading your applications…</p>
        ) : applications.length === 0 ? (
          <p className="muted">
            No approved or submitted applications yet. Approve a job in the{" "}
            <Link to="/app/review">review queue</Link> first — interview prep unlocks once an
            application is approved or submitted.
          </p>
        ) : (
          <>
            <div className="field">
              <label className="label" htmlFor="prep-job">
                Application
              </label>
              <select
                id="prep-job"
                className="select"
                value={selectedJobId}
                onChange={(e) => setSelectedJobId(e.target.value)}
              >
                {applications.map((a) => (
                  <option key={a.jobId} value={a.jobId}>
                    {a.jobTitle} — {a.company} ({a.status})
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => void handleGenerate()}
              disabled={generating || !selectedJobId}
            >
              {generating ? "Generating questions…" : "Generate interview questions"}
            </button>
          </>
        )}
      </div>

      {questionSet && (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>
            {questionSet.job_title} — {questionSet.company}
          </h2>
          {questionSet.questions.map((q, i) => (
            <div key={i} className="preview-block" style={{ marginBottom: "1rem" }}>
              <p style={{ marginTop: 0 }}>
                <strong>
                  {i + 1}. {q.question}
                </strong>{" "}
                <span className="badge">{FOCUS_LABELS[q.focus] ?? q.focus}</span>
              </p>
              {q.why && <p className="muted">{q.why}</p>}
              <textarea
                className="textarea"
                rows={4}
                placeholder="Type your practice answer…"
                value={answers[i] || ""}
                onChange={(e) => setAnswers((prev) => ({ ...prev, [i]: e.target.value }))}
              />
              <button
                type="button"
                className="btn"
                style={{ marginTop: "0.5rem" }}
                onClick={() => void handleCoach(i, q.question)}
                disabled={coachingIndex === i || !(answers[i] || "").trim()}
              >
                {coachingIndex === i ? "Coaching…" : "Get AI feedback"}
              </button>

              {feedback[i] && (
                <div style={{ marginTop: "0.75rem" }}>
                  <div className="score-panel">
                    <div className="score-pill score-pill-primary">
                      <strong>{feedback[i].score}%</strong>
                      <span>Answer score</span>
                    </div>
                  </div>
                  {feedback[i].strengths.length > 0 && (
                    <>
                      <h4 style={{ marginBottom: "0.25rem" }}>What worked</h4>
                      <ul style={{ marginTop: 0 }}>
                        {feedback[i].strengths.map((s, j) => (
                          <li key={j}>{s}</li>
                        ))}
                      </ul>
                    </>
                  )}
                  {feedback[i].improvements.length > 0 && (
                    <>
                      <h4 style={{ marginBottom: "0.25rem" }}>To improve</h4>
                      <ul style={{ marginTop: 0 }}>
                        {feedback[i].improvements.map((s, j) => (
                          <li key={j}>{s}</li>
                        ))}
                      </ul>
                    </>
                  )}
                  {feedback[i].suggested_answer && (
                    <>
                      <h4 style={{ marginBottom: "0.25rem" }}>Stronger version</h4>
                      <div className="preview-block">
                        <pre>{feedback[i].suggested_answer}</pre>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
