"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EDUCATION_LABELS, EDUCATION_ORDER } from "@/lib/crs/grid";

export interface CrsProfileValues {
  date_of_birth: string;
  education_level: string;
  clb_en_reading: number;
  clb_en_writing: number;
  clb_en_listening: number;
  clb_en_speaking: number;
  nclc_fr_reading: number;
  nclc_fr_writing: number;
  nclc_fr_listening: number;
  nclc_fr_speaking: number;
  foreign_experience_months: number;
  has_accompanying_spouse: boolean;
  spouse_education_level: string;
  spouse_clb_reading: number;
  spouse_clb_writing: number;
  spouse_clb_listening: number;
  spouse_clb_speaking: number;
  spouse_canadian_experience_years: number;
  has_provincial_nomination: boolean;
  sibling_in_canada: boolean;
  canadian_study_credential: string;
  trades_certificate: boolean;
}

const ABILITIES = ["reading", "writing", "listening", "speaking"] as const;

const CLB_HELP =
  "Enter your CLB level per ability (0-12). IELTS and CELPIP results convert to CLB — " +
  "your test report or IRCC's conversion chart gives the number.";

function LanguageRow({
  prefix,
  values,
  onChange,
  disabled,
}: {
  prefix: "clb_en" | "nclc_fr" | "spouse_clb";
  values: Record<string, number>;
  onChange: (field: string, value: number) => void;
  disabled?: boolean;
}) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {ABILITIES.map((ability) => {
        const field = `${prefix}_${ability}`;
        return (
          <div key={field}>
            <Label htmlFor={field} className="text-xs capitalize text-muted-foreground">
              {ability}
            </Label>
            <Input
              id={field}
              type="number"
              min={0}
              max={12}
              disabled={disabled}
              value={values[field] ?? 0}
              onChange={(e) => onChange(field, Number(e.target.value))}
            />
          </div>
        );
      })}
    </div>
  );
}

