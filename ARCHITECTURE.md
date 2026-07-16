# Career OS V1 — Architecture

---

## System Overview

```mermaid
flowchart TB
    subgraph Desktop["Layer 11 — Desktop (Tauri)"]
        UI[React Shell]
        LocalStore[Local Settings + Auth Token]
        Tray[System Tray]
        NativeNotif[Native Notifications]
    end

    subgraph API["FastAPI Backend"]
        Routes[API Routes /api/v1]
        DI[Dependency Injection]
        Services[Application Services]
        Ports[Port Interfaces]
    end

    subgraph Infra["Infrastructure"]
        Repos[SQLAlchemy Repositories]
        AI[Model Router + Providers]
        Prompts[Prompt Registry]
        Browser[Playwright Automation]
        Scheduler[APScheduler]
        Storage[Local File Storage]
        Audit[Audit Log]
        Log[Structlog]
    end

    subgraph Data["Data"]
        PG[(PostgreSQL)]
        Files[(File Storage)]
    end

    UI -->|HTTP REST| Routes
    LocalStore -.-> UI
    Tray -.-> UI
    NativeNotif -.-> UI

    Routes --> DI --> Services
    Services --> Ports
    Ports --> Repos
    Ports --> AI
    Ports --> Prompts
    Ports --> Browser
    Ports --> Scheduler
    Ports --> Storage
    Ports --> Audit

    Repos --> PG
    Storage --> Files
    Browser --> Files
    Services --> Log
```

---

## Hexagonal Layers

```
┌─────────────────────────────────────────────────────────┐
│  API (FastAPI routes + Pydantic schemas)                │
├─────────────────────────────────────────────────────────┤
│  Application Services (orchestration, LangGraph)      │
│    job_service, job_intelligence_service,                 │
│    document_generation_service, review_queue_service,     │
│    application_automation_service, scheduler_pipeline     │
├─────────────────────────────────────────────────────────┤
│  Ports (abstract interfaces)                            │
├─────────────────────────────────────────────────────────┤
│  Infrastructure (adapters)                              │
│    repositories, AI providers, browser, prompts, audit    │
├─────────────────────────────────────────────────────────┤
│  Domain (enums, presets, constants)                       │
└─────────────────────────────────────────────────────────┘
```

---

## AI Request Flow

```mermaid
sequenceDiagram
    participant Agent as LLM Agent
    participant Router as ModelRouter
    participant Registry as CapabilityRegistry
    participant Provider as OpenAI / Anthropic
    participant Audit as AuditLog

    Agent->>Router: complete_for_capability(capability, prompt)
    Router->>Registry: get routing config
    Registry-->>Router: primary + fallback providers
    Router->>Provider: complete(messages)
    Provider-->>Router: response
    Router-->>Agent: parsed result
    Agent->>Audit: record_agent_decision
```

**Rule:** Application services never import provider SDKs directly.

---

## Job Application Lifecycle

```mermaid
stateDiagram-v2
    [*] --> NEW: Job imported
    NEW --> SCORED: Layer 5 intelligence
    SCORED --> GENERATED: Layer 6 documents
    GENERATED --> APPROVED: Layer 8 review
    GENERATED --> REJECTED: Layer 8 review
    GENERATED --> REVISION_REQUESTED: Layer 8 review
    REVISION_REQUESTED --> GENERATED: Regenerate docs
    APPROVED --> SUBMITTED: Manual or Layer 9 automation
    REJECTED --> [*]
    SUBMITTED --> [*]
```

---

## Morning Pipeline (Layer 10)

```mermaid
flowchart LR
    A[Search Jobs] --> B[Import]
    B --> C[Dedupe + Classify]
    C --> D[Intelligence L5]
    D --> E[Documents L6]
    E --> F[Review Queue L8]
    F --> G[Notify User]
```

Triggered by: APScheduler cron, manual API, or scoped runs (source/company/job).

---

## Browser Automation (Layer 9)

```mermaid
flowchart TD
    A[Approved Application] --> B[Resolve Connector]
    B --> C[Browser Session]
    C --> D[Playwright Steps]
    D --> E{CAPTCHA?}
    E -->|Yes| F[Pause + Notify User]
    F --> G[Resume Session]
    G --> D
    E -->|No| H{Stop before submit?}
    H -->|Yes| I[Stopped]
    H -->|No| J[Record Submission L7]
```

Connectors: `job_bank_canada`, `workpei`, `indeed`, `company_career_pages` (YAML-driven).

---

## Desktop Architecture (Layer 11)

The desktop app is intentionally thin:

- **Stores locally:** backend URL, preferences, JWT
- **Polls:** scheduler notifications → native Windows toasts
- **Displays:** health, review stats, recent notifications
- **Triggers:** manual pipeline run via API
- **Does not:** duplicate business logic or embed the backend

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Single-user default | Personal career OS for one job seeker |
| Capability-based AI routing | Swap models per task without code changes |
| Prompt file + DB versioning | Git-friendly prompts with runtime active version |
| Manual submission default | User control over job applications |
| Config-driven job search | Scrapers deferred; pipeline testable via config |
| Tauri over Electron | Smaller footprint for Windows desktop shell |
| Production validation | `ENVIRONMENT=production` rejects insecure defaults at startup |
| Operational CLI | `career-os` for migrate, backup, restore, health outside the API |
