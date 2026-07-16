const DEFAULT_APP_URL = "https://career-os-daxds.vercel.app";

/** Canonical app origin for auth redirects (must match Supabase Auth URL config). */
export function getAppOrigin(): string {
  const configured = process.env.NEXT_PUBLIC_APP_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }

  if (typeof window !== "undefined" && window.location.origin) {
    return window.location.origin.replace(/\/$/, "");
  }

  return DEFAULT_APP_URL;
}

export function getAuthCallbackUrl(redirectPath = "/dashboard"): string {
  const redirect = redirectPath.startsWith("/") ? redirectPath : `/${redirectPath}`;
  return `${getAppOrigin()}/auth/callback?redirect=${encodeURIComponent(redirect)}`;
}
