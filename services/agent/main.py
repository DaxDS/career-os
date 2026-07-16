"""CareerOS agent worker — FastAPI pipeline."""

from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from config import settings
from graphs.discovery import run_discovery
from graphs.dispatch import run_dispatch
from graphs.pathway_report import run_pathway_report
from graphs.tailoring import run_tailoring
from lib.plan_limits import PlanLimitExceeded

app = FastAPI(
    title="CareerOS Agent",
    description="LangGraph pipeline worker for job discovery, NOC classification, matching, and tailoring.",
    version="0.4.0",
)


class HealthResponse(BaseModel):
    status: str
    phase: str


class UserIdRequest(BaseModel):
    user_id: str


class MatchRequest(BaseModel):
    user_id: str
    match_id: str


class ApplicationRequest(BaseModel):
    user_id: str
    application_id: str


class GraphResponse(BaseModel):
    ok: bool
    result: dict


def verify_agent_secret(x_agent_secret: str | None = Header(default=None)) -> None:
    if settings.agent_api_secret and x_agent_secret != settings.agent_api_secret:
        raise HTTPException(status_code=401, detail="Invalid agent secret")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", phase="4-monetization-polish")


@app.post("/graphs/discovery", response_model=GraphResponse, dependencies=[Depends(verify_agent_secret)])
async def discovery(body: UserIdRequest) -> GraphResponse:
    try:
        stats = run_discovery(body.user_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return GraphResponse(ok=True, result=stats)


@app.post("/graphs/tailoring", response_model=GraphResponse, dependencies=[Depends(verify_agent_secret)])
async def tailoring(body: MatchRequest) -> GraphResponse:
    try:
        result = run_tailoring(body.user_id, body.match_id)
    except PlanLimitExceeded as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return GraphResponse(ok=True, result=result)


@app.post("/graphs/pathway-report", response_model=GraphResponse, dependencies=[Depends(verify_agent_secret)])
async def pathway_report(body: UserIdRequest) -> GraphResponse:
    try:
        result = run_pathway_report(body.user_id)
    except PlanLimitExceeded as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return GraphResponse(ok=True, result=result)


@app.post("/graphs/dispatch", response_model=GraphResponse, dependencies=[Depends(verify_agent_secret)])
async def dispatch(body: ApplicationRequest) -> GraphResponse:
    try:
        result = run_dispatch(body.user_id, body.application_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return GraphResponse(ok=True, result=result)
