from enum import StrEnum


class AutomationRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED_CAPTCHA = "paused_captcha"
    STOPPED_BEFORE_SUBMIT = "stopped_before_submit"
    COMPLETED = "completed"
    FAILED = "failed"


class BrowserSessionStatus(StrEnum):
    ACTIVE = "active"
    IDLE = "idle"
    EXPIRED = "expired"


class AutomationActionType(StrEnum):
    SESSION_RESTORE = "session_restore"
    NAVIGATE = "navigate"
    UPLOAD_RESUME = "upload_resume"
    UPLOAD_COVER_LETTER = "upload_cover_letter"
    FILL_EMAIL = "fill_email"
    FILL_FIELDS = "fill_fields"
    VALIDATION_ERROR = "validation_error"
    CAPTCHA_DETECTED = "captcha_detected"
    SCREENSHOT = "screenshot"
    SUBMIT = "submit"
    STOP_BEFORE_SUBMIT = "stop_before_submit"
    ERROR = "error"
    COMPLETE = "complete"
