import { findNewNotifications, mergeSeenNotificationIds } from "./notifications";
import type { CareerOsApiClient, PipelineNotification } from "../api/client";
import type { DesktopSettings } from "./settings";
import { saveSettings } from "./localStorage";

export interface NativeNotifier {
  show(title: string, body: string): Promise<void>;
}

/** No-op notifier for tests and non-Tauri environments. */
export const noopNotifier: NativeNotifier = {
  async show() {
    // intentionally empty
  },
};

export async function createTauriNotifier(): Promise<NativeNotifier> {
  if (typeof window === "undefined" || !("__TAURI_INTERNALS__" in window)) {
    return noopNotifier;
  }
  const { isPermissionGranted, requestPermission, sendNotification } = await import(
    "@tauri-apps/plugin-notification"
  );
  let granted = await isPermissionGranted();
  if (!granted) {
    const result = await requestPermission();
    granted = result === "granted";
  }
  return {
    async show(title: string, body: string) {
      if (!granted) return;
      await sendNotification({ title, body });
    },
  };
}

export class NotificationPoller {
  private timer: ReturnType<typeof setInterval> | null = null;
  private seenIds = new Set<string>();

  constructor(
    private readonly getClient: () => CareerOsApiClient | null,
    private readonly getSettings: () => DesktopSettings,
    private readonly notifier: NativeNotifier,
    private readonly onNewNotifications?: (items: PipelineNotification[]) => void,
  ) {}

  seedSeenIds(ids: string[]): void {
    this.seenIds = new Set(ids);
  }

  start(): void {
    this.stop();
    const settings = this.getSettings();
    if (!settings.notificationsEnabled) return;

    const pollMs = Math.max(15, settings.notificationPollSeconds) * 1000;
    void this.poll();
    this.timer = setInterval(() => void this.poll(), pollMs);
  }

  stop(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  async poll(): Promise<PipelineNotification[]> {
    const client = this.getClient();
    const settings = this.getSettings();
    if (!client || !settings.notificationsEnabled) {
      return [];
    }

    try {
      const notifications = await client.schedulerNotifications(true);
      const fresh = findNewNotifications(notifications, this.seenIds);
      if (fresh.length === 0) {
        return [];
      }

      for (const item of fresh) {
        await this.notifier.show("Career OS", item.message);
        this.seenIds.add(item.id);
        try {
          await client.markNotificationRead(item.id);
        } catch {
          // Backend may be temporarily unavailable; keep local dedupe.
        }
      }

      const updated = mergeSeenNotificationIds(settings.lastSeenNotificationIds, [
        ...fresh.map((n) => n.id),
      ]);
      await saveSettings({ ...settings, lastSeenNotificationIds: updated });
      this.onNewNotifications?.(fresh);
      return fresh;
    } catch {
      return [];
    }
  }
}
