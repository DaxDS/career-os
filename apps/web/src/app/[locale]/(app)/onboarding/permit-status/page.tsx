"use client";

import { useRouter } from "@/i18n/routing";
import { useTranslations } from "next-intl";
import { createClient } from "@/lib/supabase/client";
import { OnboardingWizard } from "@/components/onboarding/onboarding-wizard";
import { IMMIGRATION_STATUS_OPTIONS } from "@/lib/onboarding/constants";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useState } from "react";

export default function PermitStatusStep() {
  const t = useTranslations("onboarding.permitStatus");
  const tc = useTranslations("common");
  const router = useRouter();
  const [status, setStatus] = useState("pgwp");
  const [permitExpiry, setPermitExpiry] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleContinue() {
    setSaving(true);
    const supabase = createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) return;

    await supabase
      .from("profiles")
      .update({
        status,
        permit_expiry: permitExpiry || null,
        onboarding_step: 4,
      })
      .eq("id", user.id);

    router.push("/onboarding/languages");
  }

  return (
    <OnboardingWizard currentStep={3}>
      <Card>
        <CardHeader>
          <CardTitle>{t("title")}</CardTitle>
          <CardDescription>{t("description")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>{t("statusLabel")}</Label>
            <select
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
          <div className="space-y-2">
            <Label>{t("expiryLabel")}</Label>
            <Input
              type="date"
              value={permitExpiry}
              onChange={(e) => setPermitExpiry(e.target.value)}
            />
          </div>
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
