import { NextResponse } from "next/server";

import { createClient } from "@/lib/supabase/server";
import { getAppUrl, getStripe } from "@/lib/stripe";

/**
 * One-time checkout for a single PR pathway report.
 *
 * Separate from /api/billing/checkout, which opens a `subscription` session for the
 * Pro plan. A first-time visitor is far likelier to pay once for a concrete artifact
 * than to start a recurring charge, so this is the lower-friction entry point.
 *
 * Requires STRIPE_SECRET_KEY and STRIPE_PRICE_REPORT (a one-time price, not recurring).
 */
export async function POST() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const priceId = process.env.STRIPE_PRICE_REPORT?.trim();
  const secretKey = process.env.STRIPE_SECRET_KEY?.trim();

  if (!secretKey || !priceId) {
    return NextResponse.json(
      {
        error:
          "One-time report checkout is not configured. Set STRIPE_PRICE_REPORT to a one-time price ID.",
        code: "STRIPE_NOT_CONFIGURED",
      },
      { status: 503 }
    );
  }

  const appUrl = getAppUrl();

  try {
    const stripe = getStripe();
    const session = await stripe.checkout.sessions.create({
      mode: "payment",
      client_reference_id: user.id,
      customer_email: user.email ?? undefined,
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: `${appUrl}/pathways?purchase=success`,
      cancel_url: `${appUrl}/pathways?purchase=cancel`,
      metadata: { product: "pathway_report", user_id: user.id },
    });

    if (!session.url) {
      return NextResponse.json(
        { error: "Failed to create checkout session", code: "CHECKOUT_FAILED" },
        { status: 502 }
      );
    }

    return NextResponse.json({ url: session.url });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Checkout failed";
    console.error("[billing/report-checkout]", message);
    const userMessage = message.includes("Invalid API Key")
      ? "Payment provider misconfigured — contact support"
      : message;
    return NextResponse.json({ error: userMessage, code: "CHECKOUT_FAILED" }, { status: 502 });
  }
}
