import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, CareerOsApiClient } from "./client";

describe("CareerOsApiClient", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("calls health without auth", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        status: "healthy",
        app: "Career OS",
        version: "1.0.0",
        layer: "11-desktop",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const client = new CareerOsApiClient("http://127.0.0.1:8000");
    const health = await client.health();

    expect(health.status).toBe("healthy");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/health",
      expect.objectContaining({
        headers: expect.any(Headers),
      }),
    );
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get("Authorization")).toBeNull();
  });

  it("stores bearer token after login", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ access_token: "abc123" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ pending_review: 2, approved: 1, rejected: 0, revision_requested: 0 }),
      });
    vi.stubGlobal("fetch", fetchMock);

    const client = new CareerOsApiClient("http://127.0.0.1:8000");
    await client.login("user@example.com", "secret");
    expect(client.hasAuth()).toBe(true);
    await client.reviewStats();

    const statsHeaders = fetchMock.mock.calls[1][1].headers as Headers;
    expect(statsHeaders.get("Authorization")).toBe("Bearer abc123");
  });

  it("raises ApiError for backend failures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        json: async () => ({ detail: "Invalid token" }),
      }),
    );

    const client = new CareerOsApiClient("http://127.0.0.1:8000", "bad");
    await expect(client.reviewStats()).rejects.toBeInstanceOf(ApiError);
  });
});
