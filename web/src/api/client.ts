/** Career OS product API client — all business logic stays on the backend. */

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  layer: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface AuthConfigResponse {
  skip_auth: boolean;
  default_email: string;
}

export interface UserResponse {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface ReviewStats {
  pending_review: number;
  approved: number;
  rejected: number;
  revision_requested: number;
}

export interface ReviewQueueItem {
  application_id: string;
  job_id: string;
  title: string;
  company: string;
  location_province: string;
  overall_score: number | null;
  match_score: number | null;
  ats_score: number | null;
  immigration_score: number | null;
  ats_fact_check_passed: boolean | null;
  resume_summary_preview: string;
  cover_letter_preview: string;
  generated_at: string;
  version: number;
}

export interface DocumentPreviews {
  resume_summary?: string;
  cover_letter_excerpt?: string;
  email_subject?: string;
  ats_score?: number | null;
  fact_check_passed?: boolean | null;
}

export interface ReviewDetail {
  application_id: string;
  job_id: string;
  status: string;
  title: string;
  company: string;
  overall_score: number | null;
  match_score: number | null;
  ats_score: number | null;
  immigration_score: number | null;
  document_previews: DocumentPreviews;
  review_notes: string;
}

export interface MasterResume {
  id: string;
  label: string;
  category: string;
  original_filename: string;
  is_active: boolean;
  version: number;
  uploaded_at: string;
  parsed_preview: {
    summary: string;
    skills: string[];
    experience_count: number;
  };
}

export interface JobPosting {
  id: string;
  title: string;
  company: string;
  location_province: string;
  source_url: string;
  description_preview: string;
  status: string;
  role_family: string | null;
  created_at: string;
  overall_score: number | null;
  immigration_score: number | null;
}

export interface AIStatus {
  ai_enabled: boolean;
  providers: Record<string, boolean>;
  prompts_synced: number;
  prompts_total: number;
}

export interface BillingOverview {
  plan: string;
  plan_label: string;
  price_monthly_cad: number | null;
  limits: {
    ai_pipeline_runs: number;
    jobs_per_month: number;
    resume_slots: number;
  };
  usage: {
    ai_pipeline_runs: number;
    jobs_this_month: number;
    resumes: number;
  };
  features: string[];
  upgrade_available: boolean;
}

export interface PipelineNotification {
  id: string;
  message: string;
  created_at: string;
  read_at: string | null;
}

export interface PipelineRun {
  id: string;
  trigger_type: string;
  status: string;
  step_log: { step: string; status: string; [key: string]: unknown }[];
  summary: {
    jobs_searched?: number;
    jobs_imported_created?: number;
    jobs_analyzed?: number;
    jobs_documents_generated?: number;
    applications_ready_for_review?: number;
    errors?: string[];
  };
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface TrackedApplication {
  application_id: string;
  job_id: string;
  status: string;
  job_title: string;
  company: string;
  location_province: string;
  source_url?: string;
  approved_at: string | null;
  submitted_at: string | null;
}

export interface AutomationResult {
  run_id: string;
  session_id: string | null;
  status: string;
  submitted: boolean;
  connector_key: string;
  paused_for_captcha: boolean;
  failure_reason: string | null;
  result: Record<string, unknown>;
}

export const RESUME_TYPES = [
  { id: "ai", label: "AI / Machine Learning", apiLabel: "AI Resume" },
  { id: "it", label: "IT & Software", apiLabel: "IT Resume" },
  { id: "general", label: "General", apiLabel: "General Resume" },
  { id: "construction", label: "Construction", apiLabel: "Construction Resume" },
  { id: "production", label: "Production & Operations", apiLabel: "Production Resume" },
] as const;

export interface LinkedInOptimization {
  keyword_score: number;
  missing_keywords: string[];
  headline_rewrite: string;
  about_rewrite: string;
  suggestions: { section: string; issue: string; fix: string }[];
}

export interface InterviewQuestionSet {
  job_title: string;
  company: string;
  questions: { question: string; focus: string; why: string }[];
}

export interface InterviewFeedback {
  score: number;
  strengths: string[];
  improvements: string[];
  suggested_answer: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class CareerOsClient {
  private accessToken: string | null = null;

  constructor(private baseUrl = "") {}

  setToken(token: string | null) {
    this.accessToken = token;
  }

  get apiBase(): string {
    const root = (this.baseUrl || "").replace(/\/$/, "");
    return `${root}/api/v1`;
  }

  async login(email: string, password: string): Promise<TokenResponse> {
    return this.request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
      auth: false,
    });
  }