export function CrsProfileForm({
  initial,
  completed,
}: {
  initial: Partial<CrsProfileValues>;
  completed: boolean;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(!completed);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [values, setValues] = useState<Record<string, unknown>>({
    date_of_birth: initial.date_of_birth ?? "",
    education_level: initial.education_level ?? "",
    foreign_experience_months: initial.foreign_experience_months ?? 0,
    has_accompanying_spouse: initial.has_accompanying_spouse ?? false,
    spouse_education_level: initial.spouse_education_level ?? "",
    spouse_canadian_experience_years: initial.spouse_canadian_experience_years ?? 0,
    has_provincial_nomination: initial.has_provincial_nomination ?? false,
    sibling_in_canada: initial.sibling_in_canada ?? false,
    canadian_study_credential: initial.canadian_study_credential ?? "",
    trades_certificate: initial.trades_certificate ?? false,
    ...Object.fromEntries(
      (["clb_en", "nclc_fr", "spouse_clb"] as const).flatMap((p) =>
        ABILITIES.map((a) => [`${p}_${a}`, (initial as Record<string, number>)[`${p}_${a}`] ?? 0])
      )
    ),
  });

  const set = (field: string, value: unknown) => setValues((v) => ({ ...v, [field]: value }));
  const hasSpouse = Boolean(values.has_accompanying_spouse);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const payload = { ...values };
      if (!payload.date_of_birth) delete payload.date_of_birth;
      if (!payload.education_level) delete payload.education_level;
      if (!payload.spouse_education_level) delete payload.spouse_education_level;

      const res = await fetch("/api/profile/crs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Could not save");

      // Regenerate immediately so the score reflects what was just entered.
      const gen = await fetch("/api/pathways/generate", { method: "POST" });
      if (!gen.ok) {
        const genData = await gen.json().catch(() => ({}));
        throw new Error(genData.error || "Saved, but the report could not be generated");
      }
      setOpen(false);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save");
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
          <p className="text-sm text-muted-foreground">
            Your score is calculated from your date of birth, education, language scores and experience.
          </p>
          <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
            Edit CRS details
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-primary/40">
      <CardHeader>
        <CardTitle className="text-base">
          {completed ? "Edit your CRS details" : "Tell us what IRCC scores you on"}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {!completed && (
          <p className="text-sm text-muted-foreground">
            These are the exact inputs of the Comprehensive Ranking System. Without them we cannot give you a
            real score, only a guess — and a guess is worthless for an immigration decision.
          </p>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="date_of_birth">Date of birth</Label>
            <Input
              id="date_of_birth"
              type="date"
              value={String(values.date_of_birth ?? "")}
              onChange={(e) => set("date_of_birth", e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="education_level">Highest completed education</Label>
            <select
              id="education_level"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={String(values.education_level ?? "")}
              onChange={(e) => set("education_level", e.target.value)}
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

        <div>
          <Label className="text-sm font-semibold">English (CLB per ability)</Label>
          <p className="mb-2 text-xs text-muted-foreground">{CLB_HELP}</p>
          <LanguageRow prefix="clb_en" values={values as Record<string, number>} onChange={set} />
        </div>

        <div>
          <Label className="text-sm font-semibold">French (NCLC per ability)</Label>
          <p className="mb-2 text-xs text-muted-foreground">
            Leave at 0 if you have no French test. NCLC 7+ across all four unlocks French-category draws, which
            have had the lowest cut-offs of any route.
          </p>
          <LanguageRow prefix="nclc_fr" values={values as Record<string, number>} onChange={set} />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="foreign_experience_months">Foreign work experience (months)</Label>
            <Input
              id="foreign_experience_months"
              type="number"
              min={0}
              value={Number(values.foreign_experience_months ?? 0)}
              onChange={(e) => set("foreign_experience_months", Number(e.target.value))}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Skilled work outside Canada. Canadian experience comes from your work history.
            </p>
          </div>
          <div>
            <Label htmlFor="canadian_study_credential">Canadian post-secondary credential</Label>
            <select
              id="canadian_study_credential"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={String(values.canadian_study_credential ?? "")}
              onChange={(e) => set("canadian_study_credential", e.target.value)}
            >
              <option value="">None</option>
              <option value="one_or_two_year">One- or two-year credential (+15)</option>
              <option value="three_year_plus">Three years or more (+30)</option>
            </select>
          </div>
        </div>

        <fieldset className="space-y-2">
          <legend className="text-sm font-semibold">Also true of you?</legend>
          {[
            ["has_provincial_nomination", "I hold a provincial nomination (+600)"],
            ["sibling_in_canada", "I have a sibling aged 18+ who is a Canadian citizen or PR (+15)"],
            ["trades_certificate", "I hold a Canadian certificate of qualification in a skilled trade"],
            ["has_accompanying_spouse", "A spouse or common-law partner will come with me"],
          ].map(([field, label]) => (
            <label key={field} className="flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                className="mt-1"
                checked={Boolean(values[field])}
                onChange={(e) => set(field, e.target.checked)}
              />
              <span>{label}</span>
            </label>
          ))}
        </fieldset>

        {hasSpouse && (
          <div className="space-y-4 rounded-md border border-border p-4">
            <p className="text-sm font-semibold">Your spouse or partner</p>
            <p className="text-xs text-muted-foreground">
              An accompanying spouse lowers your own maximum in several categories and adds up to 40 points of
              their own, so their details change the total in both directions.
            </p>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="spouse_education_level">Their highest education</Label>
                <select
                  id="spouse_education_level"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={String(values.spouse_education_level ?? "")}
                  onChange={(e) => set("spouse_education_level", e.target.value)}
                >
                  <option value="">Select…</option>
                  {EDUCATION_ORDER.map((level) => (
                    <option key={level} value={level}>
                      {EDUCATION_LABELS[level]}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <Label htmlFor="spouse_canadian_experience_years">Their Canadian work experience (years)</Label>
                <Input
                  id="spouse_canadian_experience_years"
                  type="number"
                  min={0}
                  max={50}
                  value={Number(values.spouse_canadian_experience_years ?? 0)}
                  onChange={(e) => set("spouse_canadian_experience_years", Number(e.target.value))}
                />
              </div>
            </div>
            <div>
              <Label className="text-sm">Their English (CLB per ability)</Label>
              <LanguageRow prefix="spouse_clb" values={values as Record<string, number>} onChange={set} />
            </div>
          </div>
        )}

        {error && (
          <p className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </p>
        )}

        <div className="flex flex-wrap gap-3">
          <Button onClick={save} disabled={saving}>
            {saving ? "Calculating…" : "Save and calculate my CRS"}
          </Button>
          {completed && (
            <Button variant="ghost" onClick={() => setOpen(false)} disabled={saving}>
              Cancel
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
