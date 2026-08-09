"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EDUCATION_LABELS, EDUCATION_ORDER } from "@/lib/crs/grid";
import {
  TEST_META,
  convertAll,
  type EnglishTest,
  type FrenchTest,
} from "@/lib/crs/language-conversion";

export interface CrsProfileValues {
  date_of_birth: string;
  education_level: string;
  canadian_experience_months: number;
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

const ENGLISH_TESTS: EnglishTest[] = ["clb", "celpip", "ielts", "pte"];
const FRENCH_TESTS: FrenchTest[] = ["none", "tef", "tcf", "nclc"];

/**
 * Raw test scores in, CLB out.
 *
 * IRCC's own calculator asks for test results and converts internally. Asking for CLB
 * directly — as this form used to — pushes a lookup onto the user in the largest
 * scoring factor after age, which is exactly where a transcription slip is most
 * expensive. The converted level is shown live so the number is never a black box.
 */
function LanguageRow({
  prefix,
  test,
  values,
  onChange,
}: {
  prefix: "clb_en" | "nclc_fr" | "spouse_clb";
  test: EnglishTest | FrenchTest;
  values: Record<string, number>;
  onChange: (field: string, value: number) => void;
}) {
  const meta = TEST_META[test];
  if (!meta) return null;

  const raw = {
    reading: values[`${prefix}_reading`] ?? 0,
    writing: values[`${prefix}_writing`] ?? 0,
    listening: values[`${prefix}_listening`] ?? 0,
    speaking: values[`${prefix}_speaking`] ?? 0,
  };
  const converted = convertAll(test, raw);
  const isDirect = test === "clb" || test === "nclc" || test === "celpip";
  const unit = prefix === "nclc_fr" ? "NCLC" : "CLB";

  return (
    <div className="space-y-2">
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
                min={meta.min}
                max={meta.max}
                step={meta.step}
                value={values[field] ?? 0}
                onChange={(e) => onChange(field, Number(e.target.value))}
              />
              {!isDirect && (
                <p className="mt-1 text-xs text-muted-foreground">
                  {unit} {converted[ability]}
                </p>
              )}
            </div>
          );
        })}
      </div>
      <p className="text-xs text-muted-foreground">{meta.hint}</p>
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
  // Stored values are already CLB/NCLC levels, so "I know my levels" is the only
  // default that reads them back correctly.
  const [englishTest, setEnglishTest] = useState<EnglishTest>("clb");
  // Defaults to "none" — the form used to demand four French scores from everyone,
  // including the majority who have never sat a French test. But someone who already
  // saved French levels must not have them silently zeroed on their next save, so an
  // existing score reopens the section as a direct NCLC entry.
  const [frenchTest, setFrenchTest] = useState<FrenchTest>(() =>
    ABILITIES.some((a) => Number((initial as Record<string, number>)[`nclc_fr_${a}`] ?? 0) > 0)
      ? "nclc"
      : "none"
  );
  const [spouseTest, setSpouseTest] = useState<EnglishTest>("clb");
  const [values, setValues] = useState<Record<string, unknown>>({
    date_of_birth: initial.date_of_birth ?? "",
    education_level: initial.education_level ?? "",
    canadian_experience_months: initial.canadian_experience_months ?? 0,
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

  /**
   * Clear the row when the test changes. A "9" is CLB 9 on one scale and an IELTS
   * band 9 on another — carrying the number across would quietly rescore the user.
   */
  const changeTest = <T,>(prefix: string, setter: (t: T) => void) => (test: T) => {
    setter(test);
    setValues((v) => {
      const next = { ...v };
      for (const ability of ABILITIES) next[`${prefix}_${ability}`] = 0;
      return next;
    });
  };
  const hasSpouse = Boolean(values.has_accompanying_spouse);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const payload = { ...values };

      // The API and the CRS engine speak CLB/NCLC. Whatever test the user picked,
      // convert here so raw IELTS bands never reach the scoring grid as if they
      // were levels — a 7.0 band is CLB 9, and storing it as CLB 7 costs real points.
      const toLevels = (prefix: string, test: EnglishTest | FrenchTest) => {
        const converted = convertAll(test, {
          reading: Number(values[`${prefix}_reading`] ?? 0),
          writing: Number(values[`${prefix}_writing`] ?? 0),
          listening: Number(values[`${prefix}_listening`] ?? 0),
          speaking: Number(values[`${prefix}_speaking`] ?? 0),
        });
        for (const ability of ABILITIES) payload[`${prefix}_${ability}`] = converted[ability];
      };

      toLevels("clb_en", englishTest);
      // "none" converts to all zeros, which is what an untested applicant scores.
      toLevels("nclc_fr", frenchTest);
      toLevels("spouse_clb", spouseTest);

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

        <div className="space-y-2">
          <Label htmlFor="english-test" className="text-sm font-semibold">
            English test
          </Label>
          <select
            id="english-test"
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            value={englishTest}
            onChange={(e) => changeTest<EnglishTest>("clb_en", setEnglishTest)(e.target.value as EnglishTest)}
          >
            {ENGLISH_TESTS.map((t) => (
              <option key={t} value={t}>
                {TEST_META[t]?.label}
              </option>
            ))}
          </select>
          <p className="text-xs text-muted-foreground">
            Enter the scores exactly as they appear on your report — we convert them to CLB the
            same way IRCC does.
          </p>
          <LanguageRow
            prefix="clb_en"
            test={englishTest}
            values={values as Record<string, number>}
            onChange={set}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="french-test" className="text-sm font-semibold">
            French test
          </Label>
          <select
            id="french-test"
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            value={frenchTest}
            onChange={(e) => changeTest<FrenchTest>("nclc_fr", setFrenchTest)(e.target.value as FrenchTest)}
          >
            <option value="none">I haven&apos;t taken a French test</option>
            {FRENCH_TESTS.filter((t) => t !== "none").map((t) => (
              <option key={t} value={t}>
                {TEST_META[t]?.label}
              </option>
            ))}
          </select>
          {frenchTest === "none" ? (
            <p className="text-xs text-muted-foreground">
              Nothing to enter. Worth knowing: French draws have had the lowest cut-offs of any
              route — 391 in the most recent round, against 516 for the Canadian Experience Class.
            </p>
          ) : (
            <LanguageRow
              prefix="nclc_fr"
              test={frenchTest}
              values={values as Record<string, number>}
              onChange={set}
            />
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="canadian_experience_months">Canadian skilled work experience (months)</Label>
            <Input
              id="canadian_experience_months"
              type="number"
              min={0}
              value={Number(values.canadian_experience_months ?? 0)}
              onChange={(e) => set("canadian_experience_months", Number(e.target.value))}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              The single biggest lever after language — up to 80 points, and 12 months opens the Canadian
              Experience Class. Counts TEER 0–3 work in Canada. Overrides the total from your work history.
            </p>
          </div>
          <div>
            <Label htmlFor="foreign_experience_months">Foreign work experience (months)</Label>
            <Input
              id="foreign_experience_months"
              type="number"
              min={0}
              value={Number(values.foreign_experience_months ?? 0)}
              onChange={(e) => set("foreign_experience_months", Number(e.target.value))}
            />
            <p className="mt-1 text-xs text-muted-foreground">Skilled work outside Canada.</p>
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
            <div className="space-y-2">
              <Label htmlFor="spouse-test" className="text-sm">
                Their English test
              </Label>
              <select
                id="spouse-test"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={spouseTest}
                onChange={(e) => changeTest<EnglishTest>("spouse_clb", setSpouseTest)(e.target.value as EnglishTest)}
              >
                {ENGLISH_TESTS.map((t) => (
                  <option key={t} value={t}>
                    {TEST_META[t]?.label}
                  </option>
                ))}
              </select>
              <LanguageRow
                prefix="spouse_clb"
                test={spouseTest}
                values={values as Record<string, number>}
                onChange={set}
              />
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
