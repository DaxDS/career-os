"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { PLANS, type PlanTier } from "@careeros/shared";

interface BillingOverview {
  plan: PlanTier;
  plan_label: string;
  plan_status: string | null;
  plan_renews_at: string | null;
  daily_send_cap: number;
  has_stripe_customer: boolean;
  stripe_checkout_available?: boolean;
  stripe_test_mode?: boolean;
  limits: { tailored_applications_per_month: number | null; daily_send_cap: number };
  usage: { tailored_applications: number };
  upgrade_available: boolean;
}

function formatStatus(status: string | null, t: ReturnType<typeof useTranslations<"billing">>) {
  if (status === "active") return t("statusActive");
  if (status === "past_due") return t("statusPastDue");
  if (status === "canceled") return t("statusCanceled");
  return status;
}

async function readApiError(res: Response, fallback: string): Promise<string> {
  try {
    const json = (await res.json()) as { error?: string; code?: string };
    if (json.code === "STRIPE_NOT_CONFIGURED") return fallback;
    return json.error || fallback;
  } catch {
    return `${fallback} (${res.status})`;
  }
}

export function SettingsBillingCard() {
  const t = useTranslations("billing");
  const tc = useTranslations("common");
  const searchParams = useSearchParams();
  const checkout = searchParams.get("checkout");

  const [data, setData] = useState<BillingOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/billing/overview")
      .then(async (r) => {
        if (!r.ok) throw new Error(`overview ${r.status}`);
        return r.json();
      })
      .then(setData)
      .catch(() => setError(t("checkoutFailed")))
      .finally(() => setLoading(false));
  }, [t]);

  async function checkoutPro() {
    setActionLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/billing/checkout", { method: "POST" });
      if (!res.ok) {
        setError(await readApiError(res, t("stripeNotConfigured")));
        return;
      }
      const json = (await res.json()) as { url?: string; error?: string };
      if (json.url) {
        window.location.href = json.url;
        return;
      }
      setError(json.error || t("checkoutFailed"));
    } catch (e) {
      setError(e instanceof Error ? e.message : t("checkoutFailed"));
    } finally {
      setActionLoading(false);
    }
  }

  async function openPortal() {
    setActionLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/billing/portal", { method: "POST" });
      if (!res.ok) {
        setError(await readApiError(res, t("noBillingAccount")));
        return;
      }
      const json = (await res.json()) as { url?: string; error?: string };
      if (json.url) {
        window.location.href = json.url;
        return;
      }
      setError(json.error || t("noBillingAccount"));
    } catch (e) {
      setError(e instanceof Error ? e.message : t("noBillingAccount"));
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) return <p className="text-muted-foreground">{tc("loading")}</p>;

  const plan = data?.plan ?? "free";
  const limit = data?.limits?.tailored_applications_per_month;
  const used = data?.usage?.tailored_applications ?? 0;
  const pct = limit != null && limit > 0 ? Math.min(100, (used / limit) * 100) : 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {checkout === "success" && (
          <p className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900 dark:border-emerald-900/50 dark:bg-emerald-950/30 dark:text-emerald-100">
            {t("checkoutSuccess")}
          </p>
        )}
        {checkout === "cancel" && (
          <p className="rounded-md border bg-muted p-3 text-sm text-muted-foreground">
            {t("checkoutCancel")}
          </p>
        )}

        {data?.stripe_test_mode && data.stripe_checkout_available && (
          <p className="rounded-md border border-amber-200/80 bg-amber-50/80 p-3 text-sm text-amber-950 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-100">
            {t("stripeTestModeHint")}
          </p>
        )}

        <div>
          <p className="text-sm text-muted-foreground">{t("currentPlan")}</p>
          <p className="text-lg font-semibold">
            {plan === "pro" ? t("proPlan") : t("freePlan")}
            {plan === "pro" && (
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                {t("pricePerMonth", { price: PLANS.pro.priceMonthlyCad })}
              </span>
            )}
          </p>
          {data?.plan_status && (
            <p className="text-sm text-muted-foreground">{formatStatus(data.plan_status, t)}</p>
          )}
          {data?.plan_renews_at ? (
            <p className="text-sm text-muted-foreground">
              {t("renewalDate", {
                date: new Date(data.plan_renews_at).toLocaleDateString(),
              })}
            </p>
          ) : plan === "free" ? (
            <p className="text-sm text-muted-foreground">{t("noRenewal")}</p>
          ) : null}
        </div>

        <div>
          <p className="text-sm text-muted-foreground">{t("dailySendCap")}</p>
          <p className="font-medium">
            {t("sendsPerDay", { count: data?.daily_send_cap ?? PLANS[plan].dailySendCap })}
          </p>
        </div>

        <div>
          <div className="mb-2 flex justify-between text-sm">
            <span>{t("tailoredUsage")}</span>
            <span>
              {limit == null
                ? `${used} · ${t("tailoredUnlimited")}`
                : `${used} / ${limit}`}
            </span>
          </div>
          {limit != null && <Progress value={pct} />}
        </div>

        <div className="flex flex-wrap gap-2">
          {data?.upgrade_available ? (
            <Button onClick={checkoutPro} disabled={actionLoading}>
              {actionLoading ? t("redirecting") : t("upgradeToPro")}
            </Button>
          ) : data?.has_stripe_customer ? (
            <Button variant="outline" onClick={openPortal} disabled={actionLoading}>
              {actionLoading ? t("redirecting") : t("manageBilling")}
            </Button>
          ) : null}
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}
      </CardContent>
    </Card>
  );
}
