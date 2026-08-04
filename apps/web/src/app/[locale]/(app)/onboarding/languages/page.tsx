"use client";

import { useEffect, useState } from "react";
import { useRouter } from "@/i18n/routing";
import { useTranslations } from "next-intl";
import { createClient } from "@/lib/supabase/client";
import { OnboardingWizard } from "@/components/onboarding/onboarding-wizard";
import { CANADIAN_PROVINCES } from "@/lib/onboarding/constants";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EDUCATION_LABELS, EDUCATION_ORDER, proficiencyFromClb } from "@/lib/crs/grid";

const ABILITIES = ["reading", "writing", "listening", "speaking"] as const;

type Scores = Record<(typeof ABILITIES)[number], number>;

const ZERO: Scores = { reading: 0, writing: 0, listening: 0, speaking: 0 };

function ScoreRow({
  idPrefix,
  values,
  onChange,
}: {
  idPrefix: string;
  values: Scores;
  onChange: (ability: (typeof ABILITIES)[number], value: number) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {ABILITIES.map((ability) => (
        <div key={ability}>
          <Label htmlFor={`${idPrefix}-${ability}`} className="text-xs capitalize text-muted-foreground">
            {ability}
          </Label>
          <Input
            id={`${idPrefix}-${ability}`}
            type="number"
            min={0}
            max={12}
            value={values[ability]}
            onChange={(e) => onChange(ability, Math.min(12, Math.max(0, Number(e.target.value))))}
          />
        </div>
      ))}
    </div>
  );
}

export default function LanguagesStep() {
  const t = useTranslations("onboarding.languages");
  const tc = useTranslations("common");
  const router = useRouter();

  const [dateOfBirth, setDateOfBirth] = useState("");
  const [educationLevel, setEducationLevel] = useState("");
  const [english, setEnglish] = useState<Scores>({ ...ZERO });
  const [french, setFrench] = useState<Scores>({ ...ZERO });
  const [province, setProvince] = useState("ON");
  const [targetTitles, setTargetTitles] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const supabase = createClient();
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user) return;
      const { data } = await supabase.from("profiles").select("*").eq("id", user.id).single();
      if (!data) return;
      if (data.date_of_birth) setDateOfBirth(String(data.date_of_birth).slice(0, 10));
      if (data.education_level) setEducationLevel(data.education_level);
      if (data.province) setProvince(data.province);
      setEnglish({
        reading: data.clb_en_reading ?? 0,
        writing: data.clb_en_writing ?? 0,
        listening: data.clb_en_listening ?? 0,
        speaking: data.clb_en_speaking ?? 0,
      });
      setFrench({
        reading: data.nclc_fr_reading ?? 0,
        writing: data.nclc_fr_writing ?? 0,
        listening: data.nclc_fr_listening ?? 0,
        speaking: data.nclc_fr_speaking ?? 0,
      });
    }
    load();
  }, []);

  async function handleFinish() {
    setError(null);
    if (!dateOfBirth || !educationLevel) {
      setError("Date of birth and education are both scored by IRCC — please fill them in.");
      return;
    }

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

    const { error: updateError } = await supabase
      .from("profiles")
      .update({
        date_of_birth: dateOfBirth,
        education_level: educationLevel,
        clb_en_reading: english.reading,
        clb_en_writing: english.writing,
        clb_en_listening: english.listening,
        clb_en_speaking: english.speaking,
        nclc_fr_reading: french.reading,
        nclc_fr_writing: french.writing,
        nclc_fr_listening: french.listening,
        nclc_fr_speaking: french.speaking,
        // Derived so the older matching code keeps working without asking the same
        // question twice in a different vocabulary.
        language_en: proficiencyFromClb(english),
        language_fr: proficiencyFromClb(french),
        province,
        target_titles: titles,
        crs_profile_completed: true,
        onboarding_completed: true,
        onboarding_step: 5,
      })
      .eq("id", user.id);

    if (updateError) {
      setError(updateError.message);
      setSaving(false);
      return;
    }

    // Land on the report rather than a dashboard — it is the reason they signed up.
    router.push("/pathways");
    router.refresh();
  }

  return (
    <OnboardingWizard currentStep={4}>
      <Card>
        <CardHeader>
          <CardTitle>{t("title")}</CardTitle>
          <CardDescription>
            The last few things IRCC scores you on. These four numbers and your age carry more CRS points
            than anything else on this form.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="dob">Date of birth</Label>
              <Input
                id="dob"
                type="date"
                value={dateOfBirth}
                onChange={(e) => setDateOfBirth(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">Worth up to 110 points, peaking at ages 20-29.</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="education">Highest completed education</Label>
              <select
                id="education"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={educationLevel}
                onChange={(e) => setEducationLevel(e.target.value)}
              >
                <option value="">Select…</option>
                {EDUCATION_ORDER.map((level) => (
                  <option key={level} value={level}>
                    {EDUCATION_LABELS[level]}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-sm font-semibold">English — CLB level per ability</Label>
            <p className="text-xs text-muted-foreground">
              From your IELTS or CELPIP report. Each ability is scored separately, so enter all four — CLB 9
              across the board is worth 128 more points than CLB 6.
            </p>
            <ScoreRow
              idPrefix="en"
              values={english}
              onChange={(ability, value) => setEnglish((v) => ({ ...v, [ability]: value }))}
            />
          </div>

          <div className="space-y-2">
            <Label className="text-sm font-semibold">French — NCLC level per ability</Label>
            <p className="text-xs text-muted-foreground">
              Leave at 0 if you have no French test. NCLC 7+ in all four unlocks French-category rounds,
              which have had the lowest cut-offs of any route.
            </p>
            <ScoreRow
              idPrefix="fr"
              values={french}
              onChange={(ability, value) => setFrench((v) => ({ ...v, [ability]: value }))}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="province">{t("province")}</Label>
              <select
                id="province"
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
              <Label htmlFor="titles">{t("targetTitles")}</Label>
              <Input
                id="titles"
                placeholder="Software Developer, Data Analyst"
                value={targetTitles}
                onChange={(e) => setTargetTitles(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">Comma-separated</p>
            </div>
          </div>

          {error && (
            <p className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </p>
          )}

          <div className="flex gap-2">
            <Button variant="outline" onClick={() => router.push("/onboarding/permit-status")}>
              {tc("back")}
            </Button>
            <Button onClick={handleFinish} disabled={saving}>
              {saving ? tc("loading") : "Finish and see my score"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </OnboardingWizard>
  );
}
