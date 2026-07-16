from typing import Any

from pydantic import BaseModel, Field


class AIStatusResponse(BaseModel):
    ai_enabled: bool
    providers: dict[str, bool]
    capabilities: list[str]
    prompts_synced: int
    prompts_total: int


class JobClassifyRequest(BaseModel):
    title: str = Field(..., min_length=1)
    company: str = ""
    location: str = ""
    description: str = ""
    remote_type: str | None = None


class JobClassifyResponse(BaseModel):
    classification: dict[str, Any]


class PromptSyncResponse(BaseModel):
    synced: int
    unchanged: int
    errors: list[dict[str, str]]
