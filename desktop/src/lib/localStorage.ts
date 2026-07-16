import {
  AUTH_STORE_KEY,
  AUTH_TOKEN_KEY,
  DEFAULT_SETTINGS,
  SETTINGS_STORE_KEY,
  type DesktopSettings,
  mergeSettings,
} from "./settings";

export interface KeyValueStore {
  get<T>(key: string): Promise<T | null>;
  set(key: string, value: unknown): Promise<void>;
  save(): Promise<void>;
}

/** In-memory store for Vitest and browser preview without Tauri. */
export class MemoryStore implements KeyValueStore {
  private data = new Map<string, unknown>();

  async get<T>(key: string): Promise<T | null> {
    return (this.data.get(key) as T | undefined) ?? null;
  }

  async set(key: string, value: unknown): Promise<void> {
    this.data.set(key, value);
  }

  async save(): Promise<void> {
    // no-op
  }
}

async function loadTauriStore(filename: string): Promise<KeyValueStore | null> {
  if (typeof window === "undefined" || !("__TAURI_INTERNALS__" in window)) {
    return null;
  }
  const { load } = await import("@tauri-apps/plugin-store");
  const store = await load(filename, { autoSave: false });
  return {
    get: <T>(key: string) => store.get<T>(key),
    set: (key: string, value: unknown) => store.set(key, value),
    save: () => store.save(),
  };
}

let settingsStorePromise: Promise<KeyValueStore> | null = null;
let authStorePromise: Promise<KeyValueStore> | null = null;

async function getSettingsStore(): Promise<KeyValueStore> {
  if (!settingsStorePromise) {
    settingsStorePromise = (async () => {
      const tauri = await loadTauriStore(SETTINGS_STORE_KEY);
      return tauri ?? new MemoryStore();
    })();
  }
  return settingsStorePromise;
}

async function getAuthStore(): Promise<KeyValueStore> {
  if (!authStorePromise) {
    authStorePromise = (async () => {
      const tauri = await loadTauriStore(AUTH_STORE_KEY);
      return tauri ?? new MemoryStore();
    })();
  }
  return authStorePromise;
}

const SETTINGS_KEY = "desktop";

export async function loadSettings(): Promise<DesktopSettings> {
  const store = await getSettingsStore();
  const saved = await store.get<Partial<DesktopSettings>>(SETTINGS_KEY);
  return mergeSettings(saved ?? {});
}

export async function saveSettings(settings: DesktopSettings): Promise<void> {
  const store = await getSettingsStore();
  await store.set(SETTINGS_KEY, settings);
  await store.save();
}

export async function loadAccessToken(): Promise<string | null> {
  const store = await getAuthStore();
  return store.get<string>(AUTH_TOKEN_KEY);
}

export async function saveAccessToken(token: string | null): Promise<void> {
  const store = await getAuthStore();
  if (token) {
    await store.set(AUTH_TOKEN_KEY, token);
  } else {
    await store.set(AUTH_TOKEN_KEY, null);
  }
  await store.save();
}

export async function clearLocalData(): Promise<void> {
  const settingsStore = await getSettingsStore();
  const authStore = await getAuthStore();
  await settingsStore.set(SETTINGS_KEY, DEFAULT_SETTINGS);
  await authStore.set(AUTH_TOKEN_KEY, null);
  await settingsStore.save();
  await authStore.save();
}
