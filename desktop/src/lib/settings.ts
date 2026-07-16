export interface DesktopSettings {
  backendUrl: string;
  email: string;
  notificationsEnabled: boolean;
  notificationPollSeconds: number;
  autoStartEnabled: boolean;
  launchMinimized: boolean;
  lastSeenNotificationIds: string[];
}

export const SETTINGS_STORE_KEY = "settings.json";
export const AUTH_STORE_KEY = "auth.json";
export const AUTH_TOKEN_KEY = "access_token";

export const DEFAULT_SETTINGS: DesktopSettings = {
  backendUrl: "http://127.0.0.1:8000",
  email: "user@example.com",
  notificationsEnabled: true,
  notificationPollSeconds: 60,
  autoStartEnabled: false,
  launchMinimized: false,
  lastSeenNotificationIds: [],
};

export function mergeSettings(partial: Partial<DesktopSettings>): DesktopSettings {
  return { ...DEFAULT_SETTINGS, ...partial };
}

export function normalizeBackendUrl(url: string): string {
  return url.trim().replace(/\/$/, "");
}

export function isValidBackendUrl(url: string): boolean {
  try {
    const parsed = new URL(normalizeBackendUrl(url));
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}
