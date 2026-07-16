# Career OS V1 — Database Schema

**Engine:** PostgreSQL 16  
**Migrations:** Alembic `001` → `014`  
**ORM:** SQLAlchemy 2.x

---

## Entity Relationship Diagram

```mermaid
erDiagram
    users ||--o| user_profiles : has
    users ||--o{ master_resumes : owns
    users ||--o{ job_sources : configures
    users ||--o{ job_postings : discovers
    users ||--o{ job_scores : scores
    users ||--o{ job_applications : applies
    users ||--o{ agent_runs : runs
    users ||--o{ browser_sessions : sessions
    users ||--o{ pipeline_runs : schedules
    users ||--o{ pipeline_notifications : receives

    master_resumes ||--o{ resume_versions : versions

    job_sources ||--o{ job_postings : ingests

    job_postings ||--o| job_scores : scored_by
    job_postings ||--o| job_applications : generates
    job_postings ||--o{ agent_runs : analyzed
    job_postings ||--o{ automation_runs : automated

    job_applications ||--o{ application_documents : contains
    job_applications ||--o{ application_screenshots : proofs
    job_applications ||--o{ automation_runs : submitted_via

    browser_sessions ||--o{ automation_runs : uses
    automation_runs ||--o{ automation_action_logs : logs

    pipeline_runs ||--o{ pipeline_notifications : emits

    users {
        uuid id PK
        string email UK
        string hashed_password
        bool is_active
        datetime created_at
    }

    user_profiles {
        uuid id PK
        uuid user_id FK
        string legal_name
        string location_city
        string location_province
        string work_authorization
        json immigration_goals
        json preferred_provinces
        json skills
    }

    master_resumes {
        uuid id PK
        uuid user_id FK
        string label UK
        string category
        string file_path
        json parsed_content
        int version
    }

    resume_versions {
        uuid id PK
        uuid master_resume_id FK
        int version_number
        string file_path
    }

    job_sources {
        uuid id PK
        uuid user_id FK
        string preset_key
        string name
        string source_type
        json config
        bool is_builtin
        bool is_active
    }

    job_postings {
        uuid id PK
        uuid user_id FK
        uuid source_id FK
        string title
        string company
        string description
        string dedup_key
        string status
        json classification
    }

    job_scores {
        uuid id PK
        uuid user_id FK
        uuid job_id FK UK
        int overall_score
        json immigration
        json scoring
        json ats
        uuid selected_master_resume_id
    }

    job_applications {
        uuid id PK
        uuid user_id FK
        uuid job_id FK UK
        string status
        int version
        datetime generated_at
        datetime reviewed_at
        text review_notes
    }

    application_documents {
        uuid id PK
        uuid application_id FK
        string document_type
        string storage_path
        json metadata
    }

    application_screenshots {
        uuid id PK
        uuid application_id FK
        string storage_path
        string caption
    }

    agent_runs {
        uuid id PK
        uuid user_id FK
        uuid job_id FK
        string agent_name
        string status
        json output
    }

    browser_sessions {
        uuid id PK
        uuid user_id FK
        string connector_key UK
        string profile_path
        string status
    }

    automation_runs {
        uuid id PK
        uuid user_id FK
        uuid job_id FK
        uuid application_id FK
        uuid browser_session_id FK
        string connector_key
        string status
        bool submitted
        json run_state
    }

    automation_action_logs {
        uuid id PK
        uuid run_id FK
        string action
        json details
    }

    pipeline_runs {
        uuid id PK
        uuid user_id FK
        string trigger_type
        string scope
        string status
        json step_log
        json summary
        bool notification_sent
    }

    pipeline_notifications {
        uuid id PK
        uuid user_id FK
        uuid pipeline_run_id FK
        text message
        json details
        datetime read_at
    }

    audit_logs {
        int id PK
        string entity_type
        string entity_id
        string action
        string actor
        json details
        datetime created_at
    }

    prompt_versions {
        int id PK
        string name
        int version
        string content_hash
        bool is_active
    }

    system_metadata {
        string key PK
        string value
    }
```

---

## Migration Chain

| Revision | Layer | Key Tables / Changes |
|----------|-------|-------------------|
| 001 | 0 | `system_metadata` |
| 002 | 0.1 | `audit_logs`, `prompt_versions` |
| 003 | 1 | `users`, `user_profiles` |
| 004 | 1 | Profile preference columns |
| 005 | 2 | `master_resumes`, `resume_versions` |
| 006 | 3 | `job_sources`, `job_postings` |
| 007 | 3 | Source presets (`preset_key`, `is_builtin`) |
| 008 | 4 | Schema layer marker |
| 009 | 5 | `job_scores`, `agent_runs` |
| 010 | 6 | `job_applications`, `application_documents` |
| 011 | 7 | Tracking columns, `application_screenshots` |
| 012 | 8 | `review_notes`, `reviewed_at` |
| 013 | 9 | `browser_sessions`, `automation_runs`, `automation_action_logs` |
| 014 | 10 | `pipeline_runs`, `pipeline_notifications` |

---

## File Storage (Outside Database)

| Path | Content |
|------|---------|
| `storage/resumes/{user_id}/` | Master resume files |
| `storage/applications/{user_id}/{job_id}/` | Tailored docs, cover letters, emails |
| `storage/browser_profiles/` | Playwright persistent profiles |
| `storage/browser_screenshots/` | Automation screenshots |

---

## Indexes & Constraints

- Unique: `(user_id, name)` on `job_sources`
- Unique: `(user_id, preset_key)` on `job_sources`
- Unique: `(user_id, label)` on `master_resumes`
- Unique: `(user_id, job_id)` on `job_applications`, `job_scores`
- Unique: `(user_id, connector_key)` on `browser_sessions`
