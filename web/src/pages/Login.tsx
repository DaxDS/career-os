import { FormEvent, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { DEV_EMAIL, DEV_PASSWORD } from "../dev-credentials";
import { useAuth } from "../context/AuthContext";
import "../styles/auth.css";

export function LoginPage() {
  const { login, token, skipAuth, isLoading } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState(DEV_EMAIL);
  const [password, setPassword] = useState(DEV_PASSWORD);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (!isLoading && (token || skipAuth)) return <Navigate to="/app" replace />;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/app");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sign in failed");
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
        <h1>Welcome back</h1>
        <p className="muted">Sign in to manage your job search pipeline.</p>
        <div className="error-banner" style={{ background: "#fef9c3", color: "#713f12", borderColor: "#fde047" }}>
          <strong>Demo account</strong>
          <br />
          {DEV_EMAIL} / {DEV_PASSWORD}
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
              autoComplete="current-password"
              required
            />
          </div>
          <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className="auth-footer muted">
          <Link to="/register">Create account</Link>
          {" · "}
          <Link to="/">← Back to home</Link>
        </p>
      </div>
    </div>
  );
}
