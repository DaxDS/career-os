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
    setRoles((prev) =>
      prev.map((role, i) => (i === index ? { ...role, [field]: value } : role))
    );
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
          sort_order: index,
        }))
      );
    }

    await supabase.from("profiles").update({ onboarding_step: 2 }).eq("id", user.id);
    router.push("/onboarding/noc-mapping");
  }

  if (loading) return <p>{tc("loading")}</p>;

  return (
    <OnboardingWizard currentStep={1}>
      <Card>
        <CardHeader>
          <CardTitle>{t("title")}</CardTitle>
          <CardDescription>{t("description")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {roles.map((role, index) => (
            <div key={index} className="space-y-3 rounded-lg border p-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>Job title</Label>
                  <Input
                    value={role.title}
                    onChange={(e) => updateRole(index, "title", e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Employer</Label>
                  <Input
                    value={role.employer}
                    onChange={(e) => updateRole(index, "employer", e.target.value)}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Duties (used for NOC mapping)</Label>
                <textarea
                  className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={role.duties_text}
                  onChange={(e) => updateRole(index, "duties_text", e.target.value)}
                />
              </div>
            </div>
          ))}
          <Button
            type="button"
            variant="outline"
            onClick={() => setRoles((prev) => [...prev, { ...EMPTY_ROLE }])}
          >
            Add another role
          </Button>
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
