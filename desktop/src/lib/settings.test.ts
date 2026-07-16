import { describe, expect, it } from "vitest";
import {
  DEFAULT_SETTINGS,
  isValidBackendUrl,
  mergeSettings,
  normalizeBackendUrl,
} from "./settings";

describe("desktop settings", () => {
  it("merges partial settings with defaults", () => {
    const merged = mergeSettings({ backendUrl: "http://localhost:9000" });
    expect(merged.backendUrl).toBe("http://localhost:9000");
    expect(merged.notificationsEnabled).toBe(DEFAULT_SETTINGS.notificationsEnabled);
  });

  it("normalizes backend URL trailing slash", () => {
    expect(normalizeBackendUrl("http://127.0.0.1:8000/")).toBe("http://127.0.0.1:8000");
  });

  it("validates backend URLs", () => {
    expect(isValidBackendUrl("http://127.0.0.1:8000")).toBe(true);
    expect(isValidBackendUrl("not-a-url")).toBe(false);
  });
});
