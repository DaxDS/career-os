import type { PipelineNotification } from "../api/client";

/** Pure helper — filters notifications not yet shown on the desktop. */
export function findNewNotifications(
  notifications: PipelineNotification[],
  seenIds: ReadonlySet<string>,
): PipelineNotification[] {
  return notifications.filter((n) => !seenIds.has(n.id));
}

export function mergeSeenNotificationIds(
  existing: string[],
  newIds: string[],
  maxEntries = 200,
): string[] {
  const merged = [...new Set([...existing, ...newIds])];
  return merged.slice(-maxEntries);
}
