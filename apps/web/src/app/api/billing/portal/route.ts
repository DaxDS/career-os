import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { getAppUrl, getStripe } from "@/lib/stripe";

export async function POST() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { data: profile } = await supabase
    .from("profiles")
    .select("stripe_customer_id")
    .eq("id", user.id)
    .single();

  const customerId = profile?.stripe_customer_id;
  if (!customerId) {
    return NextResponse.json(
      { error: "No billing account yet. Subscribe to Pro first." },
      { status: 400 }
    );
  }

  if (!process.env.STRIPE_SECRET_KEY) {
    return NextResponse.json({ error: "Stripe is not configured" }, { status: 503 });
  }

  const session = await getStripe().billingPortal.sessions.create({
    customer: customerId,
    return_url: `${getAppUrl()}/settings`,
  });

  return NextResponse.json({ url: session.url });
}
