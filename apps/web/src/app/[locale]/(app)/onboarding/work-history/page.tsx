"use client";

import { useEffect, useState } from "react";
import { useRouter } from "@/i18n/routing";
import { useTranslations } from "next-intl";
import { createClient } from "@/lib/supabase/client";
import { OnboardingWizard } from "@/components/onboarding/onboarding-wizard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface WorkHistoryRow {
  id?: string;
  title: string;
  employer: string;
  country: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
  duties_text: string;
}

const EMPTY_ROLE: WorkHistoryRow = {
  title: "",
  employer: "",
  country: "CA",
  start_date: "",
  end_date: "",
  is_current: false,
  duties_text: "",
};

/** Whole months between two dates, matching the server-side calculation in lib/crs/build.ts. */
function monthsBetween(start: string, end: string, isCurrent: boolean): number {
  if (!start) return 0;
  const startDate = new Date(`${start}T00:00:00Z`);
  if (Number.isNaN(startDate.getTime())) return 0;
  const endDate = isCurrent || !end ? new Date() : new Date(`${end}T00:00:00Z`);
  if (Number.isNaN(endDate.getTime())) return 0;
  return Math.max(
    0,
    (endDate.getUTCFullYear() - startDate.getUTCFullYear()) * 12 +
      (endDate.getUTCMonth() - startDate.getUTCMonth())
  );
}

export default function WorkHistoryStep() {
  const t = useTranslations("onboarding.workHistory");
  const tc = useTranslations("common");
  const router = useRouter();
  const [roles, setRoles] = useState<WorkHistoryRow[]>([EMPTY_ROLE]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    async function load() {
      const supabase = createClient();
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user) return;

      const { data } = await supabase
        .from("work_history")
        .select("*")
        .eq("user_id", user.id)
        .order("sort_order");

      if (data && data.length > 0) {
        setRoles(
          data.map((r) => ({
            id: r.id,
            title: r.title,
            employer: r.employer ?? "",
            country: r.country,
            start_date: r.start_date ?? "",
            end_date: r.end_date ?? "",
            is_current: r.is_current,
            duties_text: r.duties_text ?? "",
          }))
        );
      }
      setLoading(false);
    }
    load();
  }, []);

  function updateRole(index: number, field: keyof WorkHistoryRow, value: string | boolean) {
    setRoles((prev) => prev.map((role, i) => (i === index ? { ...role, [field]: value } : role)));
  }

  function removeRole(index: number) {
    setRoles((prev) => (prev.length === 1 ? prev : prev.filter((_, i) => i !== index)));
  }

  async function handleContinue() {
    setSaving(true);
    const supabase = createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) return;

    await supabase.from("work_history").delete().eq("user_id", user.id);

    const validRoles = roles.filter((r) => r.title.trim());
    if (validRoles.length > 0) {
      await supabase.from("work_history").insert(
        validRoles.map((role, index) => ({
          user_id: user.id,
          title: role.title,
          employer: role.employer || null,
          country: role.country,
          start_date: role.start_date || null,
          end_date: role.is_current ? null : role.end_date || null,
          is_current: role.is_current,
          duties_text: role.duties_text || null,
          // Stored so the figure survives even if dates are later cleared.
          months_canadian_experience:
            role.country === "CA" ? monthsBetween(role.start_date, role.end_date, role.is_current) : 0,
          sort_order: index,
        }))
      );
    }

    await supabase.from("profiles").update({ onboarding_step: 2 }).eq("id", user.id);
    router.push("/onboarding/noc-mapping");
  }

  if (loading) return <p>{tc("loading")}</p>;

  const canadianMonths = roles
    .filter((r) => r.country === "CA" && r.title.trim())
    .reduce((sum, r) => sum + monthsBetween(r.start_date, r.end_date, r.is_current), 0);

  return (
    <OnboardingWizard currentStep={1}>
      <Card>
        <CardHeader>
          <CardTitle>{t("title")}</CardTitle>
          <CardDescription>{t("description")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Dates drive Canadian experience, which is worth up to 80 CRS points and
              gates both CEC and every category-based round. Without them the report
              scores the user at zero experience. */}
          <p className="rounded-md border border-border bg-muted/40 p-3 text-sm text-muted-foreground">
            Dates matter more than anything else here. Twelve months of Canadian work opens the Canadian
            Experience Class and the category-based rounds — without dates we score you at zero experience.
          </p>

          {roles.map((role, index) => (
            <div key={index} className="space-y-3 rounded-lg border p-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>Job title</Label>
                  <Input value={role.title} onChange={(e) => updateRole(index, "title", e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label>Employer</Label>
                  <Input
                    value={role.employer}
                    onChange={(e) => updateRole(index, "employer", e.target.value)}
                  />
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                <div className="space-y-2">
                  <Label>Country</Label>
                  <select
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={role.country}
                    onChange={(e) => updateRole(index, "country", e.target.value)}
                  >
                    <option value="CA">Canada</option>
                    <option value="OTHER">Outside Canada</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <Label>Start date</Label>
                  <Input
                    type="date"
                    value={role.start_date}
                    onChange={(e) => updateRole(index, "start_date", e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>End date</Label>
                  <Input
                    type="date"
                    disabled={role.is_current}
                    value={role.is_current ? "" : role.end_date}
                    onChange={(e) => updateRole(index, "end_date", e.target.value)}
                  />
                </div>
              </div>

              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={role.is_current}
                  onChange={(e) => updateRole(index, "is_current", e.target.checked)}
                />
                I still work here
              </label>

              <div className="space-y-2">
                <Label>Duties (used for NOC mapping)</Label>
                <textarea
                  className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={role.duties_text}
                  onChange={(e) => updateRole(index, "duties_text", e.target.value)}
                />
              </div>

              <div className="flex items-center justify-between">
                <p className="text-xs text-muted-foreground">
                  {role.start_date
                    ? `${monthsBetween(role.start_date, role.end_date, role.is_current)} months`
                    : "Add a start date to count this role"}
                </p>
                {roles.length > 1 && (
                  <Button type="button" variant="ghost" size="sm" onClick={() => removeRole(index)}>
                    Remove
                  </Button>
                )}
              </div>
            </div>
          ))}

          <div className="flex flex-wrap items-center justify-between gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => setRoles((prev) => [...prev, { ...EMPTY_ROLE }])}
            >
              Add another role
            </Button>
            <p className="text-sm">
              Canadian experience so far:{" "}
              <span className="font-semibold tabular-nums">{canadianMonths} months</span>
              {canadianMonths >= 12 ? " — enough for CEC" : " — 12 months opens CEC"}
            </p>
          </div>

          <div className="flex gap-2">
            <Button variant="outline" onClick={() => router.push("/onboarding")}>
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
