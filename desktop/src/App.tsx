import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ApiError,
  CareerOsApiClient,
  type HealthResponse,
  type PipelineNotification,
  type ReviewStats,
} from "./api/client";
import {
  createTauriNotifier,
  NotificationPoller,
  noopNotifier,
} from "./lib/notificationPoller";
import {
  clearLocalData,
  loadAccessToken,
  loadSettings,
  saveAccessToken,
  saveSettings,
} from "./lib/localStorage";
import {
  DEFAULT_SETTINGS,
  isValidBackendUrl,
  normalizeBackendUrl,
  type DesktopSettings,
} from "./lib/settings";

async function applyAutoStart(enabled: boolean): Promise<void> {
  if (typeof window === "undefined" || !("__TAURI_INTERNALS__" in window)) {
    return;
  }
  const { enable, disable, isEnabled } = await import("@tauri-apps/plugin-autostart");
  const currentlyEnabled = await isEnabled();
  if (enabled && !currentlyEnabled) {
    await enable();
  } else if (!enabled && currentlyEnabled) {
    await disable();
  }
}

export default function App() {
  const [settings, setSettings] = useState<DesktopSettings>(DEFAULT_SETTINGS);
  const [draft, setDraft] = useState<DesktopSettings>(DEFAULT_SETTINGS);
  const [token, setToken] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [stats, setStats] = useState<ReviewStats | null>(null);
  const [recentNotifications, setRecentNotifications] = useState<PipelineNotification[]>([]);
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [isSaving, setIsSaving] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);

  const client = useMemo(() => {
    const api = new CareerOsApiClient(settings.backendUrl, token);
    return api;
  }, [settings.backendUrl, token]);

  const clientRef = useRef(client);
  clientRef.current = client;
  const settingsRef = useRef(settings);
  settingsRef.current = settings;

  const pollerRef = useRef<NotificationPoller | null>(null);

  const refreshDashboard = useCallback(async () => {
    setError("");
    try {
      const healthResult = await client.health();
      setHealth(healthResult);
      if (token) {
        const [statsResult, notifications] = await Promise.all([
          client.reviewStats(),
          client.schedulerNotifications(false),
        ]);
        setStats(statsResult);
        setRecentNotifications(notifications.slice(0, 5));
      } else {
        setStats(null);
        setRecentNotifications([]);
      }
    } catch (err) {
      setHealth(null);
      setStats(null);
      setError(err instanceof ApiError ? err.message : "Backend unreachable");
    }
  }, [client, token]);

  useEffect(() => {
    void (async () => {
      const [loadedSettings, loadedToken] = await Promise.all([
        loadSettings(),
        loadAccessToken(),
      ]);
      setSettings(loadedSettings);
      setDraft(loadedSettings);
      setToken(loadedToken);

      const notifier = await createTauriNotifier();
      const poller = new NotificationPoller(
        () => (clientRef.current.hasAuth() ? clientRef.current : null),
        () => settingsRef.current,
        notifier,
        (items) => setRecentNotifications((prev) => [...items, ...prev].slice(0, 5)),
      );
      poller.seedSeenIds(loadedSettings.lastSeenNotificationIds);
      pollerRef.current = poller;
      poller.start();
    })();

    return () => pollerRef.current?.stop();
  }, []);

  useEffect(() => {
    client.setAccessToken(token);
    void refreshDashboard();
    const interval = setInterval(() => void refreshDashboard(), 30_000);
    return () => clearInterval(interval);
  }, [client, token, refreshDashboard]);

  useEffect(() => {
    pollerRef.current?.stop();
    pollerRef.current?.start();
  }, [settings.notificationsEnabled, settings.notificationPollSeconds, token]);

  async function handleLogin() {
    setIsConnecting(true);
    setError("");
    try {
      const result = await client.login(draft.email, password);
      setToken(result.access_token);
      await saveAccessToken(result.access_token);
      setStatusMessage("Connected to backend.");
      await refreshDashboard();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed");
    } finally {
      setIsConnecting(false);
    }
  }

  async function handleLogout() {
    setToken(null);
    setPassword("");
    await saveAccessToken(null);
    setStatusMessage("Signed out.");
    await refreshDashboard();
  }

  async function handleSaveSettings() {
    if (!isValidBackendUrl(draft.backendUrl)) {
      setError("Enter a valid http(s) backend URL.");
      return;
    }
    setIsSaving(true);
    setError("");
    try {
      const normalized: DesktopSettings = {
        ...draft,
        backendUrl: normalizeBackendUrl(draft.backendUrl),
      };
      await saveSettings(normalized);
      await applyAutoStart(normalized.autoStartEnabled);
      setSettings(normalized);
      setStatusMessage("Settings saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save settings");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleRunPipeline() {
    setError("");
    try {
      await client.triggerManualPipeline();
      setStatusMessage("Pipeline started on backend.");
      await refreshDashboard();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Pipeline request failed");
    }
  }

  async function handleClearLocalData() {
    await clearLocalData();
    setSettings(DEFAULT_SETTINGS);
    setDraft(DEFAULT_SETTINGS);
    setToken(null);
    pollerRef.current?.seedSeenIds([]);
    setStatusMessage("Local desktop data cleared.");
  }

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Career OS</h1>
          <p className="subtitle">Windows desktop shell — all logic runs on your local backend.</p>
        </div>
        <div className={`status-pill ${health ? "ok" : "down"}`}>
          {health ? `${health.app} v${health.version}` : "Backend offline"}
        </div>
      </header>

      {error && <div className="banner error">{error}</div>}
      {statusMessage && <div className="banner info">{statusMessage}</div>}

      <main className="grid">
        <section className="card">
          <h2>Connection</h2>
          <label>
            Backend URL
            <input
              value={draft.backendUrl}
              onChange={(e) => setDraft({ ...draft, backendUrl: e.target.value })}
              placeholder="http://127.0.0.1:8000"
            />
          </label>
          <label>
            Email
            <input
              value={draft.email}
              onChange={(e) => setDraft({ ...draft, email: e.target.value })}
              autoComplete="username"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </label>
          <div className="row">
            {token ? (
              <button type="button" onClick={() => void handleLogout()}>
                Sign out
              </button>
            ) : (
              <button type="button" disabled={isConnecting} onClick={() => void handleLogin()}>
                {isConnecting ? "Connecting…" : "Sign in"}
              </button>
            )}
            <button type="button" className="secondary" onClick={() => void refreshDashboard()}>
              Refresh
            </button>
          </div>
        </section>

        <section className="card">
          <h2>Review queue</h2>
          {stats ? (
            <ul className="stats">
              <li>
                <strong>{stats.pending_review}</strong> pending
              </li>
              <li>
                <strong>{stats.approved}</strong> approved
              </li>
              <li>
                <strong>{stats.rejected}</strong> rejected
              </li>
              <li>
                <strong>{stats.revision_requested}</strong> revisions
              </li>
            </ul>
          ) : (
            <p className="muted">Sign in to load review stats from the backend.</p>
          )}
          {token && (
            <button type="button" onClick={() => void handleRunPipeline()}>
              Run morning pipeline
            </button>
          )}
        </section>

        <section className="card">
          <h2>Desktop settings</h2>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={draft.notificationsEnabled}
              onChange={(e) => setDraft({ ...draft, notificationsEnabled: e.target.checked })}
            />
            Native notifications for pipeline alerts
          </label>
          <label>
            Notification poll (seconds)
            <input
              type="number"
              min={15}
              value={draft.notificationPollSeconds}
              onChange={(e) =>
                setDraft({ ...draft, notificationPollSeconds: Number(e.target.value) })
              }
            />
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={draft.autoStartEnabled}
              onChange={(e) => setDraft({ ...draft, autoStartEnabled: e.target.checked })}
            />
            Start Career OS when Windows starts
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={draft.launchMinimized}
              onChange={(e) => setDraft({ ...draft, launchMinimized: e.target.checked })}
            />
            Launch minimized to tray
          </label>
          <div className="row">
            <button type="button" disabled={isSaving} onClick={() => void handleSaveSettings()}>
              {isSaving ? "Saving…" : "Save settings"}
            </button>
            <button type="button" className="secondary" onClick={() => void handleClearLocalData()}>
              Clear local data
            </button>
          </div>
        </section>

        <section className="card wide">
          <h2>Recent notifications</h2>
          {recentNotifications.length === 0 ? (
            <p className="muted">No pipeline notifications yet.</p>
          ) : (
            <ul className="notifications">
              {recentNotifications.map((n) => (
                <li key={n.id}>
                  <strong>{n.message}</strong>
                  <span>{new Date(n.created_at).toLocaleString()}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>

      <footer className="footer">
        Local storage: auth token and desktop preferences only. Resumes, applications, and pipeline
        data remain on the backend.
      </footer>
    </div>
  );
}
