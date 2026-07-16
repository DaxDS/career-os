import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../api/client";

interface AuthState {
  token: string | null;
  email: string | null;
  skipAuth: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);
const TOKEN_KEY = "career_os_token";
const EMAIL_KEY = "career_os_email";

function persistSession(token: string, userEmail: string) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(EMAIL_KEY, userEmail);
  api.setToken(token);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [email, setEmail] = useState<string | null>(() => localStorage.getItem(EMAIL_KEY));
  const [skipAuth, setSkipAuth] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        const config = await api.authConfig();
        if (cancelled) return;

        if (config.skip_auth) {
          setSkipAuth(true);
          setEmail(config.default_email);
          localStorage.setItem(EMAIL_KEY, config.default_email);

          if (token) {
            api.setToken(token);
          } else {
            api.setToken(null);
            try {
              const session = await api.autoLogin();
              if (cancelled) return;
              persistSession(session.access_token, config.default_email);
              setToken(session.access_token);
            } catch {
              /* API still works without a token in dev bypass mode */
            }
          }
          return;
        }

        if (!token) {
          return;
        }

        api.setToken(token);
        const user = await api.me();
        if (cancelled) return;
        setEmail(user.email);
        localStorage.setItem(EMAIL_KEY, user.email);
      } catch {
        if (cancelled) return;
        setToken(null);
        setSkipAuth(false);
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(EMAIL_KEY);
        api.setToken(null);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const value = useMemo<AuthState>(
    () => ({
      token,
      email,
      skipAuth,
      isLoading,
      async login(userEmail, password) {
        const result = await api.login(userEmail, password);
        persistSession(result.access_token, userEmail);
        setToken(result.access_token);
        setEmail(userEmail);
        setSkipAuth(false);
      },
      async register(userEmail, password) {
        const result = await api.register(userEmail, password);
        persistSession(result.access_token, userEmail);
        setToken(result.access_token);
        setEmail(userEmail);
        setSkipAuth(false);
      },
      logout() {
        const keepSession = skipAuth;
        localStorage.removeItem(TOKEN_KEY);
        if (!keepSession) {
          localStorage.removeItem(EMAIL_KEY);
          setEmail(null);
        }
        api.setToken(null);
        setToken(null);
      },
    }),
    [token, email, skipAuth, isLoading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
