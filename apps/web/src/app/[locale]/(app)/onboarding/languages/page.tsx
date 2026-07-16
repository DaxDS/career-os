"use client";

import { useRouter } from "@/i18n/routing";
import { useTranslations } from "next-intl";
import { createClient } from "@/lib/supabase/client";
import { OnboardingWizard } from "@/components/onboarding/onboarding-wizard";
import {
  CANADIAN_PROVINCES,
  LANGUAGE_PROFICIENCY_OPTIONS,
} from "@/lib/onboarding/constants";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useState } from "react";

export default function LanguagesStep() {
  const t = useTranslations("onboarding.languages");
  const tc = useTranslations("common");
  const router = useRouter();
  const [languageEn, setLanguageEn] = useState("intermediate");
  const [languageFr, setLanguageFr] = useState("none");
  const [province, setProvince] = useState("ON");
  const [targetTitles, setTargetTitles] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleFinish() {
    setSaving(true);
    const supabase = createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) return;

    const titles = targetTitles
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    await supabase
      .from("profiles")
      .update({
        language_en: languageEn,
        language_fr: languageFr,
        province,
        target_titles: titles,
        onboarding_completed: true,
        onboarding_step: 5,
      })
      .eq("id", user.id);

    router.push("/dashboard");
    router.refresh();
  }

  return (
    <OnboardingWizard currentStep={4}>
      <Card>
        <CardHeader>
          <CardTitle>{t("title")}</CardTitle>
          <CardDescription>{t("description")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>{t("english")}</Label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={languageEn}
                onChange={(e) => setLanguageEn(e.target.value)}
              >
                {LANGUAGE_PROFICIENCY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label>{t("french")}</Label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={languageFr}
                onChange={(e) => setLanguageFr(e.target.value)}
              >
                {LANGUAGE_PROFICIENCY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="space-y-2">
            <Label>{t("province")}</Label>
            <select
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={province}
              onChange={(e) => setProvince(e.target.value)}
            >
              {CANADIAN_PROVINCES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <Label>{t("targetTitles")}</Label>
            <Input
              placeholder="Software Developer, Data Analyst"
              value={targetTitles}
              onChange={(e) => setTargetTitles(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">Comma-separated</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => router.push("/onboarding/permit-status")}>
              {tc("back")}
            </Button>
            <Button onClick={handleFinish} disabled={saving}>
              {saving ? tc("loading") : "Finish setup"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </OnboardingWizard>
  );
}
