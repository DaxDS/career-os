import { describe, expect, it } from "vitest";
import { findNewNotifications, mergeSeenNotificationIds } from "./notifications";

describe("notification helpers", () => {
  it("finds only unseen notifications", () => {
    const notifications = [
      { id: "a", message: "one" },
      { id: "b", message: "two" },
    ] as const;

    const fresh = findNewNotifications([...notifications], new Set(["a"]));
    expect(fresh).toHaveLength(1);
    expect(fresh[0].id).toBe("b");
  });

  it("caps merged seen notification ids", () => {
    const existing = Array.from({ length: 199 }, (_, i) => `id-${i}`);
    const merged = mergeSeenNotificationIds(existing, ["id-199", "id-200"], 200);
    expect(merged).toHaveLength(200);
    expect(merged.at(-1)).toBe("id-200");
  });
});
