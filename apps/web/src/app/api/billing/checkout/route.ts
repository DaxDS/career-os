import { NextResponse } from "next/server";

import { createClient } from "@/lib/supabase/server";

import { getAppUrl, getStripe } from "@/lib/stripe";



export async function POST() {

  const supabase = await createClient();

  const {

    data: { user },

  } = await supabase.auth.getUser();

  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });



  const priceId = process.env.STRIPE_PRICE_PRO?.trim();

  const secretKey = process.env.STRIPE_SECRET_KEY?.trim();

  if (!secretKey || !priceId) {

    return NextResponse.json(

      { error: "Checkout not configured", code: "STRIPE_NOT_CONFIGURED" },

      { status: 503 }

    );

  }



  const appUrl = getAppUrl();



  try {

    const stripe = getStripe();

    const session = await stripe.checkout.sessions.create({

      mode: "subscription",

      client_reference_id: user.id,

      customer_email: user.email ?? undefined,

      line_items: [{ price: priceId, quantity: 1 }],

      success_url: `${appUrl}/settings?checkout=success`,

      cancel_url: `${appUrl}/settings?checkout=cancel`,

      metadata: { plan: "pro" },

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

    console.error("[billing/checkout]", message);

    const userMessage = message.includes("Invalid API Key")

      ? "Payment provider misconfigured — contact support"

      : message;

    return NextResponse.json(

      { error: userMessage, code: "CHECKOUT_FAILED" },

      { status: 502 }

    );

  }

}

