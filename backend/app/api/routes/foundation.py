import uuid

from fastapi import APIRouter, Depends

from app.application.ports.audit import AuditPort
from app.application.ports.prompts import PromptRegistryPort
from app.application.ports.storage import FileStoragePort
from app.config import Settings, get_settings
from app.dependencies import get_audit_log, get_current_user_id, get_file_storage, get_prompt_registry
from app.domain.v1_constants import CURRENT_LAYER

router = APIRouter(tags=["foundation"])


@router.get("/foundation/status")
def foundation_status(
    settings: Settings = Depends(get_settings),
    storage: FileStoragePort = Depends(get_file_storage),
    prompts: PromptRegistryPort = Depends(get_prompt_registry),
) -> dict:
    """Verify Layer 0 foundation subsystems are wired."""
    registered = prompts.list_registered_prompts()
    return {
        "layer": CURRENT_LAYER,
        "audit_logging": "ready",
        "file_storage": {
            "root": str(settings.storage_path),
            "resumes": str(settings.resumes_path),
            "applications": str(settings.applications_path),
            "templates": str(settings.templates_path),
        },
        "prompt_registry": {
            "root": str(prompts.get_prompts_root()),
            "registered_count": len(registered),
            "prompts": registered,
        },
    }


@router.get("/foundation/audit")
def query_audit_log(
    entity_type: str | None = None,
    entity_id: str | None = None,
    action: str | None = None,
    limit: int = 50,
    user_id: uuid.UUID = Depends(get_current_user_id),
    audit: AuditPort = Depends(get_audit_log),
) -> dict:
    from app.domain.enums import AuditAction

    audit_action = AuditAction(action) if action else None
    entries = audit.query(
        entity_type=entity_type,
        entity_id=entity_id,
        action=audit_action,
        limit=limit,
    )
    return {"entries": entries, "count": len(entries)}
