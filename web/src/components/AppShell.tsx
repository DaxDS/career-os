import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Link, useLocation } from "react-router-dom";
import "../styles/app-shell.css";

type NavItem = { to: string; label: string; end?: boolean };

const NAV: NavItem[] = [
  { to: "/app", label: "Dashboard", end: true },
  { to: "/app/resumes", label: "Resumes" },
  { to: "/app/jobs", label: "Jobs" },
  { to: "/app/review", label: "Review" },
  { to: "/app/linkedin", label: "LinkedIn" },
  { to: "/app/apply", label: "Applications" },
  { to: "/app/interview", label: "Interview Prep" },
  { to: "/app/pipeline", label: "Pipeline" },
  { to: "/app/plan", label: "Plan" },
];

export function AppShell() {
  const { email, logout } = useAuth();
  const location = useLocation();

  return (
    <div className="shell">
      <aside className="sidebar">
        <Link to="/" className="brand">
          <span className="brand-mark">◆</span>
          Career OS
        </Link>
        <nav className="nav">
          {NAV.map((item) => {
            const active =
              item.end
                ? location.pathname === item.to
                : location.pathname.startsWith(item.to);
            return (
              <Link key={item.to} to={item.to} className={active ? "nav-link active" : "nav-link"}>
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-footer">
          <p className="user-email">{email}</p>
          <button type="button" className="btn btn-ghost" onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}

export function ProtectedRoute() {
  const { token, skipAuth, isLoading } = useAuth();
  if (isLoading) {
    return (
      <div className="loading-screen">
        <p>Loading Career OS…</p>
      </div>
    );
  }
  if (!token && !skipAuth) return <Navigate to="/login" replace />;
  return <AppShell />;
}
