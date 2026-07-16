import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CareerOsApiClient, PipelineNotification } from "../api/client";
import { NotificationPoller, noopNotifier } from "./notificationPoller";
import { DEFAULT_SETTINGS } from "./settings";

function makeNotification(id: string, message: string): PipelineNotification {
  return {
    id,
    pipeline_run_id: "run-1",
    message,
    details: {},
    read_at: null,
    created_at: new Date().toISOString(),
  };
}

describe("NotificationPoller", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  it("shows native notifications for unseen backend alerts", async () => {
    const notifier = {
      show: vi.fn().mockResolvedValue(undefined),
    };
    const client = {
      schedulerNotifications: vi
        .fn()
        .mockResolvedValue([makeNotification("n1", "Today's applications are ready for review.")]),
      markNotificationRead: vi.fn().mockResolvedValue(makeNotification("n1", "done")),
    } as unknown as CareerOsApiClient;

    const poller = new NotificationPoller(
      () => client,
      () => DEFAULT_SETTINGS,
      notifier,
    );

    const fresh = await poller.poll();
    expect(fresh).toHaveLength(1);
    expect(notifier.show).toHaveBeenCalledWith(
      "Career OS",
      "Today's applications are ready for review.",
    );
    expect(client.markNotificationRead).toHaveBeenCalledWith("n1");
  });

  it("does not poll when notifications are disabled", async () => {
    const client = {
      schedulerNotifications: vi.fn(),
    } as unknown as CareerOsApiClient;

    const poller = new NotificationPoller(
      () => client,
      () => ({ ...DEFAULT_SETTINGS, notificationsEnabled: false }),
      noopNotifier,
    );

    const fresh = await poller.poll();
    expect(fresh).toHaveLength(0);
    expect(client.schedulerNotifications).not.toHaveBeenCalled();
  });
});
