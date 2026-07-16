from enum import StrEnum


class AuditAction(StrEnum):
    """Categories of auditable events — extensible without schema changes."""

    AGENT_DECISION = "agent_decision"
    RESUME_SELECTION = "resume_selection"
    APPLICATION_ACTION = "application_action"
    USER_APPROVAL = "user_approval"
    SYSTEM_EVENT = "system_event"


class AuditActor(StrEnum):
    SYSTEM = "system"
    USER = "user"
    AGENT = "agent"


class StorageCategory(StrEnum):
    """Logical storage buckets — paths resolved via settings, never hardcoded."""

    MASTER_RESUME = "master_resume"
    RESUME_VERSION = "resume_version"
    COVER_LETTER = "cover_letter"
    EMAIL = "email"
    REPORT = "report"
    TEMPLATE = "template"
    SCREENSHOT = "screenshot"


class PromptName(StrEnum):
    """Registered prompt identifiers — maps to files under prompts_path."""

    RESUME_SELECTION = "resume_selection"
    RESUME_TAILORING = "resume_tailoring"
    COVER_LETTER = "cover_letter"
    EMAIL_GENERATION = "email_generation"
    ATS_ANALYSIS = "ats_analysis"
    JOB_SCORING = "job_scoring"
    JOB_CLASSIFICATION = "job_classification"
    IMMIGRATION_SCORING = "immigration_scoring"


class AICapability(StrEnum):
    """Canonical AI capability identifiers — business logic requests these, never providers."""

    RESUME_SELECTION = "resume_selection"
    RESUME_TAILORING = "resume_tailoring"
    COVER_LETTER_GENERATION = "cover_letter_generation"
    EMAIL_GENERATION = "email_generation"
    JOB_CLASSIFICATION = "job_classification"
    ATS_ANALYSIS = "ats_analysis"
    IMMIGRATION_SCORING = "immigration_scoring"
    JOB_SCORING = "job_scoring"
    # Infrastructure capabilities (not agent-facing)
    RESUME_CLASSIFICATION = "resume_classification"
    EMBEDDING = "embedding"
    STRUCTURED_OUTPUT = "structured_output"
    LINKEDIN_OPTIMIZATION = "linkedin_optimization"
    INTERVIEW_COACHING = "interview_coaching"


# Layer 5 agent capabilities — must exist in capabilities.yaml and manifest.yaml
CORE_AI_CAPABILITIES: frozenset[AICapability] = frozenset({
    AICapability.RESUME_SELECTION,
    AICapability.RESUME_TAILORING,
    AICapability.COVER_LETTER_GENERATION,
    AICapability.EMAIL_GENERATION,
    AICapability.JOB_CLASSIFICATION,
    AICapability.ATS_ANALYSIS,
    AICapability.IMMIGRATION_SCORING,
    AICapability.JOB_SCORING,
})


PROMPT_TO_CAPABILITY: dict[PromptName, AICapability] = {
    PromptName.RESUME_SELECTION: AICapability.RESUME_SELECTION,
    PromptName.RESUME_TAILORING: AICapability.RESUME_TAILORING,
    PromptName.COVER_LETTER: AICapability.COVER_LETTER_GENERATION,
    PromptName.EMAIL_GENERATION: AICapability.EMAIL_GENERATION,
    PromptName.ATS_ANALYSIS: AICapability.ATS_ANALYSIS,
    PromptName.JOB_SCORING: AICapability.JOB_SCORING,
    PromptName.JOB_CLASSIFICATION: AICapability.JOB_CLASSIFICATION,
    PromptName.IMMIGRATION_SCORING: AICapability.IMMIGRATION_SCORING,
}


class WorkAuthorization(StrEnum):
    CITIZEN = "citizen"
    PERMANENT_RESIDENT = "permanent_resident"
    PGWP = "pgwp"
    WORK_PERMIT = "work_permit"
    NEEDS_SPONSORSHIP = "needs_sponsorship"


class RemotePreference(StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    ANY = "any"


class JobCategory(StrEnum):
    """Resume / role families — used by job matching and resume selection."""

    PRODUCTION = "production"
    CONSTRUCTION = "construction"
    IT = "it"
    AI = "ai"
    GENERAL = "general"


class ResumeLabel(StrEnum):
    """Canonical master resume labels — one per category per user."""

    PRODUCTION = "Production Resume"
    CONSTRUCTION = "Construction Resume"
    IT = "IT Resume"
    AI = "AI Resume"
    GENERAL = "General Resume"


LABEL_TO_CATEGORY: dict[str, JobCategory] = {
    ResumeLabel.PRODUCTION.value: JobCategory.PRODUCTION,
    ResumeLabel.CONSTRUCTION.value: JobCategory.CONSTRUCTION,
    ResumeLabel.IT.value: JobCategory.IT,
    ResumeLabel.AI.value: JobCategory.AI,
    ResumeLabel.GENERAL.value: JobCategory.GENERAL,
}


class CanadianProvince(StrEnum):
    """Canadian province/territory codes for location and immigration filtering."""

    AB = "AB"
    BC = "BC"
    MB = "MB"
    NB = "NB"
    NL = "NL"
    NS = "NS"
    NT = "NT"
    NU = "NU"
    ON = "ON"
    PE = "PE"
    QC = "QC"
    SK = "SK"
    YT = "YT"


class JobSourceType(StrEnum):
    """How jobs are ingested from a configured source."""

    MANUAL = "manual"
    API = "api"
    SCRAPER = "scraper"


class JobSourcePreset(StrEnum):
    """Canonical built-in job source identifiers — stable across all layers."""

    JOB_BANK_CANADA = "job_bank_canada"
    WORKPEI = "workpei"
    INDEED = "indeed"
    COMPANY_CAREER_PAGES = "company_career_pages"
    MANUAL_URL_IMPORT = "manual_url_import"


class JobStatus(StrEnum):
    """Lifecycle state of a stored job posting."""

    NEW = "new"
    ACTIVE = "active"
    DUPLICATE = "duplicate"
    ARCHIVED = "archived"
    SCORED = "scored"
    DOCUMENTS_READY = "documents_ready"
    APPLIED = "applied"


class ApplicationStatus(StrEnum):
    """Lifecycle state of generated application documents."""

    DRAFT = "draft"
    GENERATED = "generated"
    APPROVED = "approved"
    SUBMITTED = "submitted"
    FAILED = "failed"
    WITHDRAWN = "withdrawn"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class ReviewDecision(StrEnum):
    """User decision when reviewing generated application documents."""

    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_REVISION = "request_revision"


class SubmissionMethod(StrEnum):
    """How an application was submitted to the employer."""

    MANUAL = "manual"
    EMAIL = "email"
    COMPANY_PORTAL = "company_portal"
    JOB_BANK = "job_bank"
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    OTHER = "other"


class DocumentType(StrEnum):
    """Types of per-job application artifacts."""

    TAILORED_RESUME = "tailored_resume"
    COVER_LETTER = "cover_letter"
    EMAIL = "email"
    ATS_REPORT = "ats_report"


class AgentRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowType(StrEnum):
    SINGLE_JOB = "single_job"
    BATCH_INTELLIGENCE = "batch_intelligence"
    DOCUMENT_GENERATION = "document_generation"
