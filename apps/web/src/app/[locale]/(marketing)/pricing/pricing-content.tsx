"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { MarketingFooter, MarketingHeader } from "@/components/marketing/marketing-chrome";
import { Button } from "@/components/ui/button";
import { PLANS } from "@careeros/shared";
import { createClient } from "@/lib/supabase/client";

function ProCtaButton() {
  const t = useTranslations("pricing");
  const tb = useTranslations("billing");
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    createClient()
      .auth.getUser()
      .then(({ data }) => setLoggedIn(Boolean(data.user)));
  }, []);

  async function checkout() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/billing/checkout", { method: "POST" });
      if (!res.ok) {
        const json = await res.json().catch(() => ({}));
        setError(json.error || tb("stripeNotConfigured"));
        return;
      }
      const data = await res.json();
      if (data.url) window.location.href = data.url;
      else setError(data.error || tb("checkoutFailed"));
    } catch {
      setError(tb("checkoutFailed"));
    } finally {
      setLoading(false);
    }
  }

  if (loggedIn === null) {
    return (
      <Button className="w-full" disabled>
        {t("upgradeToPro")}
      </Button>
    );
  }

  if (loggedIn) {
    return (
      <div className="space-y-2">
        <Button className="w-full" onClick={checkout} disabled={loading}>
          {loading ? tb("redirecting") : t("upgradeToPro")}
        </Button>
        {error && <p className="text-center text-sm text-destructive">{error}</p>}
      </div>
    );
  }

  return (
    <Button asChild className="w-full">
      <Link href="/signup?plan=pro">{t("signupForPro")}</Link>
    </Button>
  );
}

export default function PricingContent() {
  const t = useTranslations("pricing");
  const searchParams = useSearchParams();
  const cancelled = searchParams.get("cancelled");

  return (
    <div className="flex min-h-screen flex-col">
      <MarketingHeader />
      <main className="mx-auto max-w-4xl flex-1 px-4 py-16">
        <h1 className="mb-2 text-center text-3xl font-bold">{t("title")}</h1>
        <p className="mb-10 text-center text-muted-foreground">{t("subtitle")}</p>
        {(cancelled || searchParams.get("checkout") === "cancel") && (
          <p className="mb-6 text-center text-sm text-muted-foreground">{t("checkoutCancelled")}</p>
        )}

        <div className="grid gap-6 md:grid-cols-2">
          <div className="rounded-xl border p-6">
            <h2 className="text-xl font-semibold">{PLANS.free.label}</h2>
            <p className="mt-2 text-3xl font-bold">$0</p>
            <ul className="mt-6 space-y-2 text-sm text-muted-foreground">
              {PLANS.free.features.map((f) => (
                <li key={f}>✓ {f}</li>
              ))}
            </ul>
            <Button asChild variant="outline" className="mt-8 w-full">
              <Link href="/signup">{t("getStarted")}</Link>
            </Button>
          </div>

          <div className="rounded-xl border-2 border-primary p-6 shadow-md">
            <p className="text-xs font-medium uppercase text-primary">{t("mostPopular")}</p>
            <h2 className="text-xl font-semibold">{PLANS.pro.label}</h2>
            <p className="mt-2 text-3xl font-bold">
              ${PLANS.pro.priceMonthlyCad}{" "}
              <span className="text-base font-normal text-muted-foreground">CAD/mo</span>
            </p>
            <ul className="mt-6 space-y-2 text-sm text-muted-foreground">
              {PLANS.pro.features.map((f) => (
                <li key={f}>✓ {f}</li>
              ))}
            </ul>
            <div className="mt-8 space-y-2">
              <ProCtaButton />
              <p className="text-center text-xs text-muted-foreground">{t("loginHint")}</p>
            </div>
          </div>
        </div>
      </main>
      <MarketingFooter />
    </div>
  );
}
