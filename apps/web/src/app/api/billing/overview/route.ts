import { NextResponse } from "next/server";
import { monthStartIso, normalizePlan } from "@/lib/billing/plan-limits";
import { createClient } from "@/lib/supabase/server";
import { PLANS } from "@careeros/shared";

export async function GET() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { data: profile } = await supabase
    .from("profiles")
    .select("plan, plan_status, plan_renews_at, daily_send_cap, stripe_customer_id")
    .eq("id", user.id)
    .single();

  const plan = normalizePlan(profile?.plan);
  const planDef = PLANS[plan];

  const { count: tailoredUsed } = await supabase
    .from("applications")
    .select("*", { count: "exact", head: true })
    .eq("user_id", user.id)
    .gte("created_at", monthStartIso());

  return NextResponse.json({
    plan,
    plan_label: planDef.label,
    price_monthly_cad: planDef.priceMonthlyCad,
    plan_status: profile?.plan_status ?? null,
    plan_renews_at: profile?.plan_renews_at ?? null,
    daily_send_cap: profile?.daily_send_cap ?? planDef.dailySendCap,
    has_stripe_customer: Boolean(profile?.stripe_customer_id),
    stripe_checkout_available: Boolean(
      process.env.STRIPE_SECRET_KEY?.trim() && process.env.STRIPE_PRICE_PRO?.trim()
    ),
    stripe_test_mode: process.env.STRIPE_SECRET_KEY?.trim().startsWith("sk_test_") ?? false,
    limits: {
      tailored_applications_per_month: planDef.tailoredApplicationsPerMonth,
      daily_send_cap: planDef.dailySendCap,
    },
    usage: {
      tailored_applications: tailoredUsed ?? 0,
    },
    upgrade_available: plan === "free",
  });
}
