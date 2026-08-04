"use client";

import { useEffect, useState } from "react";
import { useRouter } from "@/i18n/routing";
import { useTranslations } from "next-intl";
import { createClient } from "@/lib/supabase/client";
import { OnboardingWizard } from "@/components/onboarding/onboarding-wizard";
import { IMMIGRATION_STATUS_OPTIONS } from "@/lib/onboarding/constants";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function PermitStatusStep() {
  const t = useTranslations("onboarding.permitStatus");
  const tc = useTranslations("common");
  const router = useRouter();
  const [status, setStatus] = useState("pgwp");
  const [permitExpiry, setPermitExpiry] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // This step previously mounted with hardcoded defaults and never read what was
  // already saved. Going Back and forward again silently overwrote a real status with
  // "pgwp" and wiped the permit expiry — which drives the expiry warning and the
  // work-authorisation filters.
  useEffect(() => {
    async function load() {
      const supabase = createClient();
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user) return;

      const { data } = await supabase
        .from("profiles")
        .select("status, permit_expiry")
        .eq("id", user.id)
        .single();

      if (data?.status) setStatus(data.status);
      if (data?.permit_expiry) setPermitExpiry(String(data.permit_expiry).slice(0, 10));
      setLoading(false);
    }
    load();
  }, []);

  const needsExpiry = status === "pgwp" || status === "closed_permit" || status === "open_permit";

  async function handleContinue() {
    setError(null);

    if (needsExpiry && permitExpiry) {
      const expiry = new Date(`${permitExpiry}T00:00:00Z`);
      if (Number.isNaN(expiry.getTime())) {
        setError("That expiry date isn't valid.");
        return;
      }
    }

    setSaving(true);
    const supabase = createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) {
      setSaving(false);
      router.push("/login");
      return;
    }

    const { error: updateError } = await supabase
      .from("profiles")
      .update({
        status,
        permit_expiry: needsExpiry ? permitExpiry || null : null,
        onboarding_step: 4,
      })
      .eq("id", user.id);

    if (updateError) {
      setError(updateError.message);
      setSaving(false);
      return;
    }

    router.push("/onboarding/languages");
  }

  if (loading) return <p>{tc("loading")}</p>;

  const expiryIsPast =
    needsExpiry && permitExpiry && new Date(`${permitExpiry}T00:00:00Z`).getTime() < Date.now();

  return (
    <OnboardingWizard currentStep={3}>
      <Card>
        <CardHeader>
          <CardTitle>{t("title")}</CardTitle>
          <CardDescription>{t("description")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="status">{t("statusLabel")}</Label>
            <select
              id="status"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              {IMMIGRATION_STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {needsExpiry && (
            <div className="space-y-2">
              <Label htmlFor="expiry">{t("expiryLabel")}</Label>
              <Input
                id="expiry"
                type="date"
                value={permitExpiry}
                onChange={(e) => setPermitExpiry(e.target.value)}
              />
              {expiryIsPast && (
                <p className="text-xs text-amber-600 dark:text-amber-400">
                  That date is in the past. If your permit has expired, your options differ
                  considerably — worth confirming with a licensed RCIC.
                </p>
              )}
            </div>
          )}

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="flex gap-2">
            <Button variant="outline" onClick={() => router.push("/onboarding/noc-mapping")}>
              {tc("back")}
            </Button>
            <Button onClick={handleContinue} disabled={saving}>
              {saving ? tc("loading") : tc("continue")}
            </Button>
          </div>
        </CardContent>
      </Card>
    </OnboardingWizard>
  );
}