  async authConfig(): Promise<AuthConfigResponse> {
    return this.request<AuthConfigResponse>("/auth/config", { auth: false });
  }

  async autoLogin(): Promise<TokenResponse> {
    return this.request<TokenResponse>("/auth/auto", { method: "POST", auth: false });
  }

  async register(email: string, password: string): Promise<TokenResponse> {
    return this.request<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
      auth: false,
    });
  }

  async me(): Promise<UserResponse> {
    return this.request<UserResponse>("/auth/me");
  }

  async health(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health", { auth: false });
  }

  async aiStatus(): Promise<AIStatus> {
    return this.request<AIStatus>("/ai/status");
  }

  async billingOverview(): Promise<BillingOverview> {
    return this.request<BillingOverview>("/billing/overview");
  }

  async createCheckoutSession(plan = "pro"): Promise<{ url: string }> {
    return this.request<{ url: string }>("/billing/create-checkout-session", {
      method: "POST",
      body: JSON.stringify({ plan }),
    });
  }

  async optimizeLinkedIn(
    headline: string,
    about: string,
    targetRoleFamily: string,
  ): Promise<LinkedInOptimization> {
    return this.request<LinkedInOptimization>("/linkedin/optimize", {
      method: "POST",
      body: JSON.stringify({
        headline,
        about,
        target_role_family: targetRoleFamily,
      }),
    });
  }

  async interviewQuestions(jobId: string): Promise<InterviewQuestionSet> {
    return this.request<InterviewQuestionSet>(`/interview/jobs/${jobId}/questions`, {
      method: "POST",
    });
  }

  async coachInterviewAnswer(
    jobId: string,
    question: string,
    answer: string,
  ): Promise<InterviewFeedback> {
    return this.request<InterviewFeedback>(`/interview/jobs/${jobId}/coach`, {
      method: "POST",
      body: JSON.stringify({ question, answer }),
    });
  }

  async parseJobUrl(url: string): Promise<{
    title: string;
    company: string;
    description: string;
    location: string;
    location_province: string;
    source_url: string;
  }> {
    return this.request("/jobs/parse-url", {
      method: "POST",
      body: JSON.stringify({ url }),
    });
  }

  async reviewStats(): Promise<ReviewStats> {
    return this.request<ReviewStats>("/review/stats");
  }

  async reviewQueue(): Promise<ReviewQueueItem[]> {
    return this.request<ReviewQueueItem[]>("/review/queue");
  }

  async reviewDetail(jobId: string): Promise<ReviewDetail> {
    return this.request<ReviewDetail>(`/review/jobs/${jobId}`);
  }

  async reviewDecide(jobId: string, decision: string, notes = ""): Promise<unknown> {
    return this.request(`/review/jobs/${jobId}/decide`, {
      method: "POST",
      body: JSON.stringify({ decision, notes }),
    });
  }

  async listResumes(): Promise<MasterResume[]> {
    return this.request<MasterResume[]>("/resumes/master");
  }

  async uploadResume(file: File, apiLabel: string): Promise<MasterResume> {
    const form = new FormData();
    form.append("label", apiLabel);
    form.append("file", file);
    return this.requestForm<MasterResume>("/resumes/master", form, "POST");
  }

  async listJobs(): Promise<JobPosting[]> {
    return this.request<JobPosting[]>("/jobs");
  }

  async importJob(item: {
    title: string;
    company: string;
    source_url?: string;
    description?: string;
    location_province?: string;
  }): Promise<{ created: number; jobs: JobPosting[] }> {
    const result = await this.request<{
      created: number;
      duplicates: number;
      results: { import_status: string; job: JobPosting }[];
    }>("/jobs/import", {
      method: "POST",
      body: JSON.stringify({
        source_preset_key: "manual_url_import",
        jobs: [
          {
            title: item.title,
            company: item.company,
            source_url: item.source_url || "",
            description: item.description || "",
            location_province: item.location_province || "ON",
          },
        ],
      }),
    });
    return { created: result.created, jobs: result.results.map((r) => r.job) };
  }

  async runPipeline(): Promise<PipelineRun> {
    return this.request<PipelineRun>("/scheduler/run", { method: "POST" });
  }

  async listPipelineRuns(limit = 10): Promise<PipelineRun[]> {
    return this.request<PipelineRun[]>(`/scheduler/runs?limit=${limit}`);
  }

  async runJobPipeline(jobId: string): Promise<unknown> {
    return this.request(`/scheduler/run/job/${jobId}`, { method: "POST" });
  }

  async generateDocuments(jobId: string): Promise<unknown> {
    return this.request(`/documents/jobs/${jobId}/generate`, { method: "POST" });
  }

  async notifications(): Promise<PipelineNotification[]> {
    return this.request<PipelineNotification[]>("/scheduler/notifications?unread_only=false");
  }

  async listApplications(status?: string): Promise<
    {
      application: {
        id: string;
        job_id: string;
        status: string;
        approved_at: string | null;
        submitted_at: string | null;
      };
      job_title: string;
      company: string;
      location_province: string;
    }[]
  > {
    const q = status ? `?status=${encodeURIComponent(status)}` : "";
    return this.request(`/tracking/applications${q}`);
  }

  async applyToJob(jobId: string, stopBeforeSubmit = false): Promise<AutomationResult> {
    return this.request<AutomationResult>(`/automation/jobs/${jobId}/submit`, {
      method: "POST",
      body: JSON.stringify({ stop_before_submit: stopBeforeSubmit }),
    });
  }

  private async request<T>(
    path: string,
    options: RequestInit & { auth?: boolean } = {},
  ): Promise<T> {
    const { auth = true, ...init } = options;
    const headers = new Headers(init.headers);
    if (!(init.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
    }
    if (auth && this.accessToken) {
      headers.set("Authorization", `Bearer ${this.accessToken}`);
    }

    const response = await fetch(`${this.apiBase}${path}`, { ...init, headers });
    if (!response.ok) {
      let detail = response.statusText;
      try {
        const body = await response.json();
        if (typeof body.detail === "string") detail = body.detail;
        else if (Array.isArray(body.detail))
          detail = body.detail.map((d: { msg: string }) => d.msg).join(", ");
      } catch {
        try {
          const text = (await response.text()).trim();
          if (text.includes("Tunnel Unavailable")) {
            detail =
              "API offline — Vercel cannot reach the backend. Set CAREER_OS_API_URL in Vercel env vars to a live API URL.";
          } else if (text) {
            detail = text.slice(0, 200);
          }
        } catch {
          /* ignore */
        }
      }
      if (response.status === 503 && detail === response.statusText) {
        detail =
          "API unavailable — configure CAREER_OS_API_URL on Vercel or run the backend locally.";
      }
      throw new ApiError(detail, response.status);
    }
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  private async requestForm<T>(path: string, form: FormData, method: string): Promise<T> {
    const headers = new Headers();
    if (this.accessToken) headers.set("Authorization", `Bearer ${this.accessToken}`);
    const response = await fetch(`${this.apiBase}${path}`, { method, body: form, headers });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new ApiError(String(body.detail || response.statusText), response.status);
    }
    return (await response.json()) as T;
  }
}

export const api = new CareerOsClient(import.meta.env.VITE_API_URL ?? "");
