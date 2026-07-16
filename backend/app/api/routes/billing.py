"""Billing and plan overview — Stripe checkout, webhook, and usage."""

import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.dependencies import get_current_user_id, get_db, get_plan_limit_service
from app.application.services.plan_limit_service import PlanLimitService
from app.domain.plans import PLANS, plan_or_free
from app.infrastructure.db.models import User
from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["billing"])


class BillingOverviewResponse(BaseModel):
    plan: str
    plan_label: str
    price_monthly_cad: int | None
    limits: dict[str, int]
    usage: dict[str, int]
    features: list[str]
    upgrade_available: bool


class CheckoutSessionRequest(BaseModel):
    plan: str = "pro"


class CheckoutSessionResponse(BaseModel):
    url: str


@router.get("/billing/overview", response_model=BillingOverviewResponse)
def billing_overview(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    limits_svc: PlanLimitService = Depends(get_plan_limit_service),
):
    plan_key = plan_or_free(db.scalar(select(User.plan_tier).where(User.id == user_id)))
    plan = PLANS[plan_key]

    return BillingOverviewResponse(
        plan=plan_key,
        plan_label=plan["plan_label"],
        price_monthly_cad=plan["price_monthly_cad"],
        limits=plan["limits"],
        usage={
            "ai_pipeline_runs": limits_svc.pipeline_runs_this_month(user_id),
            "jobs_this_month": limits_svc.jobs_this_month(user_id),
            "resumes": limits_svc.active_resume_count(user_id),
        },
        features=plan["features"],
        upgrade_available=plan["upgrade_available"],
    )


@router.post("/billing/create-checkout-session", response_model=CheckoutSessionResponse)
def create_checkout_session(
    body: CheckoutSessionRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    settings: Settings = Depends(get_settings),
):
    price_by_plan = {"pro": settings.stripe_price_pro, "team": settings.stripe_price_team}
    if body.plan not in price_by_plan:
        raise HTTPException(status_code=400, detail="Unknown plan — must be 'pro' or 'team'")
    price_id = price_by_plan[body.plan]
    if not settings.stripe_secret_key or not price_id:
        raise HTTPException(status_code=503, detail="Stripe is not configured for this plan yet")

    payload = urllib.parse.urlencode(
        {
            "mode": "subscription",
            "success_url": settings.stripe_checkout_success_url,
            "cancel_url": settings.stripe_checkout_cancel_url,
            "client_reference_id": str(user_id),
            "metadata[plan]": body.plan,
            "line_items[0][price]": price_id,
            "line_items[0][quantity]": "1",
        }
    ).encode()
    request = urllib.request.Request(
        "https://api.stripe.com/v1/checkout/sessions",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.stripe_secret_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise HTTPException(status_code=502, detail=f"Stripe error: {detail}") from exc
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Stripe unreachable: {exc}") from exc

    checkout_url = data.get("url")
    if not checkout_url:
        raise HTTPException(status_code=502, detail="Stripe did not return a checkout URL")
    return CheckoutSessionResponse(url=checkout_url)


def _verify_stripe_signature(
    payload: bytes, header: str, secret: str, tolerance_seconds: int = 300
) -> bool:
    """Verify a Stripe-Signature header (t=...,v1=...) without the Stripe SDK."""
    try:
        pairs = [part.split("=", 1) for part in header.split(",")]
        timestamp = next(value for key, value in pairs if key == "t")
        signatures = [value for key, value in pairs if key == "v1"]
    except (ValueError, StopIteration):
        return False
    if not signatures:
        return False
    if abs(time.time() - int(timestamp)) > tolerance_seconds:
        return False
    signed_payload = timestamp.encode() + b"." + payload
    expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, sig) for sig in signatures)


@router.post("/billing/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook is not configured")

    payload = await request.body()
    signature_header = request.headers.get("stripe-signature", "")
    if not _verify_stripe_signature(payload, signature_header, settings.stripe_webhook_secret):
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    try:
        event = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid payload") from exc

    if event.get("type") == "checkout.session.completed":
        session = event.get("data", {}).get("object", {})
        client_reference_id = session.get("client_reference_id")
        plan = (session.get("metadata") or {}).get("plan", "")
        if not client_reference_id or plan not in PLANS:
            logger.warning(
                "stripe_webhook_unusable_session",
                client_reference_id=client_reference_id,
                plan=plan,
            )
            return {"received": True}
        user = db.get(User, uuid.UUID(client_reference_id))
        if user is None:
            logger.warning("stripe_webhook_user_not_found", user_id=client_reference_id)
            return {"received": True}
        user.plan_tier = plan
        db.commit()
        logger.info("plan_tier_updated", user_id=str(user.id), plan=plan)

    return {"received": True}
