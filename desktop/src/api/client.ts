/** Thin HTTP client — delegates all business logic to the Career OS backend API. */

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  layer: string;
}

export interface TokenResponse {
  access_token: string;
}

export interface ReviewStats {
  pending_review: number;
  approved: number;
  rejected: number;
  revision_requested: number;
}

export interface PipelineNotification {
  id: string;
  pipeline_run_id: string;
  message: string;
  details: Record<string, unknown>;
  read_at: string | null;
  created_at: string;
}

export interface ReviewQueueItem {
  job_id: string;
  application_id: string;
  title: string;
  company: string;
  overall_score: number | null;
  status: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class CareerOsApiClient {
  constructor(
    private baseUrl: string,
    private accessToken: string | null = null,
  ) {}

  setAccessToken(token: string | null): void {
    this.accessToken = token;
  }

  hasAuth(): boolean {
    return Boolean(this.accessToken);
  }

  get apiBase(): string {
    return `${this.baseUrl.replace(/\/$/, "")}/api/v1`;
  }

  async health(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health");
  }

  async login(email: string, password: string): Promise<TokenResponse> {
    const result = await this.request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
      auth: false,
    });
    this.accessToken = result.access_token;
    return result;
  }

  async reviewStats(): Promise<ReviewStats> {
    return this.request<ReviewStats>("/review/stats");
  }

  async reviewQueue(minOverallScore?: number): Promise<ReviewQueueItem[]> {
    const query = minOverallScore != null ? `?min_overall_score=${minOverallScore}` : "";
    return this.request<ReviewQueueItem[]>(`/review/queue${query}`);
  }

  async schedulerNotifications(unreadOnly = true): Promise<PipelineNotification[]> {
    return this.request<PipelineNotification[]>(
      `/scheduler/notifications?unread_only=${unreadOnly}`,
    );
  }

  async markNotificationRead(notificationId: string): Promise<PipelineNotification> {
    return this.request<PipelineNotification>(
      `/scheduler/notifications/${notificationId}/read`,
      { method: "POST" },
    );
  }

  async triggerManualPipeline(): Promise<unknown> {
    return this.request("/scheduler/run", { method: "POST" });
  }

  private async request<T>(
    path: string,
    options: RequestInit & { auth?: boolean } = {},
  ): Promise<T> {
    const { auth = true, ...init } = options;
    const headers = new Headers(init.headers);
    headers.set("Content-Type", "application/json");
    if (auth && this.accessToken) {
      headers.set("Authorization", `Bearer ${this.accessToken}`);
    }

    const response = await fetch(`${this.apiBase}${path}`, {
      ...init,
      headers,
    });

    if (!response.ok) {
      let body: unknown;
      try {
        body = await response.json();
      } catch {
        body = await response.text();
      }
      const detail =
        typeof body === "object" && body && "detail" in body
          ? String((body as { detail: unknown }).detail)
          : response.statusText;
      throw new ApiError(detail || `HTTP ${response.status}`, response.status, body);
    }

    if (response.status === 204) {
      return undefined as T;
    }
    return (await response.json()) as T;
  }
}
