import { FormEvent, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { DEV_EMAIL, DEV_PASSWORD } from "../dev-credentials";
import "../styles/auth.css";

export function RegisterPage() {
  const { register, token } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState(DEV_EMAIL);
  const [password, setPassword] = useState(DEV_PASSWORD);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (token) return <Navigate to="/app" replace />;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register(email, password);
      navigate("/app");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create account");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card card">
        <Link to="/" className="brand">
          <span className="brand-mark">◆</span> Career OS
        </Link>
        <h1>Create account</h1>
        <p className="muted">Start your AI job search pipeline in minutes.</p>
        <div className="error-banner" style={{ background: "#fef9c3", color: "#713f12", borderColor: "#fde047" }}>
          <strong>Demo account (prefilled)</strong>
          <br />
          {DEV_EMAIL} / {DEV_PASSWORD}
          <br />
          <span className="muted" style={{ fontSize: "0.85em" }}>
            In single-user mode only one account can exist — use Sign in if this email is already registered.
          </span>
        </div>
        {error && <div className="error-banner">{error}</div>}
        <form onSubmit={(e) => void handleSubmit(e)}>
          <div className="field">
            <label className="label" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              className="input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
              required
            />
          </div>
          <div className="field">
            <label className="label" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              minLength={8}
              required
            />
          </div>
          <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
            {loading ? "Creating account…" : "Create account"}
          </button>
        </form>
        <p className="auth-footer muted">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
