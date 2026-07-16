from enum import StrEnum


class PipelineTrigger(StrEnum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class PipelineScope(StrEnum):
    ALL = "all"
    SOURCE = "source"
    COMPANY = "company"
    JOB = "job"


class PipelineRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStep(StrEnum):
    SEARCH_JOBS = "search_jobs"
    IMPORT_JOBS = "import_jobs"
    DEDUPLICATE = "deduplicate"
    CLASSIFICATION = "classification"
    IMMIGRATION_SCORING = "immigration_scoring"
    ATS_ANALYSIS = "ats_analysis"
    RESUME_SELECTION = "resume_selection"
    RESUME_TAILORING = "resume_tailoring"
    COVER_LETTER = "cover_letter"
    RECRUITER_EMAIL = "recruiter_email"
    APPLICATION_PACKAGE = "application_package"
    REVIEW_QUEUE = "review_queue"
    NOTIFY_USER = "notify_user"


REVIEW_READY_MESSAGE = "Today's applications are ready for review."
