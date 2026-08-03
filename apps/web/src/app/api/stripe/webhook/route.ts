import { NextResponse } from "next/server";
import type Stripe from "stripe";
import { createAdminClient } from "@/lib/supabase/admin";
import { getStripe } from "@/lib/stripe";
import { PLANS } from "@careeros/shared";

export const runtime = "nodejs";

function mapSubscriptionStatus(status: Stripe.Subscription.Status): string | null {
  if (status === "active" || status === "trialing") return "active";
  if (status === "past_due" || status === "unpaid") return "past_due";
  if (status === "canceled" || status === "incomplete_expired") return "canceled";
  return status;
}

async function setProPlan(userId: string, customerId: string | null, subscriptionId: string | null) {
  const admin = createAdminClient();
  await admin
    .from("profiles")
    .update({
      plan: "pro",
      stripe_customer_id: customerId,
      stripe_subscription_id: subscriptionId,
      plan_status: "active",
      daily_send_cap: PLANS.pro.dailySendCap,
    })
    .eq("id", userId);
}

async function setFreePlanBySubscriptionId(subscriptionId: string) {
  const admin = createAdminClient();
  await admin
    .from("profiles")
    .update({
      plan: "free",
      plan_status: "canceled",
      stripe_subscription_id: null,
      daily_send_cap: PLANS.free.dailySendCap,
    })
    .eq("stripe_subscription_id", subscriptionId);
}

/**
 * Record a one-time report purchase and grant exactly one credit.
 *
 * Stripe redelivers webhooks on any non-2xx response, so this must be idempotent.
 * The RPC inserts against a unique session id and only increments the credit when
 * that insert actually created a row, making replays no-ops.
 */
async function grantReportCredit(userId: string, session: Stripe.Checkout.Session) {
  const admin = createAdminClient();
  const { error } = await admin.rpc("grant_report_credit", {
    p_user_id: userId,
    p_session_id: session.id,
    p_payment_intent:
      typeof session.payment_intent === "string"
        ? session.payment_intent
        : session.payment_intent?.id ?? null,
    p_amount_total: session.amount_total ?? null,
    p_currency: session.currency ?? null,
  });

  if (error) {
    // Surface the failure so Stripe retries rather than silently losing a paid credit.
    console.error("[stripe/webhook] grant_report_credit failed", error.message);
    throw new Error(`Failed to grant report credit: ${error.message}`);
  }
}

function subscriptionRenewsAt(subscription: Stripe.Subscription): string | null {
  const periodEnd = subscription.items?.data?.[0]?.current_period_end;
  return periodEnd ? new Date(periodEnd * 1000).toISOString() : null;
}

async function syncSubscription(subscription: Stripe.Subscription) {
  const admin = createAdminClient();
  const renewsAt = subscriptionRenewsAt(subscription);
  const planStatus = mapSubscriptionStatus(subscription.status);
  const isActive = planStatus === "active";

  await admin
    .from("profiles")
    .update({
      plan: isActive ? "pro" : "free",
      plan_status: planStatus,
      plan_renews_at: renewsAt,
      stripe_customer_id:
        typeof subscription.customer === "string" ? subscription.customer : subscription.customer?.id,
      stripe_subscription_id: subscription.id,
      daily_send_cap: isActive ? PLANS.pro.dailySendCap : PLANS.free.dailySendCap,
    })
    .eq("stripe_subscription_id", subscription.id);
}

export async function POST(request: Request) {
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
  if (!webhookSecret) {
    return NextResponse.json({ error: "Webhook not configured" }, { status: 503 });
  }

  const body = await request.text();
  const signature = request.headers.get("stripe-signature");
  if (!signature) {
    return NextResponse.json({ error: "Missing signature" }, { status: 400 });
  }

  let event: Stripe.Event;
  try {
    event = getStripe().webhooks.constructEvent(body, signature, webhookSecret);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Invalid signature";
    return NextResponse.json({ error: message }, { status: 400 });
  }

  switch (event.type) {
    case "checkout.session.completed": {
      const session = event.data.object as Stripe.Checkout.Session;
      const userId = session.client_reference_id;
      if (!userId) break;

      // Branch on mode. A one-time report purchase must NOT grant the Pro plan —
      // without this check any completed session upgraded the buyer to a full
      // subscription for the price of a single report.
      if (session.mode === "payment") {
        await grantReportCredit(userId, session);
        break;
      }

      if (session.mode === "subscription") {
        await setProPlan(
          userId,
          typeof session.customer === "string" ? session.customer : session.customer?.id ?? null,
          typeof session.subscription === "string" ? session.subscription : session.subscription?.id ?? null
        );
        if (session.subscription && typeof session.subscription === "string") {
          const sub = await getStripe().subscriptions.retrieve(session.subscription);
          await syncSubscription(sub);
        }
      }
      break;
    }
    case "customer.subscription.updated": {
      const subscription = event.data.object as Stripe.Subscription;
      await syncSubscription(subscription);
      break;
    }
    case "customer.subscription.deleted": {
      const subscription = event.data.object as Stripe.Subscription;
      await setFreePlanBySubscriptionId(subscription.id);
      break;
    }
    default:
      break;
  }

  return NextResponse.json({ received: true });
}
